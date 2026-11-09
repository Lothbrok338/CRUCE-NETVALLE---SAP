import pandas as pd
import pytest

from core.netvalle import preparar_netvalle


def _df(filas):
    return pd.DataFrame([
        {"PUNTO DE EMISIÓN": p, "Nº DE FACTURA": f, "FECHA": "2026-01-10",
         "TOTAL FACTURA (A)": t, "DÉBITO FISCAL": d, "ESTADO": e}
        for p, f, e, t, d in filas])


def test_tratamientos_y_montos():
    df = preparar_netvalle(_df([
        ("SFC001", 1, "V", 100.0, 13.0),     # gravada
        ("SFC001", 2, "V", 100.0, 0.0),      # exento
        ("SFC103", 3, "V", 100.0, 13.0),     # souvenir
        ("SFC001", 4, "A", 100.0, 13.0),     # anulada
        ("SFC001", 5, "I", 100.0, 13.0),     # incompleta
        ("SFC103", 6, "I", 100.0, 13.0),     # incompleta souvenir
        ("SFC103", 7, "V", 100.0, 0.0),      # souvenir con débito 0 NO es exento
    ]))
    assert df["_TRATAMIENTO"].tolist() == [
        "VENTA GRAVADA - IVA 13%", "LIBRO - EXENTO IVA E IT", "SOUVENIR - IVA 13% + IT 3%",
        "ANULADA", "INCOMPLETA - REVISAR", "INCOMPLETA - REVISAR", "SOUVENIR - IVA 13% + IT 3%"]
    assert df["_IVA_ESPERADO"].iloc[[0, 1, 2, 4, 5]].tolist() == [13.0, 0.0, 13.0, 13.0, 13.0]
    assert pd.isna(df["_IVA_ESPERADO"].iloc[3])
    assert df["_IT_ESPERADO"].iloc[[1, 2, 5]].tolist() == [0.0, 3.0, 3.0]
    assert df["_IT_ESPERADO"].iloc[[0, 3, 4]].isna().all()
    assert df["_EXENTO"].tolist() == [False, True, False, False, False, False, False]
    assert df["_SOUVENIR"].tolist() == [False, False, True, False, False, True, True]


def test_llave_y_estado_normalizados():
    df = preparar_netvalle(_df([("sfc001 ", "12.0", "Válida", 1.0, 0.13)]))
    assert df["_LLAVE"].iloc[0] == "SFC001|12|20260110"
    assert df["_ESTADO"].iloc[0] == "V"


def test_columna_faltante_lanza_error_con_texto_original():
    with pytest.raises(Exception, match="NETVALLE no contiene: DÉBITO FISCAL"):
        preparar_netvalle(_df([("SFC001", 1, "V", 1, 1)]).drop(columns=["DÉBITO FISCAL"]))
