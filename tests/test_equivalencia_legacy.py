"""Equivalencia core/ vs código original de Colab (legacy/), con datos sintéticos.

Diferencias deliberadas (decisiones del usuario, docs/HALLAZGOS.md): las facturas INCOMPLETAS ahora van a
OBSERVACIONES, y los errores de lectura SAP también (por eso este dataset no incluye ni unas ni otros) los encabezados del Excel ahora llevan color y QUÉ PASÓ muestra el motivo real.

El original se ejecuta con módulos de Colab simulados y sin modificarse. Se comparan celda por celda
las cuatro hojas y los formatos básicos del Excel generado por ambos.
"""
import pandas as pd
import pytest
from openpyxl import load_workbook

from core.control import generar_control
from tests.datos_sinteticos import crear_archivos
from tests.legacy_runner import cargar_legacy

HOJAS = ["RESUMEN_EJECUTIVO", "OBSERVACIONES", "NETVALLE", "SAP"]


@pytest.fixture(scope="module")
def excels(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("equiv")
    cruce, sap = crear_archivos(carpeta, incluir_incompletas=False)
    legacy = cargar_legacy()
    ruta_legacy = carpeta / "legacy.xlsx"
    legacy["ARCHIVO_FINAL"] = str(ruta_legacy)
    legacy["generar_control"](cruce, [sap])
    ruta_core = carpeta / "core.xlsx"
    generar_control(cruce, [sap], archivo_salida=str(ruta_core))
    return ruta_legacy, ruta_core


@pytest.mark.parametrize("hoja", HOJAS)
def test_hoja_identica_celda_por_celda(excels, hoja):
    a = pd.read_excel(excels[0], sheet_name=hoja, dtype=object, keep_default_na=False)
    b = pd.read_excel(excels[1], sheet_name=hoja, dtype=object, keep_default_na=False)
    assert list(a.columns) == list(b.columns)
    if hoja == "OBSERVACIONES":  # diferencia deliberada (hallazgo 8): QUÉ PASÓ / QUÉ REVISAR llevan el motivo real
        a, b = a.drop(columns=["QUÉ PASÓ", "QUÉ REVISAR"]), b.drop(columns=["QUÉ PASÓ", "QUÉ REVISAR"])
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def test_mismas_hojas_en_el_mismo_orden(excels):
    assert load_workbook(excels[0]).sheetnames == load_workbook(excels[1]).sheetnames == HOJAS


@pytest.mark.parametrize("hoja", HOJAS)
def test_mismo_formato_visual(excels, hoja):
    wa, wb_ = load_workbook(excels[0])[hoja], load_workbook(excels[1])[hoja]
    assert wa.freeze_panes == wb_.freeze_panes
    assert wa.auto_filter.ref == wb_.auto_filter.ref
    assert wa.sheet_view.showGridLines == wb_.sheet_view.showGridLines
    anchos = lambda ws: {k: round(v.width, 2) for k, v in ws.column_dimensions.items()}
    assert anchos(wa) == anchos(wb_)
    colores = {"RESUMEN_EJECUTIVO": "1F4E78", "OBSERVACIONES": "C00000", "NETVALLE": "1F4E78", "SAP": "5B9BD5"}
    for col in range(1, wa.max_column + 1):
        ca, cb = wa.cell(1, col), wb_.cell(1, col)
        assert ca.value == cb.value and ca.font.b == cb.font.b
        assert ca.fill.patternType is None                       # original: sin relleno (hallazgo 7)
        assert cb.fill.fgColor.rgb.endswith(colores[hoja])       # core: encabezado coloreado
    for fila in range(2, min(wa.max_row, 12) + 1):
        for col in range(1, wa.max_column + 1):
            ca, cb = wa.cell(fila, col), wb_.cell(fila, col)
            assert ca.number_format == cb.number_format
            assert ca.fill.fgColor.rgb == cb.fill.fgColor.rgb
            assert wa.row_dimensions[fila].height == wb_.row_dimensions[fila].height
