"""Llave de cruce punto|factura|AAAAMMDD y extracción de factura desde texto SAP. Origen: legacy.construir_llaves / extraer_factura_sap."""

import re

import pandas as pd

from core.texto import texto_limpio


def construir_llaves(puntos, facturas, fechas):

    """Construye llaves en bloque, conservando vacío cuando falta un componente."""

    puntos_txt = puntos.fillna("").astype("string")

    facturas_txt = facturas.astype("Int64").astype("string")

    fechas_txt = pd.to_datetime(fechas, errors="coerce").dt.strftime("%Y%m%d").astype("string")

    completas = puntos_txt.ne("") & facturas_txt.notna() & fechas_txt.notna()

    llaves = pd.Series("", index=puntos.index, dtype="string")

    llaves.loc[completas] = (

        puntos_txt.loc[completas]

        + "|" + facturas_txt.loc[completas]

        + "|" + fechas_txt.loc[completas]

    )

    return llaves


def extraer_factura_sap(texto):

    coincidencia = re.search(r"(?i)\bF\s*[\\\\.:#-]?\s*(\d+)", texto_limpio(texto))

    return int(coincidencia.group(1)) if coincidencia else pd.NA
