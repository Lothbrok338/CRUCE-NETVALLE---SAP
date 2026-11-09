import pandas as pd

from core.impuestos import redondear_impuesto


def test_iva_13_redondeo_half_up():
    # 0.5 * 0.13 = 0.065 -> ROUND_HALF_UP = 0.07 (el redondeo bancario daría 0.06)
    assert redondear_impuesto(0.5, "0.13") == 0.07


def test_it_3_por_ciento():
    assert redondear_impuesto(100, "0.03") == 3.00
    assert redondear_impuesto(0.5, "0.03") == 0.02  # 0.015 -> 0.02


def test_iva_13_caso_normal():
    assert redondear_impuesto(100, "0.13") == 13.00
    assert redondear_impuesto(1234.56, "0.13") == 160.49  # 160.4928


def test_valores_nulos_devuelven_nan():
    assert pd.isna(redondear_impuesto(float("nan"), "0.13"))
    assert pd.isna(redondear_impuesto(None, "0.13"))


def test_valor_invalido_devuelve_nan():
    assert pd.isna(redondear_impuesto("abc", "0.13"))
