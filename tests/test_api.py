"""Pruebas de contrato de la API (httpx/TestClient) con datos sintéticos."""
import io
import logging
import time

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from api.config import Settings
from api.jobs import JobManager
from api.main import crear_app
from core.control import generar_control

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture()
def cliente(tmp_path):
    manager = JobManager(ttl_horas=24, workers=2, base_dir=tmp_path / "jobs")
    app = crear_app(Settings(auth_enabled=False), manager)
    with TestClient(app) as c:
        c.manager = manager
        yield c


def _files(rutas):
    return [("archivos", (r.split("/")[-1], open(r, "rb"), XLSX)) for r in rutas]


def subir(cliente, archivos_sinteticos, **datos):
    return cliente.post("/api/controles", files=_files(archivos_sinteticos), data=datos)


def esperar(cliente, jid, hasta=("listo", "error"), timeout=30):
    fin = time.time() + timeout
    while time.time() < fin:
        r = cliente.get(f"/api/controles/{jid}")
        assert r.status_code == 200
        if r.json()["estado"] in hasta:
            return r.json()
        time.sleep(0.05)
    raise AssertionError("el job no terminó")


@pytest.fixture()
def listo(cliente, archivos_sinteticos):
    r = subir(cliente, archivos_sinteticos)
    assert r.status_code == 202, r.text
    jid = r.json()["id"]
    assert esperar(cliente, jid)["estado"] == "listo"
    return cliente, jid


def test_health(cliente):
    assert cliente.get("/health").json() == {"status": "ok"}


# ---------------- autenticación
def _app_auth(tmp_path, **kw):
    return TestClient(crear_app(Settings(**kw), JobManager(base_dir=tmp_path / "j")))


def test_auth_activada_exige_token(tmp_path):
    c = _app_auth(tmp_path, auth_enabled=True, auth_token="secreto")
    assert c.get("/health").status_code == 200  # health siempre abierto (Railway)
    assert c.get("/api/controles/x").status_code == 401
    assert c.get("/api/controles/x", headers={"Authorization": "Bearer mal"}).status_code == 401
    assert c.get("/api/controles/x", headers={"Authorization": "Bearer secreto"}).status_code == 404  # pasó auth


def test_auth_activada_sin_token_configurado_falla_cerrado(tmp_path):
    c = _app_auth(tmp_path, auth_enabled=True, auth_token="")
    assert c.get("/api/controles/x", headers={"Authorization": "Bearer "}).status_code == 503


def test_auth_desactivada_no_pide_token(cliente):
    assert cliente.get("/api/controles/x").status_code == 404


def test_auth_activa_por_defecto(monkeypatch):
    from api.config import get_settings
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    assert get_settings().auth_enabled is True


# ---------------- clasificación y validación
def test_clasificar_vista_previa(cliente, archivos_sinteticos):
    r = cliente.post("/api/clasificar", files=_files(archivos_sinteticos))
    assert r.status_code == 200
    j = r.json()
    assert j["valido"] and j["problemas"] == []
    assert {(a["nombre"], a["tipo"]) for a in j["archivos"]} == {("CRUCE.xlsx", "NETVALLE"), ("SAP.xlsx", "SAP")}
    assert next(a for a in j["archivos"] if a["tipo"] == "SAP")["cuentas"] == ["IVA", "IT"]


def test_rechaza_archivo_que_no_es_excel(cliente):
    r = cliente.post("/api/controles", files=[("archivos", ("datos.csv", b"a,b\n1,2", "text/csv"))])
    assert r.status_code == 422 and "no es un archivo Excel" in r.json()["detail"]


def test_rechaza_xls_antiguo(cliente):
    r = cliente.post("/api/controles", files=[("archivos", ("viejo.xls", b"x", "application/vnd.ms-excel"))])
    assert r.status_code == 422 and ".xls" in r.json()["detail"]


def test_rechaza_archivo_vacio_y_sin_archivos(cliente):
    assert cliente.post("/api/controles", files=[("archivos", ("a.xlsx", b"", XLSX))]).status_code == 422
    assert cliente.post("/api/controles").status_code == 422


def test_rechaza_archivo_demasiado_grande(tmp_path, archivos_sinteticos):
    app = crear_app(Settings(auth_enabled=False, max_upload_mb=0), JobManager(base_dir=tmp_path / "j"))
    r = TestClient(app).post("/api/controles", files=_files(archivos_sinteticos))
    assert r.status_code == 413 and "tamaño máximo" in r.json()["detail"]


def test_rechaza_xlsx_no_clasificable_con_mensaje_claro(cliente, archivos_sinteticos, tmp_path):
    otro = tmp_path / "otro.xlsx"
    pd.DataFrame({"x": [1]}).to_excel(otro, index=False)
    r = cliente.post("/api/controles", files=_files([*archivos_sinteticos, str(otro)]))
    assert r.status_code == 422
    assert "No se pudieron clasificar: otro.xlsx" in r.json()["detail"]
    assert "/tmp" not in r.json()["detail"]  # sin rutas del servidor


