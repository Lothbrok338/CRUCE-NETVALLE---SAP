"""Clasificación automática de archivos. Origen: legacy, sección CLASIFICACIÓN AUTOMÁTICA."""

import pandas as pd

from core.constantes import CUENTA_IT, CUENTA_IVA
from core.texto import buscar_columna, normalizar_texto, texto_limpio


def hojas_archivo(ruta):

    try:

        return pd.ExcelFile(ruta, engine="openpyxl").sheet_names

    except Exception as exc:

        raise Exception(f"No se pudo abrir {ruta}: {exc}")


def contiene_base_netvalle(ruta):

    normalizadas = {normalizar_texto(x) for x in hojas_archivo(ruta)}

    return "NETVALLE" in normalizadas or "CONSOLIDADO" in normalizadas


def cuentas_en_archivo(ruta):

    hojas = hojas_archivo(ruta)

    if not hojas:

        return set()

    try:

        encabezado = pd.read_excel(

            ruta, sheet_name=hojas[0], nrows=0, dtype=object, engine="openpyxl"

        )

        columna = buscar_columna(encabezado.columns, "Cuenta de mayor")

        if columna is None:

            return set()

        muestra = pd.read_excel(

            ruta, sheet_name=hojas[0], usecols=[columna], dtype=object, engine="openpyxl"

        )

    except Exception:

        return set()

    return {texto_limpio(x).split(".")[0] for x in muestra[columna] if texto_limpio(x)}


def clasificar_archivos(nombres):

    encontrados = {"NETVALLE": [], "SAP": [], "OTROS": []}

    cuentas_sap = set()

    for nombre in nombres:

        if contiene_base_netvalle(nombre):

            encontrados["NETVALLE"].append(nombre)

            continue

        cuentas = cuentas_en_archivo(nombre)

        if cuentas & {CUENTA_IVA, CUENTA_IT}:

            encontrados["SAP"].append(nombre)

            cuentas_sap.update(cuentas)

        else:

            encontrados["OTROS"].append(nombre)

    problemas = []

    if len(encontrados["NETVALLE"]) != 1:

        problemas.append(

            "Se esperaba exactamente 1 archivo NETVALLE; "

            f"se identificaron {len(encontrados['NETVALLE'])}."

        )

    if not encontrados["SAP"]:

        problemas.append("No se identificó el archivo SAP con las cuentas de IVA e IT.")

    if CUENTA_IVA not in cuentas_sap:

        problemas.append(f"El SAP no contiene la cuenta de IVA {CUENTA_IVA}.")

    if CUENTA_IT not in cuentas_sap:

        problemas.append(f"El SAP no contiene la cuenta de IT {CUENTA_IT}.")

    if encontrados["OTROS"]:

        problemas.append("No se pudieron clasificar: " + ", ".join(encontrados["OTROS"]))

    if problemas:

        raise Exception("\n".join(problemas))

    return encontrados
