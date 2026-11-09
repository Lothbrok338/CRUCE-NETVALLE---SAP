"""Lectura, preparación, reversos y resúmenes de los mayores SAP. Origen: legacy, secciones SAP."""

import logging
import os

import pandas as pd

from core.clasificacion import hojas_archivo
from core.constantes import CUENTA_IT, CUENTA_IVA, TOLERANCIA
from core.llaves import construir_llaves
from core.texto import buscar_columna, normalizar_texto, texto_limpio, unir_unicos

logger = logging.getLogger(__name__)


def leer_sap(rutas):

    bloques = []

    origenes = []

    for ruta in rutas:

        hoja = hojas_archivo(ruta)[0]

        df = pd.read_excel(ruta, sheet_name=hoja, dtype=object, engine="openpyxl")

        df = df.dropna(axis=1, how="all")

        df["ARCHIVO SAP ORIGEN"] = os.path.basename(ruta)

        bloques.append(df)

        origenes.append(f"{os.path.basename(ruta)} · {hoja}")

    return pd.concat(bloques, ignore_index=True, sort=False), " / ".join(origenes)


def separar_cuentas_sap(df):

    columna = buscar_columna(df.columns, "Cuenta de mayor")

    if columna is None:

        raise Exception("El archivo SAP no contiene la columna Cuenta de mayor.")

    cuentas = df[columna].map(lambda x: texto_limpio(x).split(".")[0])

    iva = df[cuentas.eq(CUENTA_IVA)].copy()

    it = df[cuentas.eq(CUENTA_IT)].copy()

    if iva.empty or it.empty:

        raise Exception(

            "El archivo SAP debe contener movimientos de ambas cuentas: "

            f"IVA {CUENTA_IVA} e IT {CUENTA_IT}."

        )

    otras = int((~cuentas.isin([CUENTA_IVA, CUENTA_IT]) & cuentas.ne("")).sum())

    if otras:

        logger.warning("Se ignoraron %s partidas de otras cuentas SAP.", f"{otras:,}")

    return iva, it


def preparar_sap(df, tipo):

    cuenta_esperada = CUENTA_IVA if tipo == "IVA" else CUENTA_IT

    clave_original = "50" if tipo == "IVA" else "40"

    clave_reverso = "40" if tipo == "IVA" else "50"

    nombres = {

        "cuenta": "Cuenta de mayor",

        "factura_texto": "Txt.pos.reg.diario",

        "punto": "AC creado por",

        "fecha": "Fe.contab.",

        "clave": "Clave contab.",

        "importe": "Impte.moneda socied.",

        "asiento": "Asiento contable",

    }

    columnas = {k: buscar_columna(df.columns, v) for k, v in nombres.items()}

    faltantes = [nombres[k] for k, v in columnas.items() if v is None]

    if faltantes:

        raise Exception(f"El reporte SAP {tipo} no contiene: " + ", ".join(faltantes))

    salida = df.copy()

    salida["_TIPO"] = tipo

    salida["_CUENTA"] = salida[columnas["cuenta"]].map(lambda x: texto_limpio(x).split(".")[0])

    salida["_PUNTO"] = salida[columnas["punto"]].map(normalizar_texto)

    salida["_PUNTO_REPORTADO"] = salida["_PUNTO"]

    facturas = salida[columnas["factura_texto"]].map(texto_limpio).str.extract(

        r"(?i)\bF\s*[\\\\.:#-]?\s*(\d+)", expand=False

    )

    salida["_FACTURA"] = pd.to_numeric(facturas, errors="coerce").astype("Int64")

    salida["_FECHA"] = pd.to_datetime(salida[columnas["fecha"]], errors="coerce").dt.normalize()

    salida["_CLAVE"] = salida[columnas["clave"]].map(lambda x: texto_limpio(x).split(".")[0])

    salida["_IMPORTE"] = pd.to_numeric(salida[columnas["importe"]], errors="coerce")

    salida["_ASIENTO"] = salida[columnas["asiento"]].map(texto_limpio)

    salida["_LLAVE"] = construir_llaves(salida["_PUNTO"], salida["_FACTURA"], salida["_FECHA"])

    salida["_LLAVE_REPORTADA"] = salida["_LLAVE"]

    salida["_PUNTO_VINCULADO"] = ""

    salida["_METODO_VINCULO"] = "LLAVE DIRECTA"

    errores = []

    for cuenta, punto, factura, fecha, clave, importe in salida[

        ["_CUENTA", "_PUNTO", "_FACTURA", "_FECHA", "_CLAVE", "_IMPORTE"]

    ].itertuples(index=False, name=None):

        partes = []

        if cuenta != cuenta_esperada:

            partes.append(f"CUENTA DISTINTA DE {cuenta_esperada}")

        if not punto:

            partes.append("PUNTO VACÍO")

        if pd.isna(factura):

            partes.append("FACTURA NO INTERPRETABLE")

        if pd.isna(fecha):

            partes.append("FECHA VACÍA")

        if clave not in {clave_original, clave_reverso}:

            partes.append(f"CLAVE {clave or 'VACÍA'} NO ESPERADA")

        if pd.isna(importe):

            partes.append("IMPORTE VACÍO")

        errores.append("; ".join(partes))

    salida["_ERROR"] = errores

    return salida


