"""Regresión contra archivos REALES (pendiente).

Se habilita cuando el usuario coloque en tests/fixtures/ los archivos de muestra y el Excel generado
por el original, con estos nombres (ignorados por git):
  CRUCE.xlsx, SAP*.xlsx (uno o más) y ESPERADO_CONTROL_TRIBUTARIO_INTEGRAL_V3.xlsx
"""
from pathlib import Path

import pandas as pd
import pytest

from core.clasificacion import clasificar_archivos
from core.control import generar_control

FIX = Path(__file__).parent / "fixtures"
CRUCE = FIX / "CRUCE.xlsx"
ESPERADO = FIX / "ESPERADO_CONTROL_TRIBUTARIO_INTEGRAL_V3.xlsx"
SAPS = sorted(FIX.glob("SAP*.xlsx"))

pytestmark = pytest.mark.skipif(
    not (CRUCE.exists() and ESPERADO.exists() and SAPS),
    reason="PENDIENTE: faltan archivos de muestra y el Excel del original en tests/fixtures/ "
           "(CRUCE.xlsx, SAP*.xlsx, ESPERADO_CONTROL_TRIBUTARIO_INTEGRAL_V3.xlsx).",
)


@pytest.mark.parametrize("hoja", ["RESUMEN_EJECUTIVO", "OBSERVACIONES", "NETVALLE", "SAP"])
def test_hoja_igual_al_original(hoja, tmp_path):
    clasif = clasificar_archivos([str(CRUCE)] + [str(p) for p in SAPS])
    salida = tmp_path / "core.xlsx"
    generar_control(clasif["NETVALLE"][0], clasif["SAP"], archivo_salida=str(salida))
    a = pd.read_excel(ESPERADO, sheet_name=hoja, dtype=object, keep_default_na=False)
    b = pd.read_excel(salida, sheet_name=hoja, dtype=object, keep_default_na=False)
    assert list(a.columns) == list(b.columns)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)
