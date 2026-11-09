import numpy as np
import pandas as pd
import pytest

from core.texto import (buscar_columna, normalizar_entero, normalizar_estado,
                        normalizar_texto, texto_limpio, unir_unicos)


@pytest.mark.parametrize("entrada,esperado", [
    (None, ""), (np.nan, ""), ("nan", ""), ("None", ""), ("<NA>", ""), ("NaT", ""),
    ("  hola \t mundo\n", "hola mundo"),
    ("a\xa0b​c﻿", "a bc"),
    ("x\x00y", "xy"),
    (123, "123"),
])
def test_texto_limpio(entrada, esperado):
    assert texto_limpio(entrada) == esperado


@pytest.mark.parametrize("entrada,esperado", [
    ("Débito  Fiscal", "DEBITO FISCAL"),
    ("Nº de factura", "Nº DE FACTURA"),  # º no se descompone con NFD: se conserva
    ("  emisión ", "EMISION"),
    (None, ""),
])
def test_normalizar_texto(entrada, esperado):
    assert normalizar_texto(entrada) == esperado


@pytest.mark.parametrize("entrada,esperado", [
    (1234, 1234), (np.int64(7), 7), (12.0, 12), (np.float64(5.0), 5),
    ("1234", 1234), ("1234.0", 1234), ("1234,0", 1234), ("1234.00", 1234),
    ("F-123", 123), ("0012", 12),
])
def test_normalizar_entero_valores(entrada, esperado):
    assert normalizar_entero(entrada) == esperado


@pytest.mark.parametrize("entrada", [None, np.nan, "", "sin numero", float("nan")])
def test_normalizar_entero_vacios(entrada):
    assert pd.isna(normalizar_entero(entrada))


@pytest.mark.parametrize("entrada,esperado", [
    ("V", "V"), ("válida", "V"), ("VALIDO", "V"), ("Valid", "V"),
    ("A", "A"), ("Anulada", "A"), ("ANULADO", "A"), ("anul", "A"),
    ("I", "I"), ("incompleta", "I"), ("INCOMPLETO", "I"),
    ("Otro estado", "OTRO ESTADO"), ("", ""),
])
def test_normalizar_estado(entrada, esperado):
    assert normalizar_estado(entrada) == esperado


def test_buscar_columna_ignora_tildes_y_mayusculas():
    cols = ["Punto de Emisión", "otra"]
    assert buscar_columna(cols, "PUNTO DE EMISIÓN") == "Punto de Emisión"
    assert buscar_columna(cols, "no existe") is None


def test_unir_unicos_conserva_orden_y_quita_vacios():
    assert unir_unicos(["b", "a", "b", "", None, "a ", "c"]) == "b / a / c"
