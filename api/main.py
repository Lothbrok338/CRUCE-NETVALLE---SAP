"""FastAPI: clasificación, jobs, observaciones paginadas y descarga del Excel.

Arranque:  uvicorn api.main:crear_app --factory --host 0.0.0.0 --port $PORT
"""
import logging
import re
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.auth import verificar_acceso
from api.config import Settings, get_settings
from api.jobs import EN_COLA, ERROR, LISTO, PROCESANDO, JobManager, filas
from api.schemas import (ArchivoClasificado, Clasificacion, EstadoControl, JobCreado,
                         PaginaObservaciones)
from core.clasificacion import (clasificar_archivos, contiene_base_netvalle,
                                cuentas_en_archivo)
from core.constantes import ARCHIVO_FINAL, CUENTA_IT, CUENTA_IVA

logger = logging.getLogger("api")
EXTENSIONES = {".xlsx", ".xlsm"}
PROGRESO = {EN_COLA: 5, PROCESANDO: 50, LISTO: 100, ERROR: 100}
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def nombre_seguro(nombre: str) -> str:
    base = Path((nombre or "archivo.xlsx").replace("\\", "/")).name
    return re.sub(r"[^\w.\- ()]", "_", base)[:120] or "archivo.xlsx"


async def guardar_archivos(archivos: List[UploadFile], directorio: Path, limite: int) -> dict:
    """Guarda los archivos validando extensión y tamaño. Devuelve {nombre_visible: ruta}."""
    if not archivos:
        raise HTTPException(422, "No se recibió ningún archivo.")
    guardados = {}
    for f in archivos:
        nombre = nombre_seguro(f.filename)
        if Path(nombre).suffix.lower() not in EXTENSIONES:
            raise HTTPException(
                422, f"'{nombre}' no es un archivo Excel (.xlsx). Los .xls antiguos no se admiten: guárdalo como .xlsx.")
        original, n = nombre, 1
        while nombre in guardados:  # nombres repetidos
            n += 1
            nombre = f"{Path(original).stem} ({n}){Path(original).suffix}"
        datos = await f.read(limite + 1)
        if len(datos) > limite:
            raise HTTPException(413, f"'{nombre}' supera el tamaño máximo de {limite // (1024 * 1024)} MB.")
        if not datos:
            raise HTTPException(422, f"'{nombre}' está vacío.")
        ruta = directorio / nombre
        ruta.write_bytes(datos)
        guardados[nombre] = str(ruta)
    return guardados


def _limpiar(texto: str, directorio: Path) -> str:
    return re.sub(re.escape(str(directorio)) + r"[/\\]?", "", texto)


def clasificar_vista(guardados: dict, directorio: Path) -> Clasificacion:
    """Mismo criterio que clasificar_archivos, pero devolviendo el detalle por archivo."""
    archivos = []
    for nombre, ruta in guardados.items():
        try:
            if contiene_base_netvalle(ruta):
                archivos.append(ArchivoClasificado(nombre=nombre, tipo="NETVALLE"))
                continue
            cuentas = cuentas_en_archivo(ruta)
            tipos = [t for t, c in (("IVA", CUENTA_IVA), ("IT", CUENTA_IT)) if c in cuentas]
            archivos.append(ArchivoClasificado(
                nombre=nombre, tipo="SAP" if tipos else "OTROS", cuentas=tipos,
                detalle=None if tipos else "No es NETVALLE ni contiene las cuentas de IVA/IT."))
        except Exception as exc:
            archivos.append(ArchivoClasificado(nombre=nombre, tipo="OTROS", detalle=_limpiar(str(exc), directorio)))
    problemas = []
    try:
        clasificar_archivos(list(guardados.values()))
    except Exception as exc:
        problemas = [p for p in _limpiar(str(exc), directorio).split("\n") if p]
    return Clasificacion(valido=not problemas, archivos=archivos, problemas=problemas)


def validar_seleccion(guardados: dict, netvalle: str, sap: List[str], directorio: Path):
    """Corrección manual: se usan solo los archivos elegidos, validados con los mismos criterios."""
    for n in [netvalle, *sap]:
        if n not in guardados:
            raise HTTPException(422, f"El archivo '{n}' no fue enviado.")
    if netvalle in sap:
        raise HTTPException(422, "Un mismo archivo no puede ser NETVALLE y SAP a la vez.")
    if not sap:
        raise HTTPException(422, "Falta indicar al menos un archivo SAP.")
    try:
        if not contiene_base_netvalle(guardados[netvalle]):
            raise HTTPException(422, f"'{netvalle}' no contiene las hojas NETVALLE ni CONSOLIDADO.")
        cuentas = set()
        for n in sap:
            c = cuentas_en_archivo(guardados[n])
            if not c & {CUENTA_IVA, CUENTA_IT}:
                raise HTTPException(422, f"'{n}' no contiene las cuentas de IVA ({CUENTA_IVA}) ni de IT ({CUENTA_IT}).")
            cuentas |= c
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, _limpiar(str(exc), directorio))
    if CUENTA_IVA not in cuentas:
        raise HTTPException(422, f"El SAP no contiene la cuenta de IVA {CUENTA_IVA}.")
    if CUENTA_IT not in cuentas:
        raise HTTPException(422, f"El SAP no contiene la cuenta de IT {CUENTA_IT}.")