def test_rechaza_si_falta_sap(cliente, archivos_sinteticos):
    r = cliente.post("/api/controles", files=_files(archivos_sinteticos[:1]))
    assert r.status_code == 422 and "No se identificó el archivo SAP" in r.json()["detail"]


def test_xlsx_corrupto(cliente):
    r = cliente.post("/api/controles", files=[("archivos", ("roto.xlsx", b"no es excel", XLSX))])
    assert r.status_code == 422 and "No se pudo abrir" in r.json()["detail"]


# ---------------- flujo completo
def test_flujo_completo_estado_y_tarjetas(cliente, archivos_sinteticos):
    r = subir(cliente, archivos_sinteticos)
    assert r.status_code == 202
    cuerpo = r.json()
    assert cuerpo["clasificacion"]["valido"] and cuerpo["estado"] in {"en cola", "procesando", "listo"}
    est = esperar(cliente, cuerpo["id"])
    assert est["estado"] == "listo" and est["progreso"] == 100 and est["error"] is None
    assert est["expira"] - est["creado"] == pytest.approx(24 * 3600)
    tarjetas = est["resumen"]["tarjetas"]
    assert [t["control"] for t in tarjetas] == [
        "RESULTADO GENERAL", "NETVALLE vs SIAT", "NETVALLE vs SAP",
        "FACTURAS PARA REVISAR", "AJUSTES SAP NEUTRALIZADOS", "LIBROS EXENTOS"]
    assert tarjetas[0]["resultado"] == "REVISAR" and tarjetas[1]["resultado"] == "TODO CUADRA"
    assert tarjetas[4]["resultado"] == "SIN EFECTO NETO"
    assert est["resumen"]["observaciones_total"] == tarjetas[3]["cantidad"] == 13


def test_job_con_error_de_negocio_informa_el_motivo(cliente, archivos_sinteticos, tmp_path):
    falso = tmp_path / "CRUCE_MALO.xlsx"
    pd.DataFrame({"a": [1]}).to_excel(falso, sheet_name="NETVALLE", index=False)
    r = cliente.post("/api/controles", files=_files([str(falso), archivos_sinteticos[1]]))
    assert r.status_code == 202
    est = esperar(cliente, r.json()["id"])
    assert est["estado"] == "error"
    assert "El archivo del motor 1 debe incluir: RESUMEN_CRUCE, SIAT" in est["error"]


def test_correccion_manual_de_clasificacion(cliente, archivos_sinteticos, tmp_path):
    extra = tmp_path / "SAP_extra_sin_cuentas.xlsx"
    pd.DataFrame({"x": [1]}).to_excel(extra, index=False)  # el auto-clasificador lo rechazaría
    todos = [*archivos_sinteticos, str(extra)]
    assert cliente.post("/api/controles", files=_files(todos)).status_code == 422
    r = cliente.post("/api/controles", files=_files(todos), data={"netvalle": "CRUCE.xlsx", "sap": ["SAP.xlsx"]})
    assert r.status_code == 202
    assert esperar(cliente, r.json()["id"])["estado"] == "listo"


@pytest.mark.parametrize("datos,mensaje", [
    ({"netvalle": "CRUCE.xlsx"}, "Falta indicar al menos un archivo SAP"),
    ({"sap": ["SAP.xlsx"]}, "Falta indicar el archivo NETVALLE"),
    ({"netvalle": "SAP.xlsx", "sap": ["CRUCE.xlsx"]}, "no contiene las hojas NETVALLE"),
    ({"netvalle": "CRUCE.xlsx", "sap": ["CRUCE.xlsx"]}, "no puede ser NETVALLE y SAP"),
    ({"netvalle": "CRUCE.xlsx", "sap": ["NO_EXISTE.xlsx"]}, "no fue enviado"),
])
def test_correccion_manual_invalida(cliente, archivos_sinteticos, datos, mensaje):
    r = subir(cliente, archivos_sinteticos, **datos)
    assert r.status_code == 422 and mensaje in r.json()["detail"]


def test_id_inexistente_404(cliente):
    for ruta in ("", "/observaciones", "/excel"):
        assert cliente.get(f"/api/controles/noexiste{ruta}").status_code == 404


def test_observaciones_y_excel_antes_de_terminar_409(cliente, archivos_sinteticos, monkeypatch):
    import threading
    freno = threading.Event()
    import api.jobs as jobs
    original = jobs.generar_control
    monkeypatch.setattr(jobs, "generar_control", lambda *a, **k: (freno.wait(10), original(*a, **k))[1])
    jid = subir(cliente, archivos_sinteticos).json()["id"]
    assert cliente.get(f"/api/controles/{jid}/observaciones").status_code == 409
    assert cliente.get(f"/api/controles/{jid}/excel").status_code == 409
    freno.set()
    assert esperar(cliente, jid)["estado"] == "listo"


# ---------------- observaciones: paginación, filtros, búsqueda y orden
def obs(cliente, jid, **p):
    r = cliente.get(f"/api/controles/{jid}/observaciones", params=p)
    assert r.status_code == 200, r.text
    return r.json()


