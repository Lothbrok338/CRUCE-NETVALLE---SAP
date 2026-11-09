import pandas as pd
import pytest

from core.sap import (grupo_sap_neutralizado, preparar_sap, resumir_sap,
                      vincular_reversos_manuales)
from tests import datos_sinteticos as ds


def _sap(filas):
    return pd.DataFrame(filas)


def test_preparar_sap_iva_llave_y_sin_errores():
    df = preparar_sap(_sap([ds.iva("SFC001", 1001, "50", -13.0, "A1")]), "IVA")
    fila = df.iloc[0]
    assert fila["_LLAVE"] == "SFC001|1001|20260110"
    assert fila["_FACTURA"] == 1001 and fila["_CLAVE"] == "50" and fila["_ERROR"] == ""
    assert fila["_METODO_VINCULO"] == "LLAVE DIRECTA"


def test_preparar_sap_errores_de_lectura():
    filas = [
        ds.it("SFC001", 1, "40", 3.0, "T1"),                                  # cuenta distinta (IVA esperado)
        ds._sap(ds.CUENTA_IVA, "", 2, "50", -1.0, "A2"),                      # punto vacío
        ds._sap(ds.CUENTA_IVA, "SFC001", 0, "50", -1.0, "A3", texto="nada"),  # sin factura
        ds._sap(ds.CUENTA_IVA, "SFC001", 4, "99", -1.0, "A4"),                # clave inesperada
        ds._sap(ds.CUENTA_IVA, "SFC001", 5, "50", None, "A5"),                # importe vacío
    ]
    err = preparar_sap(_sap(filas), "IVA")["_ERROR"].tolist()
    assert "CUENTA DISTINTA DE 210106001" in err[0]
    assert "PUNTO VACÍO" in err[1] and "LLAVE" not in err[1]
    assert "FACTURA NO INTERPRETABLE" in err[2]
    assert "CLAVE 99 NO ESPERADA" in err[3]
    assert "IMPORTE VACÍO" in err[4]


def test_preparar_sap_falta_columna():
    with pytest.raises(Exception, match="El reporte SAP IVA no contiene: Asiento contable"):
        preparar_sap(_sap([ds.iva("SFC001", 1, "50", -1.0, "A")]).drop(columns=["Asiento contable"]), "IVA")


def _iva_prep(filas):
    return preparar_sap(_sap(filas), "IVA")


def test_reverso_manual_se_vincula_si_candidato_unico():
    df = vincular_reversos_manuales(_iva_prep([
        ds.iva("SFC001", 5001, "50", -13.0, "O"), ds.iva("USUARIO1", 5001, "40", 13.0, "R")]), "IVA")
    rev = df[df["_ASIENTO"] == "R"].iloc[0]
    assert rev["_LLAVE"] == "SFC001|5001|20260110"
    assert rev["_PUNTO_VINCULADO"] == "SFC001"
    assert rev["_METODO_VINCULO"] == "REVERSO MANUAL VINCULADO POR FACTURA + FECHA + IMPORTE"
    assert rev["_ERROR"] == ""


def test_reverso_manual_ambiguo_no_se_vincula():
    df = vincular_reversos_manuales(_iva_prep([
        ds.iva("SFC001", 5001, "50", -13.0, "O1"), ds.iva("SFC002", 5001, "50", -13.0, "O2"),
        ds.iva("USUARIO1", 5001, "40", 13.0, "R")]), "IVA")
    rev = df[df["_ASIENTO"] == "R"].iloc[0]
    assert rev["_METODO_VINCULO"] == "REVERSO MANUAL AMBIGUO"
    assert rev["_ERROR"].startswith("REVERSO MANUAL AMBIGUO")


