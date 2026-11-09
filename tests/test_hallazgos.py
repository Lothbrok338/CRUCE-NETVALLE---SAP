"""Pruebas de caracterización de los hallazgos (docs/HALLAZGOS.md).

Documentan el comportamiento ACTUAL del original, que core/ conserva. Si alguien corrige un hallazgo
por decisión de negocio, la prueba correspondiente debe actualizarse a propósito.
"""
import ast
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

from core.control import generar_control
from core.llaves import extraer_factura_sap
from core.texto import normalizar_entero


@pytest.fixture(scope="module")
def res(archivos_sinteticos):
    cruce, sap = archivos_sinteticos
    return generar_control(cruce, [sap])


def test_h1_filas_con_error_no_llegan_a_observaciones(res):
    errores = res.sap[res.sap["ERROR DE LECTURA"].astype(str) != ""]
    assert len(errores) == 1 and errores.iloc[0]["Asiento contable"] == "A9999"
    # se calculan y cuentan en el diagnóstico...
    assert len(res.diagnostico["errores_sap"]) >= 1
    # ...aparecen solo en la hoja SAP, NO en OBSERVACIONES ni en las tarjetas
    assert "A9999" not in " ".join(res.observaciones["ASIENTO SAP"].astype(str))
    assert "ERROR" not in " ".join(res.ejecutivo["QUÉ SIGNIFICA"].astype(str)).upper()


def test_h2_dos_calculos_de_sap_sin_netvalle_no_son_equivalentes(res):
    """construir_sap_sin_netvalle (solo dictamen) != sap_sin_justificar (el que se exporta)."""
    primero = set(res.diagnostico["sap_sin_netvalle"]["NÚMERO DE FACTURA"].astype(int))
    segundo = {int(f) for f in res.observaciones.loc[res.observaciones["CONTROL"].eq("SAP sin coincidencia"), "FACTURA"]}
    assert segundo == {9002}
    assert primero == {6001, 9002}           # 6001: anulada en NETVALLE, SAP la registró con otra fecha
    assert primero != segundo                # => NO se puede unificar sin decisión de negocio


def test_h3_salidas_calculadas_pero_no_exportadas(res, archivos_sinteticos, tmp_path):
    assert {"resumen", "dictamen", "observaciones_originales"} <= set(res.diagnostico)
    ruta = tmp_path / "x.xlsx"
    generar_control(archivos_sinteticos[0], [archivos_sinteticos[1]], archivo_salida=str(ruta))
    assert load_workbook(ruta).sheetnames == ["RESUMEN_EJECUTIVO", "OBSERVACIONES", "NETVALLE", "SAP"]


@pytest.mark.parametrize("texto", ["F-123", "F 123", "F.123", "F123"])
def test_h4_regex_factura_casos_pedidos(texto):
    assert extraer_factura_sap(texto) == 123


@pytest.mark.parametrize("texto,esperado", [("1234.0", 1234), ("1234,0", 1234), ("1234", 1234)])
def test_h4_normalizar_entero_casos_pedidos(texto, esperado):
    assert normalizar_entero(texto) == esperado


def test_h4_el_escape_doble_tambien_acepta_barra_invertida():
    """Efecto del `\\\\` en el original: además de . : # -, acepta una barra invertida literal."""
    assert extraer_factura_sap("F\\123") == 123
    assert normalizar_entero("1234\\0") == 1234


def test_h5_core_sin_dependencias_de_colab_ni_web():
    prohibidos = {"google", "IPython", "ipywidgets", "fastapi", "starlette", "flask", "django", "uvicorn"}
    for archivo in Path("core").glob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Import):
                mods = [a.name.split(".")[0] for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                mods = [(nodo.module or "").split(".")[0]]
            else:
                continue
            assert not (set(mods) & prohibidos), (archivo, mods)
        assert "!pip" not in archivo.read_text(encoding="utf-8")


def test_h6_anuladas_e_incompletas_con_revisar_no_llegan_a_observaciones(res):
    net = res.netvalle
    pendientes = net[net["RESULTADO CONTROL"].str.contains("REVISAR") & net["ESTADO"].isin(["A", "I"])]
    assert set(pendientes["Nº DE FACTURA"].astype(int)) == {3003, 3004, 3005, 3006, 3008, 4001}
    assert not (set(pendientes["Nº DE FACTURA"].astype(int).astype(str)) & set(res.observaciones["FACTURA"]))


def test_h7_encabezados_sin_relleno_en_celdas_con_datos(archivos_sinteticos, tmp_path):
    ruta = tmp_path / "x.xlsx"
    generar_control(archivos_sinteticos[0], [archivos_sinteticos[1]], archivo_salida=str(ruta))
    ws = load_workbook(ruta)["OBSERVACIONES"]
    assert ws["A1"].fill.patternType is None   # el color de encabezado no se aplica sobre los datos
