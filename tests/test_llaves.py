import pandas as pd
import pytest

from core.llaves import construir_llaves, extraer_factura_sap


def test_construir_llaves_formato_punto_factura_fecha():
    puntos = pd.Series(["SFC001", "SFC002"])
    facturas = pd.Series([123, 45], dtype="Int64")
    fechas = pd.Series(pd.to_datetime(["2026-01-10", "2026-12-01"]))
    assert construir_llaves(puntos, facturas, fechas).tolist() == [
        "SFC001|123|20260110", "SFC002|45|20261201"]


def test_construir_llaves_vacia_si_falta_un_componente():
    puntos = pd.Series(["SFC001", "", "SFC003", "SFC004"])
    facturas = pd.Series([1, 2, pd.NA, 4], dtype="Int64")
    fechas = pd.Series(pd.to_datetime(["2026-01-10", "2026-01-10", "2026-01-10", None]))
    assert construir_llaves(puntos, facturas, fechas).tolist() == ["SFC001|1|20260110", "", "", ""]


# Hallazgo 4: casos pedidos por el usuario.
@pytest.mark.parametrize("texto,esperado", [
    ("F-123", 123), ("F 123", 123), ("F.123", 123), ("F123", 123),
    ("f:45", 45), ("F#77", 77), ("Venta F 9001 caja", 9001),
])
def test_extraer_factura_sap(texto, esperado):
    assert extraer_factura_sap(texto) == esperado


@pytest.mark.parametrize("texto", ["SIN REFERENCIA", "", None, "Factura sin numero"])
def test_extraer_factura_sap_sin_match(texto):
    assert pd.isna(extraer_factura_sap(texto))