def vincular_reversos_manuales(df, tipo):

    """Vincula reversos cuyo usuario SAP reemplazó al punto de emisión.

    La llave principal nunca se debilita para movimientos normales. Solamente si un

    reverso no tiene original con su llave directa, se busca una partida original de

    la misma cuenta por factura, fecha e importe absoluto. Se vincula únicamente

    cuando la llave candidata es única; los casos ambiguos quedan observados.

    """

    salida = df.copy()

    clave_original = "50" if tipo == "IVA" else "40"

    clave_reverso = "40" if tipo == "IVA" else "50"

    validas = salida["_ERROR"].eq("") & salida["_LLAVE"].ne("")

    originales = salida[validas & salida["_CLAVE"].eq(clave_original)].copy()

    reversos = salida[validas & salida["_CLAVE"].eq(clave_reverso)].index

    for indice in reversos:

        fila = salida.loc[indice]

        directo = originales[originales["_LLAVE"].eq(fila["_LLAVE"])]

        if not directo.empty:

            continue

        candidatos = originales[

            originales["_FACTURA"].eq(fila["_FACTURA"])

            & originales["_FECHA"].eq(fila["_FECHA"])

            & (originales["_IMPORTE"].abs() - abs(float(fila["_IMPORTE"]))).abs().le(TOLERANCIA)

        ]

        llaves = [x for x in candidatos["_LLAVE"].dropna().unique() if x]

        if len(llaves) == 1:

            llave = llaves[0]

            candidato = candidatos[candidatos["_LLAVE"].eq(llave)].iloc[0]

            salida.at[indice, "_LLAVE"] = llave

            salida.at[indice, "_PUNTO_VINCULADO"] = candidato["_PUNTO"]

            salida.at[indice, "_METODO_VINCULO"] = (

                "REVERSO MANUAL VINCULADO POR FACTURA + FECHA + IMPORTE"

            )

        elif len(llaves) > 1:

            salida.at[indice, "_METODO_VINCULO"] = "REVERSO MANUAL AMBIGUO"

            salida.at[indice, "_ERROR"] = (

                "REVERSO MANUAL AMBIGUO: COINCIDE CON MÁS DE UNA LLAVE ORIGINAL"

            )

    return salida


def resumir_sap(df, tipo):

    clave_original = "50" if tipo == "IVA" else "40"

    clave_reverso = "40" if tipo == "IVA" else "50"

    validos = df[(df["_ERROR"] == "") & (df["_LLAVE"] != "")].copy()

    base = validos.groupby("_LLAVE", sort=False).agg(

        FILAS=("_LLAVE", "size"),

        SALDO=("_IMPORTE", "sum"),

    )

    def bloque(clave, prefijo):

        parte = validos[validos["_CLAVE"] == clave].copy()

        if parte.empty:

            return pd.DataFrame(columns=[f"CANT_{prefijo}", f"MONTO_{prefijo}", f"ASIENTOS_{prefijo}"])

        parte["_ABS"] = parte["_IMPORTE"].abs()

        return parte.groupby("_LLAVE", sort=False).agg(

            **{

                f"CANT_{prefijo}": ("_LLAVE", "size"),

                f"MONTO_{prefijo}": ("_ABS", "sum"),

                f"ASIENTOS_{prefijo}": ("_ASIENTO", unir_unicos),

            }

        )

    resumen = base.join(bloque(clave_original, "ORIGINAL"), how="left")

    resumen = resumen.join(bloque(clave_reverso, "REVERSO"), how="left")

    for columna in ["CANT_ORIGINAL", "CANT_REVERSO"]:

        resumen[columna] = resumen[columna].fillna(0).astype(int)

    for columna in ["MONTO_ORIGINAL", "MONTO_REVERSO", "SALDO"]:

        resumen[columna] = pd.to_numeric(resumen[columna], errors="coerce").fillna(0.0).round(2)

    for columna in ["ASIENTOS_ORIGINAL", "ASIENTOS_REVERSO"]:

        resumen[columna] = resumen[columna].fillna("")

    return resumen


