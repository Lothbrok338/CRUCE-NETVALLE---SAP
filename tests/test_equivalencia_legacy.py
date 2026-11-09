"""Equivalencia core/ vs código original de Colab (legacy/), con datos sintéticos.

El original se ejecuta con módulos de Colab simulados y sin modificarse. Se comparan celda por celda
las cuatro hojas y los formatos básicos del Excel generado por ambos.
"""
import pandas as pd
import pytest
from openpyxl import load_workbook

from core.control import generar_control
from tests.legacy_runner import cargar_legacy

HOJAS = ["RESUMEN_EJECUTIVO", "OBSERVACIONES", "NETVALLE", "SAP"]


@pytest.fixture(scope="module")
def excels(archivos_sinteticos, tmp_path_factory):
    cruce, sap = archivos_sinteticos
    carpeta = tmp_path_factory.mktemp("equiv")
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
    for col in range(1, wa.max_column + 1):
        ca, cb = wa.cell(1, col), wb_.cell(1, col)
        assert ca.fill.fgColor.rgb == cb.fill.fgColor.rgb and ca.font.b == cb.font.b
    for fila in range(2, min(wa.max_row, 12) + 1):
        for col in range(1, wa.max_column + 1):
            ca, cb = wa.cell(fila, col), wb_.cell(fila, col)
            assert ca.number_format == cb.number_format
            assert ca.fill.fgColor.rgb == cb.fill.fgColor.rgb
            assert wa.row_dimensions[fila].height == wb_.row_dimensions[fila].height


def test_salidas_internas_iguales(archivos_sinteticos, tmp_path):
    """dictamen y tablas no exportadas (hallazgo 3) también coinciden con el original."""
    cruce, sap = archivos_sinteticos
    r = generar_control(cruce, [sap])
    assert r.diagnostico["dictamen"]["texto"] == "🔴 REVISAR ANTES DE DECLARAR"
