"""generar_control de punta a punta con datos sintéticos."""
import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook

from core.control import generar_control
from tests import datos_sinteticos as ds

HOJAS = ["RESUMEN_EJECUTIVO", "OBSERVACIONES", "NETVALLE", "SAP"]
COLS_EJECUTIVO = ["CONTROL", "RESULTADO", "CANTIDAD", "TOTAL FACTURAS Bs", "DATO CLAVE", "QUÉ SIGNIFICA", "QUÉ HACER"]
COLS_OBS = ["CONTROL", "FACTURA", "PUNTO", "FECHA NETVALLE", "TOTAL FACTURA NETVALLE Bs", "QUÉ PASÓ",
            "ASIENTO SAP", "FECHA SAP", "IVA ESPERADO Bs", "IVA SAP Bs", "IT ESPERADO Bs", "IT SAP Bs", "QUÉ REVISAR"]
COLS_NETVALLE_CONTROL = [
    "RESULTADO CONTROL", "TRATAMIENTO TRIBUTARIO", "LLAVE CONTROL", "IVA ESPERADO", "IVA SAP ORIGINAL",
    "DIFERENCIA IVA", "CANT. ORIGINAL IVA", "CANT. REVERSO IVA", "ASIENTO IVA ORIGINAL", "ASIENTO IVA REVERSO",
    "SALDO IVA SAP", "IT ESPERADO", "IT SAP ORIGINAL", "DIFERENCIA IT", "CANT. ORIGINAL IT",
    "CANT. REVERSO IT", "ASIENTO IT ORIGINAL", "ASIENTO IT REVERSO", "SALDO IT SAP"]
COLS_SAP_TECNICAS = [
    "TIPO REPORTE", "LLAVE CONTROL", "LLAVE REPORTADA SAP", "FACTURA EXTRAÍDA", "PUNTO NORMALIZADO",
    "PUNTO VINCULADO", "MÉTODO DE VINCULACIÓN", "FECHA NORMALIZADA", "CLAVE NORMALIZADA",
    "IMPORTE NORMALIZADO", "ERROR DE LECTURA"]


@pytest.fixture(scope="module")
def resultado(archivos_sinteticos):
    cruce, sap = archivos_sinteticos
    return generar_control(cruce, [sap])


def test_cada_factura_recibe_su_resultado_esperado(resultado):
    net = resultado.netvalle
    obtenido = {(r["PUNTO DE EMISIÓN"], None if pd.isna(r["Nº DE FACTURA"]) else int(r["Nº DE FACTURA"])):
                r["RESULTADO CONTROL"] for _, r in net.iterrows()}
    esperado = {(p, f): res for p, f, _e, _t, _d, res in ds.NETVALLE}
    assert obtenido == esperado


def test_hojas_y_columnas_del_contrato(resultado):
    assert [h[0] for h in resultado.hojas] == HOJAS
    assert list(resultado.ejecutivo.columns) == COLS_EJECUTIVO
    assert list(resultado.observaciones.columns) == COLS_OBS
    assert list(resultado.netvalle.columns[:19]) == COLS_NETVALLE_CONTROL
    assert list(resultado.sap.columns[:11]) == COLS_SAP_TECNICAS
    # las columnas originales de NETVALLE van después, en su orden original
    assert list(resultado.netvalle.columns[19:]) == [
        "PUNTO DE EMISIÓN", "Nº DE FACTURA", "FECHA", "TOTAL FACTURA (A)", "DÉBITO FISCAL", "ESTADO"]