def crear_app(settings: Optional[Settings] = None, manager: Optional[JobManager] = None) -> FastAPI:
    settings = settings or get_settings()
    manager = manager or JobManager(ttl_horas=settings.result_ttl_hours, workers=settings.workers)

    @asynccontextmanager
    async def ciclo(_app):
        yield
        manager.cerrar()

    app = FastAPI(title="Control Tributario Integral", version="1.0.0", lifespan=ciclo)
    app.state.settings, app.state.manager = settings, manager
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"],
                       allow_headers=["*"], expose_headers=["Content-Disposition"])

    @app.get("/health", include_in_schema=False)
    def health():
        return {"status": "ok"}

    protegido = [Depends(verificar_acceso)]

    def job_o_404(jid: str):
        job = manager.obtener(jid)
        if job is None:
            raise HTTPException(404, "Control no encontrado o expirado (los resultados se conservan 24 horas).")
        return job

    @app.post("/api/clasificar", response_model=Clasificacion, dependencies=protegido)
    async def clasificar(archivos: List[UploadFile] = File(...)):
        """Vista previa de la clasificación automática, sin crear un control."""
        _jid, d = manager.nuevo_directorio()
        try:
            guardados = await guardar_archivos(archivos, d, settings.max_upload_bytes)
            return await run_in_threadpool(clasificar_vista, guardados, d)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    @app.post("/api/controles", response_model=JobCreado, status_code=202, dependencies=protegido)
    async def crear_control(archivos: List[UploadFile] = File(...), netvalle: Optional[str] = Form(None),
                            sap: Optional[List[str]] = Form(None)):
        """Clasifica, valida y crea el job. Con `netvalle`/`sap` se corrige la clasificación automática."""
        jid, d = manager.nuevo_directorio()
        try:
            guardados = await guardar_archivos(archivos, d, settings.max_upload_bytes)
            vista = await run_in_threadpool(clasificar_vista, guardados, d)
            if netvalle or sap:
                if not netvalle:
                    raise HTTPException(422, "Falta indicar el archivo NETVALLE (CRUCE).")
                await run_in_threadpool(validar_seleccion, guardados, netvalle, sap or [], d)
                ruta_net, rutas_sap = guardados[netvalle], [guardados[n] for n in sap]
            else:
                if not vista.valido:
                    raise HTTPException(422, "\n".join(vista.problemas))
                clasif = await run_in_threadpool(clasificar_archivos, list(guardados.values()))
                ruta_net, rutas_sap = clasif["NETVALLE"][0], clasif["SAP"]
        except BaseException:
            shutil.rmtree(d, ignore_errors=True)
            raise
        for ruta in guardados.values():  # no dejar en disco archivos que no se usan
            if ruta != ruta_net and ruta not in rutas_sap:
                Path(ruta).unlink(missing_ok=True)
        job = manager.crear(jid, d, ruta_net, rutas_sap)
        return JobCreado(id=job.id, estado=job.estado, clasificacion=vista)

    @app.get("/api/controles/{jid}", response_model=EstadoControl, dependencies=protegido)
    def estado(jid: str):
        job = job_o_404(jid)
        return EstadoControl(id=job.id, estado=job.estado, progreso=PROGRESO[job.estado], creado=job.creado,
                             expira=manager.expira_en(job), resumen=job.resumen, error=job.error)

    @app.get("/api/controles/{jid}/observaciones", response_model=PaginaObservaciones, dependencies=protegido)
    def observaciones(jid: str, pagina: int = Query(1, ge=1), por_pagina: int = Query(50, ge=1, le=500),
                      q: Optional[str] = None, control: Optional[str] = None, punto: Optional[str] = None,
                      orden: Optional[str] = None, direccion: str = Query("asc", pattern="^(asc|desc)$")):
        job = job_o_404(jid)
        if job.estado != LISTO:
            raise HTTPException(409, f"El control está '{job.estado}'.")
        df = job.observaciones
        filtros = {"CONTROL": sorted(df["CONTROL"].dropna().unique().tolist()),
                   "PUNTO": sorted(df["PUNTO"].dropna().unique().tolist())}
        if control:
            df = df[df["CONTROL"].eq(control)]
        if punto:
            df = df[df["PUNTO"].eq(punto)]
        if q:
            texto = df.fillna("").astype(str)
            df = df[texto.apply(lambda c: c.str.contains(q, case=False, regex=False)).any(axis=1)]
        if orden:
            if orden not in df.columns:
                raise HTTPException(422, f"Columna de orden desconocida: {orden}.")
            df = df.sort_values(orden, ascending=direccion == "asc", na_position="last", kind="stable")
        total = len(df)
        paginas = max(1, -(-total // por_pagina))
        trozo = df.iloc[(pagina - 1) * por_pagina: pagina * por_pagina]
        return PaginaObservaciones(total=total, pagina=pagina, por_pagina=por_pagina, paginas=paginas,
                                   columnas=list(df.columns), filas=filas(trozo), filtros=filtros)

    @app.get("/api/controles/{jid}/excel", dependencies=protegido)
    def excel(jid: str):
        job = job_o_404(jid)
        if job.estado != LISTO or not job.excel or not job.excel.exists():
            raise HTTPException(409, f"El control está '{job.estado}'.")
        return FileResponse(job.excel, filename=ARCHIVO_FINAL, media_type=MIME_XLSX)

    return app
