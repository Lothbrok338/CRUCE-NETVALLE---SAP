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


def test_h1_errores_de_lectura_van_a_observaciones(res):
    """Prueba a evaluar por el usuario: si no convence, se revierte este bloque."""
    obs = res.observaciones
    fila = obs[obs["CONTROL"] == "SAP error de lectura"].iloc[0]
    assert fila["ASIENTO SAP"] == "A9999"
    assert fila["QUÉ PASÓ"] == "Fila SAP que no se pudo interpretar y quedó fuera del cruce"
    assert "FACTURA NO INTERPRETABLE" in fila["QUÉ REVISAR"] and "cuenta IVA" in fila["QUÉ REVISAR"]
    assert (obs["CONTROL"] == "SAP error de lectura").sum() == 1


def test_h2_sap_con_factura_anulada_en_netvalle_no_se_observa(res):
    """Decisión: si la factura (punto+número) está anulada en NETVALLE y también aparece en SAP, no se observa."""
    sin_coincidencia = {int(f) for f in res.observaciones.loc[res.observaciones["CONTROL"].eq("SAP sin coincidencia"), "FACTURA"]}
    assert sin_coincidencia == {9002}          # 6001 (anulada en NETVALLE, SAP con otra fecha) NO se observa
    assert "6001" not in set(res.observaciones["FACTURA"])


def test_h3_codigo_muerto_eliminado(res, archivos_sinteticos, tmp_path):
    import core.control, core.sap
    assert not hasattr(core.control, "determinar_dictamen") and not hasattr(core.sap, "construir_sap_sin_netvalle")
    assert set(res.diagnostico) == {"errores_sap"}
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


def test_h6_incompletas_van_a_observaciones_y_anuladas_se_ignoran(res):
    obs = res.observaciones
    # incompleta (4001): observada con motivo propio
    fila = obs[obs["FACTURA"] == "4001"].iloc[0]
    assert fila["QUÉ PASÓ"] == "Factura INCOMPLETA en NETVALLE"
    assert "incompleto" in fila["QUÉ REVISAR"]
    # anuladas con REVISAR (3003, 3004, 3005, 3006, 3008): nunca se observan
    assert not ({"3003", "3004", "3005", "3006", "3008"} & set(obs["FACTURA"]))
    assert len(obs) == 13 and res.pendientes_sap == 13


def test_h7_encabezados_con_color_por_hoja(archivos_sinteticos, tmp_path):
    ruta = tmp_path / "x.xlsx"
    generar_control(archivos_sinteticos[0], [archivos_sinteticos[1]], archivo_salida=str(ruta))
    wb = load_workbook(ruta)
    esperado = {"RESUMEN_EJECUTIVO": "1F4E78", "OBSERVACIONES": "C00000", "NETVALLE": "1F4E78", "SAP": "5B9BD5"}
    for hoja, color in esperado.items():
        for celda in wb[hoja][1]:
            assert celda.fill.fgColor.rgb.endswith(color) and celda.font.b and celda.font.color.rgb.endswith("FFFFFF")


def test_h8_que_paso_muestra_el_motivo_real(res):
    """Decisión: QUÉ PASÓ lleva el resultado exacto calculado (texto de contrato)."""
    obs = res.observaciones.set_index("FACTURA")
    assert obs.loc["2003", "QUÉ PASÓ"] == "DUPLICADA EN SAP IT - REVISAR"
    assert obs.loc["2005", "QUÉ PASÓ"] == "DIFERENCIA IMPORTE IT"
    assert obs.loc["1002", "QUÉ PASÓ"] == "FALTA EN SAP IVA"
    assert obs.loc["1004", "QUÉ PASÓ"] == "FACTURA VÁLIDA CON REVERSO IVA - REVISAR"
    assert obs.loc["1005", "QUÉ PASÓ"] == "DIFERENCIA IMPORTE IVA"