def agregar_datos_sap(netvalle, resumen, prefijo):

    mapas = {

        f"_{prefijo}_CANT_ORIGINAL": "CANT_ORIGINAL",

        f"_{prefijo}_CANT_REVERSO": "CANT_REVERSO",

        f"_{prefijo}_MONTO": "MONTO_ORIGINAL",

        f"_{prefijo}_MONTO_REVERSO": "MONTO_REVERSO",

        f"_{prefijo}_SALDO": "SALDO",

        f"_{prefijo}_ASIENTOS": "ASIENTOS_ORIGINAL",

        f"_{prefijo}_ASIENTOS_REVERSO": "ASIENTOS_REVERSO",

    }

    for destino, origen in mapas.items():

        netvalle[destino] = netvalle["_LLAVE"].map(resumen[origen])

    for columna in [

        f"_{prefijo}_CANT_ORIGINAL", f"_{prefijo}_CANT_REVERSO",

    ]:

        netvalle[columna] = netvalle[columna].fillna(0).astype(int)

    for columna in [

        f"_{prefijo}_MONTO", f"_{prefijo}_MONTO_REVERSO", f"_{prefijo}_SALDO",

    ]:

        netvalle[columna] = pd.to_numeric(netvalle[columna], errors="coerce").fillna(0.0).round(2)

    for columna in [f"_{prefijo}_ASIENTOS", f"_{prefijo}_ASIENTOS_REVERSO"]:

        netvalle[columna] = netvalle[columna].fillna("")


def grupo_sap_neutralizado(grupo):
    """
    Devuelve True cuando un grupo SAP se cancela completamente entre sí.

    Regla conservadora:
    - se evalúa por referencia/fecha ya agrupada;
    - para cada impuesto presente debe existir clave 40 y 50;
    - el saldo firmado del impuesto debe ser cero dentro de la tolerancia.

    Esto permite reconocer, por ejemplo, un asiento incorrecto y su reverso
    exacto, sin confundirlos con una venta adicional pendiente.
    """
    if grupo is None or grupo.empty:
        return False

    tipos_presentes = 0

    for tipo in ("IVA", "IT"):
        parte = grupo[grupo["_TIPO"].eq(tipo)].copy()

        if parte.empty:
            continue

        tipos_presentes += 1

        claves = set(parte["_CLAVE"].dropna().astype(str))
        saldo = pd.to_numeric(parte["_IMPORTE"], errors="coerce").fillna(0.0).sum()

        if not {"40", "50"}.issubset(claves):
            return False

        if abs(float(saldo)) > TOLERANCIA:
            return False

    return tipos_presentes > 0


def construir_errores_sap(iva, it, resumen_iva, resumen_it):

    filas = []

    for df, tipo in ((iva, "IVA"), (it, "IT")):

        for _, fila in df[df["_ERROR"] != ""].iterrows():

            filas.append({

                "TIPO REPORTE": tipo,

                "LLAVE CONTROL": fila["_LLAVE"],

                "TIPO ERROR": "FILA NO INTERPRETABLE",

                "DETALLE": fila["_ERROR"],

            })

    for resumen, tipo in ((resumen_iva, "IVA"), (resumen_it, "IT")):

        anomalias = resumen[(resumen["CANT_ORIGINAL"] > 1) | (resumen["CANT_REVERSO"] > 1)]

        for llave, fila in anomalias.iterrows():

            filas.append({

                "TIPO REPORTE": tipo,

                "LLAVE CONTROL": llave,

                "TIPO ERROR": "MÚLTIPLES PARTIDAS DEL MISMO TIPO",

                "DETALLE": (

                    f"Originales={int(fila['CANT_ORIGINAL'])}; "

                    f"Reversos={int(fila['CANT_REVERSO'])}"

                ),

            })

    return pd.DataFrame(filas, columns=["TIPO REPORTE", "LLAVE CONTROL", "TIPO ERROR", "DETALLE"])


def exportar_sap_legible(df):

    tecnicas = pd.DataFrame({

        "TIPO REPORTE": df["_TIPO"],

        "LLAVE CONTROL": df["_LLAVE"],

        "LLAVE REPORTADA SAP": df["_LLAVE_REPORTADA"],

        "FACTURA EXTRAÍDA": df["_FACTURA"],

        "PUNTO NORMALIZADO": df["_PUNTO"],

        "PUNTO VINCULADO": df["_PUNTO_VINCULADO"],

        "MÉTODO DE VINCULACIÓN": df["_METODO_VINCULO"],

        "FECHA NORMALIZADA": df["_FECHA"],

        "CLAVE NORMALIZADA": df["_CLAVE"],

        "IMPORTE NORMALIZADO": df["_IMPORTE"],

        "ERROR DE LECTURA": df["_ERROR"],

    })

    originales = df[[c for c in df.columns if not str(c).startswith("_")]].reset_index(drop=True)

    return pd.concat([tecnicas.reset_index(drop=True), originales], axis=1)
