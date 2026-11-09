"""Limpieza y normalización de texto/estado/enteros. Origen: legacy, sección LIMPIEZA Y NORMALIZACIÓN."""

import re
import unicodedata

import numpy as np
import pandas as pd


def texto_limpio(valor):

    if pd.isna(valor):

        return ""

    texto = str(valor)

    texto = texto.replace("\xa0", " ").replace("​", "").replace("﻿", "")

    texto = texto.replace("\t", " ").replace("\r", " ").replace("\n", " ")

    texto = "".join(c for c in texto if unicodedata.category(c)[0] != "C")

    texto = re.sub(r"\s+", " ", texto).strip()

    return "" if texto.lower() in {"nan", "none", "<na>", "nat"} else texto


def normalizar_texto(valor):

    texto = texto_limpio(valor).upper()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")

    return re.sub(r"\s+", " ", texto).strip()


def normalizar_entero(valor):

    if pd.isna(valor):

        return pd.NA

    if isinstance(valor, (int, np.integer)):

        return int(valor)

    if isinstance(valor, (float, np.floating)):

        return pd.NA if pd.isna(valor) else int(valor)

    texto = texto_limpio(valor)

    if re.fullmatch(r"\d+[\\\\.,]0+", texto):

        texto = re.split(r"[\\\\.,]", texto)[0]

    digitos = re.sub(r"\D", "", texto)

    return int(digitos) if digitos else pd.NA


def normalizar_estado(valor):

    estado = normalizar_texto(valor)

    if estado in {"V", "VALIDA", "VALIDO"} or estado.startswith("VALID"):

        return "V"

    if estado in {"A", "ANULADA", "ANULADO"} or estado.startswith("ANUL"):

        return "A"

    if estado in {"I", "INCOMPLETA", "INCOMPLETO"} or estado.startswith("INCOMPL"):

        return "I"

    return estado


def buscar_columna(columnas, nombre):

    objetivo = normalizar_texto(nombre)

    for columna in columnas:

        if normalizar_texto(columna) == objetivo:

            return columna

    return None


def unir_unicos(valores):

    salida = []

    vistos = set()

    for valor in valores:

        texto = texto_limpio(valor)

        if texto and texto not in vistos:

            vistos.add(texto)

            salida.append(texto)

    return " / ".join(salida)
