"""Jobs en memoria con un pool de hilos. Resultados temporales con expiración (24 h por defecto).

Sin base de datos: al reiniciar el servicio los resultados se pierden (por diseño, son temporales).
No se escribe ningún dato de facturas en logs: solo ids y estados.
"""
import logging
import re
import shutil
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

from core.constantes import ARCHIVO_FINAL
from core.control import generar_control

logger = logging.getLogger("api.jobs")

EN_COLA, PROCESANDO, LISTO, ERROR = "en cola", "procesando", "listo", "error"


@dataclass
class Job:
    id: str
    directorio: Path
    netvalle: str
    sap: list
    creado: float
    estado: str = EN_COLA
    resumen: Optional[dict] = None
    observaciones: Optional[pd.DataFrame] = None
    excel: Optional[Path] = None
    error: Optional[str] = None
    terminado: Optional[float] = None


def mensaje_seguro(exc: Exception, directorio: Path) -> str:
    """Los mensajes de core están pensados para el usuario; solo se quitan rutas del servidor."""
    texto = str(exc) or exc.__class__.__name__
    return re.sub(re.escape(str(directorio)) + r"[/\\]?", "", texto)


def limpiar_valor(v):
    return None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)


def filas(df: pd.DataFrame) -> list:
    obj = df.astype(object).where(df.notna(), None)
    return [{k: limpiar_valor(v) if v is not None else None for k, v in r.items()} for r in obj.to_dict("records")]


def construir_resumen(resultado) -> dict:
    e = resultado.ejecutivo
    tarjetas = []
    for _, f in e.iterrows():
        tarjetas.append({
            "control": f["CONTROL"],
            "resultado": f["RESULTADO"],
            "cantidad": limpiar_valor(f["CANTIDAD"]),
            "total_facturas_bs": limpiar_valor(f["TOTAL FACTURAS Bs"]),
            "dato_clave": f["DATO CLAVE"],
            "que_significa": f["QUÉ SIGNIFICA"],
            "que_hacer": f["QUÉ HACER"],
        })
    return {"tarjetas": tarjetas, "observaciones_total": int(len(resultado.observaciones))}


class JobManager:
    def __init__(self, ttl_horas: float = 24.0, workers: int = 2, base_dir: Optional[Path] = None):
        self.ttl = ttl_horas * 3600
        self.base = Path(base_dir) if base_dir else Path(tempfile.mkdtemp(prefix="ct_jobs_"))
        self.base.mkdir(parents=True, exist_ok=True)
        self._jobs: dict = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="control")
        self._detener = threading.Event()
        self._limpieza = threading.Thread(target=self._bucle_limpieza, daemon=True)
        self._limpieza.start()

    # ---- ciclo de vida
    def nuevo_directorio(self) -> tuple:
        jid = uuid.uuid4().hex
        d = self.base / jid
        d.mkdir(parents=True)
        return jid, d

    def crear(self, jid: str, directorio: Path, netvalle: str, sap: list) -> Job:
        self.purgar()
        job = Job(id=jid, directorio=directorio, netvalle=netvalle, sap=sap, creado=time.time())
        with self._lock:
            self._jobs[jid] = job
        self._pool.submit(self._ejecutar, jid)
        logger.info("job %s en cola", jid)
        return job

    def obtener(self, jid: str) -> Optional[Job]:
        self.purgar()
        with self._lock:
            return self._jobs.get(jid)

    def expira_en(self, job: Job) -> float:
        return job.creado + self.ttl

    def purgar(self) -> int:
        ahora = time.time()
        with self._lock:
            vencidos = [j for j in self._jobs.values() if ahora >= j.creado + self.ttl and j.estado in (LISTO, ERROR)]
            for j in vencidos:
                self._jobs.pop(j.id, None)
        for j in vencidos:
            shutil.rmtree(j.directorio, ignore_errors=True)
            logger.info("job %s expirado y eliminado", j.id)
        return len(vencidos)

    def cerrar(self):
        self._detener.set()
        self._pool.shutdown(wait=False, cancel_futures=True)
        shutil.rmtree(self.base, ignore_errors=True)

    def _bucle_limpieza(self):
        while not self._detener.wait(900):
            self.purgar()

    # ---- ejecución
    def _ejecutar(self, jid: str):
        with self._lock:
            job = self._jobs.get(jid)
        if job is None:
            return
        job.estado = PROCESANDO
        try:
            salida = job.directorio / ARCHIVO_FINAL
            resultado = generar_control(job.netvalle, job.sap, archivo_salida=str(salida))
            job.resumen = construir_resumen(resultado)
            job.observaciones = resultado.observaciones.reset_index(drop=True)
            job.excel = salida
            job.estado = LISTO
        except Exception as exc:  # el mensaje de core es para el usuario; el detalle no se loguea
            job.error = mensaje_seguro(exc, job.directorio)
            job.estado = ERROR
        finally:
            job.terminado = time.time()
            # los archivos de entrada ya no se necesitan: se borran apenas termina el proceso
            for ruta in [job.netvalle, *job.sap]:
                try:
                    Path(ruta).unlink(missing_ok=True)
                except OSError:
                    pass
            logger.info("job %s -> %s", jid, job.estado)