def test_observaciones_paginacion(listo):
    c, jid = listo
    p1 = obs(c, jid, por_pagina=4, pagina=1)
    assert p1["total"] == 13 and p1["paginas"] == 4 and len(p1["filas"]) == 4
    assert len(obs(c, jid, por_pagina=4, pagina=3)["filas"]) == 4
    assert obs(c, jid, por_pagina=4, pagina=9)["filas"] == []
    assert "FACTURA" in p1["columnas"] and "QUÉ REVISAR" in p1["columnas"]


def test_observaciones_filtros_y_busqueda(listo):
    c, jid = listo
    assert obs(c, jid, control="SAP sin coincidencia")["total"] == 1
    assert obs(c, jid, control="NETVALLE vs SAP")["total"] == 11
    assert obs(c, jid, punto="SFC103")["total"] == 4
    assert obs(c, jid, q="2003")["filas"][0]["FACTURA"] == "2003"
    assert obs(c, jid, q="2003".lower(), punto="SFC001")["total"] == 0
    assert obs(c, jid, q="no-existe-xyz")["total"] == 0
    f = obs(c, jid)["filtros"]
    assert f["PUNTO"] == ["SFC001", "SFC103"] and "SAP sin coincidencia" in f["CONTROL"]


def test_observaciones_orden(listo):
    c, jid = listo
    asc = [x["FACTURA"] for x in obs(c, jid, orden="FACTURA", direccion="asc")["filas"]]
    desc = [x["FACTURA"] for x in obs(c, jid, orden="FACTURA", direccion="desc")["filas"]]
    assert asc == sorted(asc) and desc == sorted(desc, reverse=True)
    assert c.get(f"/api/controles/{jid}/observaciones", params={"orden": "NOPE"}).status_code == 422
    assert c.get(f"/api/controles/{jid}/observaciones", params={"direccion": "x"}).status_code == 422


def test_observaciones_json_valido_con_nulos(listo):
    c, jid = listo
    fila = next(x for x in obs(c, jid, control="SAP sin coincidencia")["filas"])
    assert fila["TOTAL FACTURA NETVALLE Bs"] is None and fila["IVA ESPERADO Bs"] is None  # NaN -> null


# ---------------- Excel
def test_excel_mismas_hojas_columnas_y_contenido_que_core(listo, archivos_sinteticos, tmp_path):
    c, jid = listo
    r = c.get(f"/api/controles/{jid}/excel")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(XLSX)
    assert "CONTROL_TRIBUTARIO_INTEGRAL_V3.xlsx" in r.headers["content-disposition"]
    ruta = tmp_path / "api.xlsx"
    ruta.write_bytes(r.content)
    esperado = tmp_path / "core.xlsx"
    generar_control(archivos_sinteticos[0], [archivos_sinteticos[1]], archivo_salida=str(esperado))
    assert load_workbook(ruta).sheetnames == ["RESUMEN_EJECUTIVO", "OBSERVACIONES", "NETVALLE", "SAP"]
    for hoja in ["RESUMEN_EJECUTIVO", "OBSERVACIONES", "NETVALLE", "SAP"]:
        a = pd.read_excel(ruta, sheet_name=hoja, dtype=object, keep_default_na=False)
        b = pd.read_excel(esperado, sheet_name=hoja, dtype=object, keep_default_na=False)
        pd.testing.assert_frame_equal(a, b, check_dtype=False)
    wa, wb_ = load_workbook(ruta), load_workbook(esperado)
    for hoja in wa.sheetnames:
        assert wa[hoja].freeze_panes == wb_[hoja].freeze_panes and wa[hoja].auto_filter.ref == wb_[hoja].auto_filter.ref


# ---------------- expiración y limpieza
def test_resultados_expiran_y_se_borran(tmp_path, archivos_sinteticos):
    manager = JobManager(ttl_horas=0, workers=1, base_dir=tmp_path / "jobs")
    c = TestClient(crear_app(Settings(auth_enabled=False), manager))
    jid = c.post("/api/controles", files=_files(archivos_sinteticos)).json()["id"]
    fin = time.time() + 30
    while time.time() < fin and manager._jobs.get(jid) and manager._jobs[jid].estado not in ("listo", "error"):
        time.sleep(0.05)
    carpeta = manager.base / jid
    assert c.get(f"/api/controles/{jid}").status_code == 404   # ttl=0: vencido apenas termina
    assert not carpeta.exists()


def test_archivos_de_entrada_se_borran_al_terminar(listo):
    c, jid = listo
    carpeta = c.manager.base / jid
    assert [p.name for p in carpeta.iterdir()] == ["CONTROL_TRIBUTARIO_INTEGRAL_V3.xlsx"]


def test_no_hay_datos_en_logs(cliente, archivos_sinteticos, caplog):
    caplog.set_level(logging.DEBUG)
    jid = subir(cliente, archivos_sinteticos).json()["id"]
    esperar(cliente, jid)
    texto = " ".join(r.getMessage() for r in caplog.records)
    for dato in ("CRUCE.xlsx", "SAP.xlsx", "SFC001", "SFC103", "1001", "A1001", "13.0"):
        assert dato not in texto
    assert jid in texto  # solo ids y estados