def test_resumen_ejecutivo_seis_tarjetas(resultado):
    e = resultado.ejecutivo.set_index("CONTROL")
    assert list(e.index) == ["RESULTADO GENERAL", "NETVALLE vs SIAT", "NETVALLE vs SAP",
                             "FACTURAS PARA REVISAR", "AJUSTES SAP NEUTRALIZADOS", "LIBROS EXENTOS"]
    assert e.loc["RESULTADO GENERAL", "RESULTADO"] == "REVISAR"
    assert e.loc["NETVALLE vs SIAT", "RESULTADO"] == "TODO CUADRA"
    assert e.loc["AJUSTES SAP NEUTRALIZADOS", "RESULTADO"] == "SIN EFECTO NETO"
    assert e.loc["AJUSTES SAP NEUTRALIZADOS", "CANTIDAD"] == 1          # 9001
    assert e.loc["LIBROS EXENTOS", "CANTIDAD"] == 2                      # 1006 y 1007
    assert e.loc["LIBROS EXENTOS", "RESULTADO"] == "INFORMATIVO"
    assert e.loc["FACTURAS PARA REVISAR", "CANTIDAD"] == len(resultado.observaciones)


def test_observaciones_agrupan_por_factura_y_excluyen_los_ok(resultado):
    obs = resultado.observaciones
    facturas_obs = set(obs["FACTURA"])
    ok = {"1001", "1006", "2001", "3002", "3007", "5001"}
    assert not (facturas_obs & ok)
    # Solo facturas VÁLIDAS (ver hallazgo 6: las anuladas/incompletas con REVISAR no llegan aquí)
    assert {"1002", "1003", "1004", "1005", "1007", "2002", "2003", "2004", "2005", "9002"} <= facturas_obs
    # SAP sin NETVALLE real aparece una vez; el ajuste neutralizado (9001) no aparece
    assert (obs["CONTROL"].eq("SAP sin coincidencia")).sum() == 1
    assert "9001" not in facturas_obs


def test_reverso_manual_queda_incorporado(resultado):
    s = resultado.sap
    reverso = s[(s["Asiento contable"] == "A5001b")].iloc[0]
    assert reverso["MÉTODO DE VINCULACIÓN"] == "REVERSO MANUAL VINCULADO POR FACTURA + FECHA + IMPORTE"
    assert reverso["PUNTO VINCULADO"] == "SFC001"


def test_ignora_otras_cuentas(resultado):
    assert not resultado.sap["Cuenta de mayor"].astype(str).eq("999999999").any()


def test_escribe_excel_con_las_cuatro_hojas(archivos_sinteticos, tmp_path):
    cruce, sap = archivos_sinteticos
    ruta = tmp_path / "salida.xlsx"
    generar_control(cruce, [sap], archivo_salida=str(ruta))
    wb = load_workbook(ruta)
    assert wb.sheetnames == HOJAS
    for hoja in HOJAS:
        ws = wb[hoja]
        assert ws.freeze_panes == "A2" and ws.auto_filter.ref
    assert wb["RESUMEN_EJECUTIVO"]["A1"].font.b  # encabezado en negrita (el color: ver hallazgo 7)


def test_no_escribe_si_no_se_pide(archivos_sinteticos, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cruce, sap = archivos_sinteticos
    generar_control(cruce, [sap])
    assert list(tmp_path.glob("*.xlsx")) == []


def test_exige_hojas_del_motor_1(tmp_path, archivos_sinteticos):
    _, sap = archivos_sinteticos
    falso = tmp_path / "falso.xlsx"
    pd.DataFrame({"a": [1]}).to_excel(falso, sheet_name="NETVALLE", index=False)
    with pytest.raises(ValueError, match="El archivo del motor 1 debe incluir: RESUMEN_CRUCE, SIAT"):
        generar_control(str(falso), [sap])


def test_sap_sin_ambas_cuentas(tmp_path, archivos_sinteticos):
    cruce, _ = archivos_sinteticos
    solo_iva = tmp_path / "iva.xlsx"
    pd.DataFrame([ds.iva("SFC001", 1, "50", -13.0, "A1")]).to_excel(solo_iva, index=False)
    with pytest.raises(Exception, match="debe contener movimientos de ambas cuentas"):
        generar_control(cruce, [str(solo_iva)])