def test_reverso_manual_sin_candidato_importe_distinto():
    df = vincular_reversos_manuales(_iva_prep([
        ds.iva("SFC001", 5001, "50", -13.0, "O"), ds.iva("USUARIO1", 5001, "40", 9.0, "R")]), "IVA")
    rev = df[df["_ASIENTO"] == "R"].iloc[0]
    assert rev["_METODO_VINCULO"] == "LLAVE DIRECTA" and rev["_LLAVE"].startswith("USUARIO1|")


def test_reverso_con_llave_directa_no_se_toca():
    df = vincular_reversos_manuales(_iva_prep([
        ds.iva("SFC001", 1, "50", -13.0, "O"), ds.iva("SFC001", 1, "40", 13.0, "R")]), "IVA")
    assert (df["_METODO_VINCULO"] == "LLAVE DIRECTA").all()


def test_resumir_sap_cantidades_montos_y_saldo():
    df = _iva_prep([
        ds.iva("SFC001", 1, "50", -13.0, "O1"), ds.iva("SFC001", 1, "50", -13.0, "O2"),
        ds.iva("SFC001", 1, "40", 13.0, "R1"),
        ds.iva("SFC001", 2, "50", -26.0, "O3"),
    ])
    r = resumir_sap(df, "IVA")
    a = r.loc["SFC001|1|20260110"]
    assert (a["CANT_ORIGINAL"], a["CANT_REVERSO"]) == (2, 1)
    assert a["MONTO_ORIGINAL"] == 26.0 and a["MONTO_REVERSO"] == 13.0 and a["SALDO"] == -13.0
    assert a["ASIENTOS_ORIGINAL"] == "O1 / O2" and a["ASIENTOS_REVERSO"] == "R1"
    b = r.loc["SFC001|2|20260110"]
    assert (b["CANT_REVERSO"], b["MONTO_REVERSO"], b["ASIENTOS_REVERSO"]) == (0, 0.0, "")


def test_resumir_sap_excluye_filas_con_error():
    df = _iva_prep([ds._sap(ds.CUENTA_IVA, "SFC001", 0, "50", -1.0, "X", texto="nada")])
    assert resumir_sap(df, "IVA").empty


def _grupo(filas_iva=(), filas_it=()):
    partes = []
    if filas_iva:
        partes.append(_iva_prep(list(filas_iva)))
    if filas_it:
        partes.append(preparar_sap(_sap(list(filas_it)), "IT"))
    return pd.concat(partes, ignore_index=True)


def test_grupo_neutralizado_original_mas_reverso_cero():
    g = _grupo([ds.iva("S", 1, "50", -13.0, "a"), ds.iva("S", 1, "40", 13.0, "b")])
    assert grupo_sap_neutralizado(g) is True


def test_grupo_neutralizado_iva_e_it():
    g = _grupo([ds.iva("S", 1, "50", -13.0, "a"), ds.iva("S", 1, "40", 13.0, "b")],
               [ds.it("S", 1, "40", 3.0, "c"), ds.it("S", 1, "50", -3.0, "d")])
    assert grupo_sap_neutralizado(g) is True


@pytest.mark.parametrize("filas", [
    [("50", -13.0)],                                  # sin reverso
    [("50", -13.0), ("40", 10.0)],                    # saldo distinto de cero
    [("40", 13.0), ("40", -13.0)],                    # falta clave 50
])
def test_grupo_no_neutralizado(filas):
    g = _grupo([ds.iva("S", 1, c, i, f"x{k}") for k, (c, i) in enumerate(filas)])
    assert grupo_sap_neutralizado(g) is False


def test_grupo_iva_neutralizado_pero_it_no():
    g = _grupo([ds.iva("S", 1, "50", -13.0, "a"), ds.iva("S", 1, "40", 13.0, "b")],
               [ds.it("S", 1, "40", 3.0, "c")])
    assert grupo_sap_neutralizado(g) is False


def test_grupo_vacio_o_none():
    assert grupo_sap_neutralizado(None) is False
    assert grupo_sap_neutralizado(pd.DataFrame(columns=["_TIPO", "_CLAVE", "_IMPORTE"])) is False
