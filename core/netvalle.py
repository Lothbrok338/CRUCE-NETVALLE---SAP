"""Lectura y preparación de NETVALLE. Origen: legacy, sección LECTURA Y PREPARACIÓN DE NETVALLE."""

import numpy as np
import pandas as pd

from core.clasificacion import hojas_archivo
from core.constantes import PUNTOS_SOUVENIRS, TOLERANCIA
from core.impuestos import redondear_impuesto
from core.llaves import construir_llaves
from core.texto import buscar_columna, normalizar_entero, normalizar_estado, normalizar_texto


def leer_netvalle(ruta):

    hojas = hojas_archivo(ruta)

    mapa = {normalizar_texto(x): x for x in hojas}

    hoja = mapa.get("NETVALLE") or mapa.get("CONSOLIDADO")

    if hoja is None:

        raise Exception("El archivo NETVALLE no contiene las hojas NETVALLE ni CONSOLIDADO.")

    df = pd.read_excel(ruta, sheet_name=hoja, dtype=object, engine="openpyxl")

    df = df.dropna(axis=1, how="all")

    return df, hoja


def preparar_netvalle(df):

    requeridas = [

        "PUNTO DE EMISIÓN", "Nº DE FACTURA", "FECHA", "TOTAL FACTURA (A)",

        "DÉBITO FISCAL", "ESTADO",

    ]

    columnas = {nombre: buscar_columna(df.columns, nombre) for nombre in requeridas}

    faltantes = [nombre for nombre, columna in columnas.items() if columna is None]

    if faltantes:

        raise Exception("NETVALLE no contiene: " + ", ".join(faltantes))

    salida = df.copy()

    salida["_PUNTO"] = salida[columnas["PUNTO DE EMISIÓN"]].map(normalizar_texto)

    salida["_FACTURA"] = salida[columnas["Nº DE FACTURA"]].map(normalizar_entero).astype("Int64")

    salida["_FECHA"] = pd.to_datetime(salida[columnas["FECHA"]], errors="coerce").dt.normalize()

    salida["_TOTAL"] = pd.to_numeric(salida[columnas["TOTAL FACTURA (A)"]], errors="coerce").fillna(0.0)

    salida["_DEBITO"] = pd.to_numeric(salida[columnas["DÉBITO FISCAL"]], errors="coerce").fillna(0.0)

    salida["_ESTADO"] = salida[columnas["ESTADO"]].map(normalizar_estado)

    salida["_LLAVE"] = construir_llaves(salida["_PUNTO"], salida["_FACTURA"], salida["_FECHA"])

    salida["_SOUVENIR"] = salida["_PUNTO"].isin(PUNTOS_SOUVENIRS)

    salida["_EXENTO"] = (

        salida["_ESTADO"].eq("V")

        & ~salida["_SOUVENIR"]

        & salida["_DEBITO"].abs().le(TOLERANCIA)

    )

    tratamientos = []

    iva_esperado = []

    it_esperado = []

    for estado, es_souvenir, es_exento, total in salida[

        ["_ESTADO", "_SOUVENIR", "_EXENTO", "_TOTAL"]

    ].itertuples(index=False, name=None):

        if estado == "A":

            tratamientos.append("ANULADA")

            iva_esperado.append(np.nan)

            it_esperado.append(np.nan)

        elif estado == "I":

            tratamientos.append("INCOMPLETA - REVISAR")

            iva_esperado.append(redondear_impuesto(total, "0.13"))

            it_esperado.append(redondear_impuesto(total, "0.03") if es_souvenir else np.nan)

        elif es_souvenir:

            tratamientos.append("SOUVENIR - IVA 13% + IT 3%")

            iva_esperado.append(redondear_impuesto(total, "0.13"))

            it_esperado.append(redondear_impuesto(total, "0.03"))

        elif es_exento:

            tratamientos.append("LIBRO - EXENTO IVA E IT")

            iva_esperado.append(0.0)

            it_esperado.append(0.0)

        else:

            tratamientos.append("VENTA GRAVADA - IVA 13%")

            iva_esperado.append(redondear_impuesto(total, "0.13"))

            it_esperado.append(np.nan)

    salida["_TRATAMIENTO"] = tratamientos

    salida["_IVA_ESPERADO"] = iva_esperado

    salida["_IT_ESPERADO"] = it_esperado

    return salida
