#@title 🚀 CONTROL TRIBUTARIO INTEGRAL V3.1 — Panel ejecutivo (código plegado)







!pip install -q pandas openpyxl xlsxwriter ipywidgets







import os



import re



import unicodedata



import warnings



from decimal import Decimal, ROUND_HALF_UP



from time import perf_counter







import numpy as np



import pandas as pd



import ipywidgets as widgets







from google.colab import files



from IPython.display import clear_output, display







warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")











# ============================================================



# CONFIGURACIÓN Y REGLAS CONFIRMADAS



# ============================================================







ARCHIVO_FINAL = "CONTROL_TRIBUTARIO_INTEGRAL_V3.xlsx"



CUENTA_IVA = "210106001"



CUENTA_IT = "610501001"



TOLERANCIA = 0.01







# Cajas detectadas en los archivos de Souvenirs del primer control.



PUNTOS_SOUVENIRS = {"SFC103", "SFC204", "SFC503", "SFC303", "SFC403"}







AZUL = "1F4E78"



ROJO = "C00000"



VERDE = "548235"



NARANJA = "ED7D31"



CELESTE = "5B9BD5"



GRIS = "7F7F7F"



MORADO = "7030A0"



BLANCO = "FFFFFF"











# ============================================================



# LIMPIEZA Y NORMALIZACIÓN



# ============================================================







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











def redondear_impuesto(valor, tasa):



    if pd.isna(valor):



        return np.nan



    try:



        resultado = (Decimal(str(valor)) * Decimal(str(tasa))).quantize(



            Decimal("0.01"), rounding=ROUND_HALF_UP



        )



        return float(resultado)



    except Exception:



        return np.nan











def buscar_columna(columnas, nombre):



    objetivo = normalizar_texto(nombre)



    for columna in columnas:



        if normalizar_texto(columna) == objetivo:



            return columna



    return None











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











def unir_unicos(valores):



    salida = []



    vistos = set()



    for valor in valores:



        texto = texto_limpio(valor)



        if texto and texto not in vistos:



            vistos.add(texto)



            salida.append(texto)



    return " / ".join(salida)











# ============================================================



# CLASIFICACIÓN AUTOMÁTICA DE NETVALLE + SAP COMBINADO



# ============================================================







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











# ============================================================



# LECTURA Y PREPARACIÓN DE NETVALLE



# ============================================================







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











# ============================================================



# LECTURA Y PREPARACIÓN DE LOS MAYORES SAP



# ============================================================







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



        print(f"⚠ Se ignoraron {otras:,} partidas de otras cuentas SAP.")



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











# ============================================================



# EVALUACIÓN DEL CONTROL



# ============================================================







def evaluar_fila(fila):



    estado = fila["_ESTADO"]



    iva_o = fila["_IVA_CANT_ORIGINAL"]



    iva_r = fila["_IVA_CANT_REVERSO"]



    it_o = fila["_IT_CANT_ORIGINAL"]



    it_r = fila["_IT_CANT_REVERSO"]







    if not fila["_LLAVE"]:



        return "NETVALLE SIN LLAVE COMPLETA - REVISAR"







    if estado == "A":



        if fila["_SOUVENIR"]:



            iva_ok = iva_o >= 1 and iva_r >= 1 and abs(fila["_IVA_SALDO"]) <= TOLERANCIA



            it_ok = it_o >= 1 and it_r >= 1 and abs(fila["_IT_SALDO"]) <= TOLERANCIA



            return (



                "ANULADA Y REVERTIDA CORRECTAMENTE"



                if iva_ok and it_ok



                else "ANULADA SOUVENIR - REVISAR IVA/IT"



            )







        if iva_o == iva_r == it_o == it_r == 0:



            return "ANULADA SIN MOVIMIENTO TRIBUTARIO"



        if iva_o > 0 and (iva_r == 0 or abs(fila["_IVA_SALDO"]) > TOLERANCIA):



            return "ANULADA SIN REVERSO IVA - REVISAR"



        if it_o > 0 and (it_r == 0 or abs(fila["_IT_SALDO"]) > TOLERANCIA):



            return "ANULADA SIN REVERSO IT - REVISAR"



        if iva_r > 0 and iva_o == 0:



            return "REVERSO IVA SIN ORIGINAL - REVISAR"



        if it_r > 0 and it_o == 0:



            return "REVERSO IT SIN ORIGINAL - REVISAR"



        return "ANULADA Y REVERTIDA CORRECTAMENTE"







    if estado != "V":



        return "INCOMPLETA O ESTADO NO RECONOCIDO - REVISAR"







    if fila["_EXENTO"]:



        if iva_o > 0 or it_o > 0:



            return "LIBRO EXENTO CON PARTIDA TRIBUTARIA - REVISAR"



        return "LIBRO EXENTO - SIN IMPUESTOS"







    if iva_o == 0:



        return "FALTA EN SAP IVA"



    if iva_o > 1:



        return "DUPLICADA EN SAP IVA - REVISAR"



    if iva_r > 0:



        return "FACTURA VÁLIDA CON REVERSO IVA - REVISAR"



    if abs(fila["_DIF_IVA"]) > TOLERANCIA:



        return "DIFERENCIA IMPORTE IVA"







    if fila["_SOUVENIR"]:



        if it_o == 0:



            return "FALTA EN SAP IT"



        if it_o > 1:



            return "DUPLICADA EN SAP IT - REVISAR"



        if it_r > 0:



            return "SOUVENIR VÁLIDO CON REVERSO IT - REVISAR"



        if abs(fila["_DIF_IT"]) > TOLERANCIA:



            return "DIFERENCIA IMPORTE IT"



        return "SOUVENIR - IVA E IT CORRECTOS"







    return "CARGADA CORRECTAMENTE"











def construir_exportacion_netvalle(netvalle):



    control = pd.DataFrame({



        "RESULTADO CONTROL": netvalle["_RESULTADO"],



        "TRATAMIENTO TRIBUTARIO": netvalle["_TRATAMIENTO"],



        "LLAVE CONTROL": netvalle["_LLAVE"],



        "IVA ESPERADO": netvalle["_IVA_ESPERADO"],



        "IVA SAP ORIGINAL": netvalle["_IVA_MONTO"],



        "DIFERENCIA IVA": netvalle["_DIF_IVA"],



        "CANT. ORIGINAL IVA": netvalle["_IVA_CANT_ORIGINAL"],



        "CANT. REVERSO IVA": netvalle["_IVA_CANT_REVERSO"],



        "ASIENTO IVA ORIGINAL": netvalle["_IVA_ASIENTOS"],



        "ASIENTO IVA REVERSO": netvalle["_IVA_ASIENTOS_REVERSO"],



        "SALDO IVA SAP": netvalle["_IVA_SALDO"],



        "IT ESPERADO": netvalle["_IT_ESPERADO"],



        "IT SAP ORIGINAL": netvalle["_IT_MONTO"],



        "DIFERENCIA IT": netvalle["_DIF_IT"],



        "CANT. ORIGINAL IT": netvalle["_IT_CANT_ORIGINAL"],



        "CANT. REVERSO IT": netvalle["_IT_CANT_REVERSO"],



        "ASIENTO IT ORIGINAL": netvalle["_IT_ASIENTOS"],



        "ASIENTO IT REVERSO": netvalle["_IT_ASIENTOS_REVERSO"],



        "SALDO IT SAP": netvalle["_IT_SALDO"],



    })



    originales = netvalle[[c for c in netvalle.columns if not str(c).startswith("_")]].reset_index(drop=True)



    return pd.concat([control.reset_index(drop=True), originales], axis=1)











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


def construir_sap_sin_netvalle(iva, it, llaves_net):
    columnas = [
        "RESULTADO", "LLAVE CONTROL", "PUNTO DE EMISIÓN", "NÚMERO DE FACTURA",
        "FECHA", "PARTIDAS IVA", "CLAVES IVA", "IMPORTE IVA Bs", "ASIENTOS IVA",
        "PARTIDAS IT", "CLAVES IT", "IMPORTE IT Bs", "ASIENTOS IT",
        "TOTAL PARTIDAS SAP",
    ]

    bloques = []

    for df, tipo in ((iva, "IVA"), (it, "IT")):
        parte = df[
            (df["_ERROR"] == "") & (df["_LLAVE"] != "")
            & ~df["_LLAVE"].isin(llaves_net)
        ].copy()

        if parte.empty:
            continue

        parte["_TIPO_AGRUPADO"] = tipo
        bloques.append(parte)

    if not bloques:
        return pd.DataFrame(columns=columnas)

    movimientos = pd.concat(bloques, ignore_index=True)
    filas = []

    for llave, grupo in movimientos.groupby("_LLAVE", sort=False):

        # NUEVO: si el asiento original y su reverso se anulan exactamente,
        # no es una venta adicional ni una diferencia pendiente.
        if grupo_sap_neutralizado(grupo):
            continue

        por_tipo = {
            tipo: grupo[grupo["_TIPO_AGRUPADO"] == tipo]
            for tipo in ("IVA", "IT")
        }

        def dato(tipo, campo, defecto=""):
            parte = por_tipo[tipo]

            if parte.empty:
                return defecto

            if campo == "cantidad":
                return len(parte)

            if campo == "claves":
                return unir_unicos(parte["_CLAVE"])

            if campo == "importe":
                return round(float(parte["_IMPORTE"].sum()), 2)

            if campo == "asientos":
                return unir_unicos(parte["_ASIENTO"])

            return defecto

        primera = grupo.iloc[0]

        filas.append({
            "RESULTADO": "FACTURA REGISTRADA EN SAP SIN RESPALDO NETVALLE",
            "LLAVE CONTROL": llave,
            "PUNTO DE EMISIÓN": primera["_PUNTO"],
            "NÚMERO DE FACTURA": primera["_FACTURA"],
            "FECHA": primera["_FECHA"],
            "PARTIDAS IVA": dato("IVA", "cantidad", 0),
            "CLAVES IVA": dato("IVA", "claves"),
            "IMPORTE IVA Bs": dato("IVA", "importe", 0.0),
            "ASIENTOS IVA": dato("IVA", "asientos"),
            "PARTIDAS IT": dato("IT", "cantidad", 0),
            "CLAVES IT": dato("IT", "claves"),
            "IMPORTE IT Bs": dato("IT", "importe", 0.0),
            "ASIENTOS IT": dato("IT", "asientos"),
            "TOTAL PARTIDAS SAP": len(grupo),
        })

    return pd.DataFrame(filas, columns=columnas)


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











def determinar_dictamen(pendientes_netvalle, sap_sin_netvalle, errores_sap,



                        reversos_manuales, libros_exentos):



    """Emite una conclusión conservadora sin reutilizar importes del SIAT."""



    pendientes = int(pendientes_netvalle) + int(sap_sin_netvalle) + int(errores_sap)



    if pendientes:



        return {



            "nivel": "REVISAR",



            "texto": "🔴 REVISAR ANTES DE DECLARAR",



            "pendientes": pendientes,



            "explicacion": (



                "Existen diferencias no justificadas entre NETVALLE y las partidas "



                "tributarias de SAP."



            ),



            "accion": "Revisar SAP_SIN_NETVALLE y OBSERVACIONES antes de confirmar la declaración.",



        }



    if reversos_manuales:



        return {



            "nivel": "AJUSTES",



            "texto": "🟡 APTO CON AJUSTES IDENTIFICADOS",



            "pendientes": 0,



            "explicacion": (



                "No quedan diferencias pendientes; existen reversiones manuales "



                "vinculadas de manera única y verificable."



            ),



            "accion": "Conservar el respaldo de las reversiones manuales junto con el control.",



        }



    if libros_exentos:



        return {



            "nivel": "APTO",



            "texto": "🟢 APTO PARA DECLARAR",



            "pendientes": 0,



            "explicacion": (



                "La carga tributaria coincide. Las únicas exclusiones corresponden "



                "a libros válidos exentos de IVA e IT."



            ),



            "accion": "Sin diferencias tributarias pendientes; conservar el archivo como respaldo.",



        }



    return {



        "nivel": "APTO",



        "texto": "🟢 APTO PARA DECLARAR",



        "pendientes": 0,



        "explicacion": "NETVALLE y las partidas tributarias de SAP coinciden sin diferencias pendientes.",



        "accion": "Conservar el archivo como respaldo del control.",



    }











# ============================================================



# FORMATO DEL ARCHIVO FINAL



# ============================================================







def formatear_hoja(ws, wb, dataframe, color):



    """Aplica formatos por columnas; evita recorrer decenas de miles de celdas."""



    encabezado = wb.add_format({



        "bold": True, "font_color": BLANCO, "bg_color": f"#{color}",



        "align": "center", "valign": "vcenter", "text_wrap": True,



    })



    moneda = wb.add_format({"num_format": "#,##0.00", "align": "right"})



    fecha = wb.add_format({"num_format": "dd/mm/yyyy", "align": "center"})



    texto = wb.add_format({"num_format": "@"})



    explicacion = wb.add_format({"text_wrap": True, "valign": "vcenter"})







    ws.hide_gridlines(2)



    ws.freeze_panes(1, 0)



    ws.set_row(0, 42, encabezado)



    if len(dataframe.columns):



        ws.autofilter(0, 0, len(dataframe), len(dataframe.columns) - 1)







    monetarios = (



        "IVA ESPERADO", "IVA SAP", "DIFERENCIA IVA", "SALDO IVA",



        "IT ESPERADO", "IT SAP", "DIFERENCIA IT", "SALDO IT",



        "TOTAL FACTURA", "TOTAL VENTA", "TOTAL DECLARABLE", "DESCUENTO",



        "AJUSTE POSTERIOR", "IMPORTE NETO", "BASE CREDITO", "BASE PARA DEBITO",



        "DEBITO FISCAL", "IMPTE.MONEDA", "IMPORTE NORMALIZADO", "IMPORTE BS",



    )



    muestra = dataframe.head(250)



    for indice, columna in enumerate(dataframe.columns):



        nombre = normalizar_texto(columna)



        largos = muestra[columna].dropna().astype(str).map(len)



        maximo = int(largos.max()) if not largos.empty else 0



        ancho = min(max(maximo + 2, len(str(columna)) + 2, 12), 45)



        formato = None



        if any(p in nombre for p in monetarios):



            formato = moneda



        elif "FECHA" in nombre:



            formato = fecha



        elif nombre in {"CODIGO AUXILIAR", "LLAVE CONTROL", "LLAVE REPORTADA SAP", "CUENTA DE MAYOR"} or "ASIENTO" in nombre:



            formato = texto



        ws.set_column(indice, indice, ancho, formato)







    if ws.get_name() == "RESUMEN_EJECUTIVO":
        # Hoja pensada para lectura gerencial/no técnica.
        ws.set_column("A:A", 27)
        ws.set_column("B:B", 24)
        ws.set_column("C:C", 12)
        ws.set_column("D:D", 21)
        ws.set_column("E:E", 38)
        ws.set_column("F:F", 62)
        ws.set_column("G:G", 38)

        ws.set_row(0, 42)
        ws.freeze_panes(1, 0)
        ws.hide_gridlines(2)
        ws.set_landscape()
        ws.fit_to_pages(1, 1)

        texto_fmt = wb.add_format({
            "text_wrap": True,
            "valign": "vcenter",
        })
        moneda_resumen = wb.add_format({
            "num_format": '#,##0.00',
            "align": "right",
            "valign": "vcenter",
        })

        ws.set_column("D:D", 21, moneda_resumen)
        ws.set_column("E:G", 45, texto_fmt)

        formato_estado_bien = wb.add_format({
            "bold": True,
            "bg_color": "#E2F0D9",
            "font_color": "#20613C",
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        })
        formato_estado_alerta = wb.add_format({
            "bold": True,
            "bg_color": "#FCE4D6",
            "font_color": "#9C0006",
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        })
        formato_estado_info = wb.add_format({
            "bold": True,
            "bg_color": "#DDEBF7",
            "font_color": "#1F4E78",
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        })
        formato_estado_ajuste = wb.add_format({
            "bold": True,
            "bg_color": "#FFF2CC",
            "font_color": "#7F6000",
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        })

        if "RESULTADO" in dataframe.columns:
            for i, valor in enumerate(dataframe["RESULTADO"], start=1):
                estado = str(valor).upper()

                if "REVISAR" in estado or "OBSERV" in estado:
                    formato = formato_estado_alerta
                elif (
                    "TODO CUADRA" in estado
                    or estado == "OK"
                    or "SIN PENDIENTES" in estado
                ):
                    formato = formato_estado_bien
                elif "SIN EFECTO NETO" in estado:
                    formato = formato_estado_ajuste
                else:
                    formato = formato_estado_info

                ws.write(i, 1, str(valor), formato)
                ws.set_row(i, 58)

    if ws.get_name() == "OBSERVACIONES":
        # Primero lo que entiende cualquier persona: factura, fecha y total.
        ws.set_column("A:A", 20)
        ws.set_column("B:B", 13)
        ws.set_column("C:C", 14)
        ws.set_column("D:D", 16)
        ws.set_column("E:E", 22)
        ws.set_column("F:F", 48)
        ws.set_column("G:G", 24)
        ws.set_column("H:H", 18)
        ws.set_column("I:L", 17)
        ws.set_column("M:M", 58)
        ws.freeze_panes(1, 0)

        texto_obs = wb.add_format({
            "text_wrap": True,
            "valign": "vcenter",
        })
        moneda_obs = wb.add_format({
            "num_format": '#,##0.00',
            "align": "right",
        })

        ws.set_column("E:E", 22, moneda_obs)
        ws.set_column("I:L", 17, moneda_obs)
        ws.set_column("F:F", 48, texto_obs)
        ws.set_column("M:M", 58, texto_obs)

        for fila in range(1, len(dataframe) + 1):
            ws.set_row(fila, 48)


    if ws.get_name() == "RESUMEN":



        for indice, ancho in enumerate([39, 13, 16, 72, 52]):



            ws.set_column(indice, indice, ancho, explicacion if indice >= 3 else None)



        for fila in range(1, len(dataframe) + 1):



            ws.set_row(fila, 34)



        if not dataframe.empty:



            texto_dictamen = texto_limpio(dataframe.iloc[0]["CONTROL"])



            if "REVISAR" in texto_dictamen:



                fondo = "#F4CCCC"



                fuente = "#9C0006"



            elif "AJUSTES" in texto_dictamen:



                fondo = "#FFF2CC"



                fuente = "#7F6000"



            else:



                fondo = "#D9EAD3"



                fuente = "#274E13"



            formato_dictamen = wb.add_format({



                "bold": True, "bg_color": fondo, "font_color": fuente,



                "valign": "vcenter", "text_wrap": True,



            })



            ws.set_row(1, 48)



            for columna, valor in enumerate(dataframe.iloc[0].tolist()):



                ws.write(1, columna, "" if pd.isna(valor) else valor, formato_dictamen)







    if ws.get_name() == "SAP_SIN_NETVALLE":



        for indice, ancho in {0: 48, 1: 32, 2: 20, 3: 20, 8: 20, 12: 20, 13: 20}.items():



            ws.set_column(indice, indice, ancho)







# ============================================================



# MOTOR PRINCIPAL



# ============================================================







def generar_control(netvalle_archivo, sap_archivos):



    inicio = perf_counter()







    print("\n============================================")



    print("   CONTROL TRIBUTARIO INTEGRAL V3 — NETVALLE/SIAT + SAP")



    print("============================================\n")







    # CRUCE es la fuente de verdad depurada por el usuario. No recalcular motor 1.

    hojas_cruce = hojas_archivo(netvalle_archivo)

    requeridas_cruce = {"RESUMEN_CRUCE", "NETVALLE", "SIAT"}

    faltan = requeridas_cruce - set(hojas_cruce)

    if faltan:

        raise ValueError("El archivo del motor 1 debe incluir: " + ", ".join(sorted(faltan)))

    resumen_cruce_oficial = pd.read_excel(netvalle_archivo, sheet_name="RESUMEN_CRUCE", engine="openpyxl")

    siat_oficial = pd.read_excel(netvalle_archivo, sheet_name="SIAT", engine="openpyxl")

    # Extraer los controles existentes sin reinterpretar ni sobrescribir su resultado

    resumen_cruce_oficial = resumen_cruce_oficial.dropna(how="all")

    net_raw, hoja_net = leer_netvalle(netvalle_archivo)



    sap_raw, origen_sap = leer_sap(sap_archivos)



    iva_raw, it_raw = separar_cuentas_sap(sap_raw)



    print(f"✓ NETVALLE: {len(net_raw):,} registros (hoja {hoja_net})")



    print(f"✓ SAP combinado: {len(sap_raw):,} partidas ({origen_sap})")



    print(f"  · IVA: {len(iva_raw):,} partidas")



    print(f"  · IT:  {len(it_raw):,} partidas")







    net = preparar_netvalle(net_raw)



    iva = preparar_sap(iva_raw, "IVA")



    it = preparar_sap(it_raw, "IT")



    iva = vincular_reversos_manuales(iva, "IVA")



    it = vincular_reversos_manuales(it, "IT")



    resumen_iva = resumir_sap(iva, "IVA")



    resumen_it = resumir_sap(it, "IT")



    agregar_datos_sap(net, resumen_iva, "IVA")



    agregar_datos_sap(net, resumen_it, "IT")







    net["_DIF_IVA"] = (net["_IVA_MONTO"] - net["_IVA_ESPERADO"]).round(2)



    net["_DIF_IT"] = (net["_IT_MONTO"] - net["_IT_ESPERADO"]).round(2)



    net["_RESULTADO"] = net.apply(evaluar_fila, axis=1)







    exportar = construir_exportacion_netvalle(net)



    validas = net["_ESTADO"].eq("V")



    exentas = validas & net["_EXENTO"]



    gravadas = validas & ~net["_EXENTO"]



    souvenirs = validas & net["_SOUVENIR"]



    falta_iva_mask = gravadas & net["_IVA_CANT_ORIGINAL"].eq(0)



    falta_it_mask = souvenirs & net["_IT_CANT_ORIGINAL"].eq(0)



    dif_iva_mask = (



        gravadas & net["_IVA_CANT_ORIGINAL"].gt(0)



        & net["_DIF_IVA"].abs().gt(TOLERANCIA)



    )



    dif_it_mask = (



        souvenirs & net["_IT_CANT_ORIGINAL"].gt(0)



        & net["_DIF_IT"].abs().gt(TOLERANCIA)



    )



    diferencia_mask = dif_iva_mask | dif_it_mask



    anuladas_mask = net["_ESTADO"].eq("A")



    incompletas_mask = ~net["_ESTADO"].isin(["V", "A"])



    resultados_sin_observacion = {



        "CARGADA CORRECTAMENTE", "SOUVENIR - IVA E IT CORRECTOS",



        "LIBRO EXENTO - SIN IMPUESTOS", "ANULADA Y REVERTIDA CORRECTAMENTE",



        "ANULADA SIN MOVIMIENTO TRIBUTARIO",



    }



    observaciones_mask = ~net["_RESULTADO"].isin(resultados_sin_observacion)







    llaves_net = set(net.loc[net["_LLAVE"] != "", "_LLAVE"])



    sap_sin_net = construir_sap_sin_netvalle(iva, it, llaves_net)



    errores_sap = construir_errores_sap(iva, it, resumen_iva, resumen_it)







    def corte(mascara):



        return exportar.loc[mascara.to_numpy()].reset_index(drop=True)







    observaciones_net = corte(observaciones_mask)



    observaciones_net.insert(0, "ORIGEN OBSERVACIÓN", "NETVALLE")



    observaciones_sap = errores_sap.copy()



    if not observaciones_sap.empty:



        observaciones_sap.insert(0, "ORIGEN OBSERVACIÓN", "SAP")



        observaciones_sap["RESULTADO CONTROL"] = observaciones_sap["TIPO ERROR"]



        observaciones = pd.concat(



            [observaciones_net, observaciones_sap], ignore_index=True, sort=False



        )



    else:



        observaciones = observaciones_net







    anuladas_ok = int(net.loc[anuladas_mask, "_RESULTADO"].eq("ANULADA Y REVERTIDA CORRECTAMENTE").sum())



    iva_correcto_mask = (



        gravadas & net["_IVA_CANT_ORIGINAL"].eq(1)



        & net["_IVA_CANT_REVERSO"].eq(0)



        & net["_DIF_IVA"].abs().le(TOLERANCIA)



    )



    iva_correcto = int(iva_correcto_mask.sum())



    it_souvenir_correcto = int((souvenirs & net["_IT_CANT_ORIGINAL"].eq(1) & net["_IT_CANT_REVERSO"].eq(0) & net["_DIF_IT"].abs().le(TOLERANCIA)).sum())



    llaves_reversos_manuales = set()



    for movimientos in (iva, it):



        manuales = movimientos[



            movimientos["_METODO_VINCULO"].eq(



                "REVERSO MANUAL VINCULADO POR FACTURA + FECHA + IMPORTE"



            )



        ]



        llaves_reversos_manuales.update(manuales["_LLAVE"].dropna())







    dictamen = determinar_dictamen(



        pendientes_netvalle=int(observaciones_mask.sum()),



        sap_sin_netvalle=len(sap_sin_net),



        errores_sap=len(errores_sap),



        reversos_manuales=len(llaves_reversos_manuales),



        libros_exentos=int(exentas.sum()),



    )







    resumen = pd.DataFrame([



        (dictamen["texto"], dictamen["pendientes"], np.nan,



         dictamen["explicacion"], dictamen["accion"]),



        ("REGISTROS NETVALLE", len(net), np.nan,



         "Universo total recibido desde el primer cruce.", "Dato informativo."),



        ("CARGADAS CORRECTAMENTE EN SAP", iva_correcto, float(net.loc[iva_correcto_mask, "_IVA_MONTO"].sum()),



         "Ventas gravadas con una partida IVA y sin diferencia de importe.", "No requieren revisión."),



        ("LIBROS EXENTOS IVA E IT", int(exentas.sum()), float(net.loc[exentas, "_TOTAL"].sum()),



         "Ventas sin débito fiscal, excluidas del control tributario SAP.", "No requieren IVA ni IT."),



        ("SOUVENIRS IVA E IT CORRECTOS", it_souvenir_correcto, float(net.loc[souvenirs, "_TOTAL"].sum()),



         "Souvenirs encontrados correctamente en ambas cuentas SAP.", "No requieren revisión."),



        ("FALTAN EN SAP IVA", int(falta_iva_mask.sum()), float(net.loc[falta_iva_mask, "_IVA_ESPERADO"].sum()),



         "Ventas gravadas que no tienen partida original de IVA.", "Revisar la pestaña OBSERVACIONES."),



        ("FALTAN EN SAP IT - SOUVENIRS", int(falta_it_mask.sum()), float(net.loc[falta_it_mask, "_IT_ESPERADO"].sum()),



         "Souvenirs que no tienen partida original de IT.", "Revisar la pestaña OBSERVACIONES."),



        ("FACTURAS CON DIFERENCIA DE IMPORTE", int(diferencia_mask.sum()),



         float(net.loc[diferencia_mask, ["_DIF_IVA", "_DIF_IT"]].fillna(0).abs().sum().sum()),



         "El impuesto SAP difiere del porcentaje esperado por más de Bs 0,01.",



         "Revisar importes en OBSERVACIONES."),



        ("ANULADAS", int(anuladas_mask.sum()), np.nan,



         "Facturas anuladas informadas por NETVALLE.",



         f"{anuladas_ok} tienen reversión tributaria correcta."),



        ("INCOMPLETAS / ESTADO A REVISAR", int(incompletas_mask.sum()), np.nan,



         "Registros cuyo estado no es válido ni anulado.", "Revisar en OBSERVACIONES."),



        ("REVERSOS MANUALES VINCULADOS", len(llaves_reversos_manuales), np.nan,



         "Reversiones cuyo usuario SAP era distinto al punto de emisión, vinculadas de forma única.",



         "Ya están incorporadas al resultado de cada factura."),



        ("FACTURAS SAP SIN NETVALLE", len(sap_sin_net), np.nan,



         "Facturas presentes en SAP que no tienen una llave equivalente en NETVALLE.",



         "Revisar primero la pestaña SAP_SIN_NETVALLE."),



        ("ERRORES O DUPLICADOS SAP", len(errores_sap), np.nan,



         "Filas no interpretables o más de una partida original/reversa por llave.",



         "Revisar en OBSERVACIONES."),



    ], columns=["CONTROL", "CANTIDAD", "IMPORTE Bs", "QUÉ SIGNIFICA", "QUÉ HACER"])







    sap_exportado = pd.concat(



        [exportar_sap_legible(iva), exportar_sap_legible(it)],



        ignore_index=True,



    )







    # ============================================================
    # RESUMEN EJECUTIVO PARA PERSONAS NO TÉCNICAS
    # ============================================================
    # La prioridad aquí es que cualquier persona entienda:
    #   1) cuánto se facturó,
    #   2) cuántas facturas están bien,
    #   3) cuántas requieren revisión,
    #   4) si un asiento SAP antiguo fue neutralizado por su reverso.
    # No se modifican las reglas del motor NETVALLE/SIAT ni las tasas tributarias.

    def valor_cruce(nombre, por_defecto=0):
        col_control = buscar_columna(resumen_cruce_oficial.columns, "CONTROL")
        col_cantidad = buscar_columna(resumen_cruce_oficial.columns, "CANTIDAD")

        if col_control is None or col_cantidad is None:
            return por_defecto

        filtro = (
            resumen_cruce_oficial[col_control]
            .map(normalizar_texto)
            .eq(normalizar_texto(nombre))
        )

        return (
            resumen_cruce_oficial.loc[filtro, col_cantidad].iloc[0]
            if filtro.any()
            else por_defecto
        )

    alertas_cruce = 0

    for nombre in [
        "FALTAN EN NETVALLE",
        "FALTAN EN SIAT",
        "DIFERENCIAS DE ESTADO",
        "DUPLICADOS REALES NETVALLE",
        "DUPLICADOS REALES SIAT",
        "SIN CODIGO NETVALLE",
        "SIN CODIGO SIAT",
    ]:
        valor = pd.to_numeric(valor_cruce(nombre), errors="coerce")

        if pd.notna(valor):
            alertas_cruce += int(valor)

    # ------------------------------------------------------------
    # TOTALES DE FACTURA: esto es lo principal para lectura gerencial.
    # ------------------------------------------------------------
    total_net = round(float(net.loc[validas, "_TOTAL"].sum()), 2)
    cantidad_validas = int(validas.sum())

    siat_col_estado = buscar_columna(siat_oficial.columns, "ESTADO")
    siat_col_monto = (
        buscar_columna(siat_oficial.columns, "IMPORTE TOTAL DE LA VENTA")
        or buscar_columna(siat_oficial.columns, "TOTAL FACTURA (A)")
    )

    total_siat = None

    if siat_col_estado and siat_col_monto:
        mask_siat = (
            siat_oficial[siat_col_estado]
            .map(normalizar_estado)
            .eq("V")
        )

        total_siat = round(
            float(
                pd.to_numeric(
                    siat_oficial.loc[mask_siat, siat_col_monto],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            ),
            2,
        )

    diferencia_net_siat = (
        round(total_net - total_siat, 2)
        if total_siat is not None
        else None
    )

    # ------------------------------------------------------------
    # QUÉ FACTURAS ESTÁN CORRECTAS EN SAP
    # ------------------------------------------------------------
    iva_ok = (
        net["_IVA_CANT_ORIGINAL"].eq(1)
        & net["_IVA_CANT_REVERSO"].eq(0)
        & net["_DIF_IVA"].abs().le(TOLERANCIA)
    )

    it_ok = (
        net["_IT_CANT_ORIGINAL"].eq(1)
        & net["_IT_CANT_REVERSO"].eq(0)
        & net["_DIF_IT"].abs().le(TOLERANCIA)
    )

    sap_ok_mask = (
        validas
        & ~exentas
        & iva_ok
        & (~net["_SOUVENIR"] | it_ok)
    )

    cantidad_sap_ok = int(sap_ok_mask.sum())
    total_facturas_sap_ok = round(
        float(net.loc[sap_ok_mask, "_TOTAL"].sum()),
        2,
    )

    total_exentas = round(
        float(net.loc[exentas, "_TOTAL"].sum()),
        2,
    )

    # ------------------------------------------------------------
    # CASOS NETVALLE QUE REQUIEREN INVESTIGACIÓN
    # Se agrupan IVA e IT para no contar la misma factura dos veces.
    # ------------------------------------------------------------
    observables = net.loc[validas & observaciones_mask].copy()

    casos = {}

    for _, n in observables.iterrows():
        key = (
            str(n["_PUNTO"]),
            int(n["_FACTURA"]) if pd.notna(n["_FACTURA"]) else None,
        )

        caso = casos.setdefault(
            key,
            {
                "punto": key[0],
                "factura": key[1],
                "fecha": n["_FECHA"],
                "total": float(n["_TOTAL"]),
                "motivos": set(),
                "sap": [],
                "iva": (
                    float(n["_IVA_ESPERADO"])
                    if pd.notna(n["_IVA_ESPERADO"])
                    else None
                ),
                "it": (
                    float(n["_IT_ESPERADO"])
                    if pd.notna(n["_IT_ESPERADO"])
                    else None
                ),
            },
        )

        caso["motivos"].add(str(n["_RESULTADO"]))

    # ------------------------------------------------------------
    # REFERENCIAS SAP SIN LLAVE EXACTA NETVALLE
    # Antes de convertirlas en alerta, identificar ajustes que se
    # neutralizan exactamente (asiento original + reverso).
    # ------------------------------------------------------------
    sap_referencias = pd.concat([iva, it], ignore_index=True)

    sap_no_vinculado = sap_referencias[
        sap_referencias["_FACTURA"].notna()
        & ~sap_referencias["_LLAVE"].isin(llaves_net)
        & sap_referencias["_ERROR"].eq("")
    ].copy()

    ajustes_neutralizados = []
    indices_neutralizados = set()

    if not sap_no_vinculado.empty:
        agrupadores = ["_PUNTO", "_FACTURA", "_FECHA"]

        for (punto, factura, fecha_ajuste), grupo in sap_no_vinculado.groupby(
            agrupadores,
            sort=False,
            dropna=False,
        ):
            if grupo_sap_neutralizado(grupo):
                indices_neutralizados.update(grupo.index.tolist())

                ajustes_neutralizados.append({
                    "punto": str(punto),
                    "factura": (
                        int(factura)
                        if pd.notna(factura)
                        else None
                    ),
                    "fecha": fecha_ajuste,
                    "asientos": unir_unicos(grupo["_ASIENTO"]),
                    "saldo_iva": round(
                        float(
                            pd.to_numeric(
                                grupo.loc[
                                    grupo["_TIPO"].eq("IVA"),
                                    "_IMPORTE",
                                ],
                                errors="coerce",
                            )
                            .fillna(0)
                            .sum()
                        ),
                        2,
                    ),
                    "saldo_it": round(
                        float(
                            pd.to_numeric(
                                grupo.loc[
                                    grupo["_TIPO"].eq("IT"),
                                    "_IMPORTE",
                                ],
                                errors="coerce",
                            )
                            .fillna(0)
                            .sum()
                        ),
                        2,
                    ),
                })

    if indices_neutralizados:
        sap_no_vinculado = sap_no_vinculado.drop(
            index=list(indices_neutralizados)
        )

    # ------------------------------------------------------------
    # Vincular referencias SAP restantes solo como diagnóstico.
    # No se debilita la llave oficial del control.
    # ------------------------------------------------------------
    sap_sin_justificar = {}

    for _, srow in sap_no_vinculado.iterrows():
        key = (
            str(srow["_PUNTO"]),
            int(srow["_FACTURA"]),
        )

        if key in casos:
            casos[key]["sap"].append(srow)
        else:
            sap_sin_justificar.setdefault(key, []).append(srow)

    # ------------------------------------------------------------
    # OBSERVACIONES AMIGABLES
    # El TOTAL DE LA FACTURA queda visible antes de los impuestos.
    # ------------------------------------------------------------
    obs_amigables = []

    for key, c in sorted(
        casos.items(),
        key=lambda x: (x[0][0], str(x[0][1])),
    ):
        sap_asientos = sorted({
            str(f["_ASIENTO"])
            for f in c["sap"]
            if str(f["_ASIENTO"])
        })

        fecha_sap = sorted({
            pd.to_datetime(f["_FECHA"]).strftime("%d/%m/%Y")
            for f in c["sap"]
            if pd.notna(f["_FECHA"])
        })

        fecha_net = (
            pd.to_datetime(c["fecha"]).strftime("%d/%m/%Y")
            if pd.notna(c["fecha"])
            else ""
        )

        iva_sap = None
        it_sap = None

        if c["sap"]:
            montos_iva = [
                abs(float(f["_IMPORTE"]))
                for f in c["sap"]
                if f["_TIPO"] == "IVA" and f["_CLAVE"] == "50"
            ]

            montos_it = [
                abs(float(f["_IMPORTE"]))
                for f in c["sap"]
                if f["_TIPO"] == "IT" and f["_CLAVE"] == "40"
            ]

            iva_sap = (
                round(sum(montos_iva), 2)
                if montos_iva
                else None
            )

            it_sap = (
                round(sum(montos_it), 2)
                if montos_it
                else None
            )

            motivo = "Misma referencia en SAP, pero los datos no coinciden"

            detalle = (
                f"Factura NETVALLE de Bs {c['total']:,.2f}, "
                f"fecha {fecha_net}. "
                f"SAP tiene referencia en "
                f"{', '.join(fecha_sap) if fecha_sap else 'fecha no identificada'}."
            )

        else:
            motivo = "No se encontró la contabilización esperada en SAP"

            detalle = (
                f"Factura NETVALLE de Bs {c['total']:,.2f}, "
                f"fecha {fecha_net}, sin coincidencia exacta "
                f"en los mayores tributarios SAP revisados."
            )

        obs_amigables.append({
            "CONTROL": "NETVALLE vs SAP",
            "FACTURA": str(c["factura"]),
            "PUNTO": c["punto"],
            "FECHA NETVALLE": fecha_net,
            "TOTAL FACTURA NETVALLE Bs": round(c["total"], 2),
            "QUÉ PASÓ": motivo,
            "ASIENTO SAP": ", ".join(sap_asientos),
            "FECHA SAP": ", ".join(fecha_sap),
            "IVA ESPERADO Bs": c["iva"],
            "IVA SAP Bs": iva_sap,
            "IT ESPERADO Bs": c["it"],
            "IT SAP Bs": it_sap,
            "QUÉ REVISAR": (
                detalle
                + " Verificar el respaldo con Sistemas/Contabilidad."
            ),
        })

    # ------------------------------------------------------------
    # SAP SIN NETVALLE: solo quedan partidas NO neutralizadas.
    # ------------------------------------------------------------
    for key, rows in sorted(sap_sin_justificar.items()):

        en_net = net[
            (net["_PUNTO"] == key[0])
            & (net["_FACTURA"] == key[1])
        ]

        # Una factura anulada en NETVALLE no se lleva como alerta gerencial.
        if not en_net.empty and en_net["_ESTADO"].eq("A").all():
            continue

        asientos = ", ".join(
            sorted({str(x["_ASIENTO"]) for x in rows})
        )

        fechas = sorted({
            pd.to_datetime(x["_FECHA"]).strftime("%d/%m/%Y")
            for x in rows
            if pd.notna(x["_FECHA"])
        })

        iva_sap = round(
            sum(
                abs(float(x["_IMPORTE"]))
                for x in rows
                if x["_TIPO"] == "IVA" and x["_CLAVE"] == "50"
            ),
            2,
        )

        it_sap = round(
            sum(
                abs(float(x["_IMPORTE"]))
                for x in rows
                if x["_TIPO"] == "IT" and x["_CLAVE"] == "40"
            ),
            2,
        )

        obs_amigables.append({
            "CONTROL": "SAP sin coincidencia",
            "FACTURA": str(key[1]),
            "PUNTO": key[0],
            "FECHA NETVALLE": "",
            "TOTAL FACTURA NETVALLE Bs": float("nan"),
            "QUÉ PASÓ": "Partida SAP sin factura equivalente en NETVALLE",
            "ASIENTO SAP": asientos,
            "FECHA SAP": ", ".join(fechas),
            "IVA ESPERADO Bs": float("nan"),
            "IVA SAP Bs": iva_sap if iva_sap else float("nan"),
            "IT ESPERADO Bs": float("nan"),
            "IT SAP Bs": it_sap if it_sap else float("nan"),
            "QUÉ REVISAR": (
                "Revisar referencia y respaldo. "
                "No implica automáticamente una segunda venta."
            ),
        })

    observaciones_amigables = pd.DataFrame(
        obs_amigables,
        columns=[
            "CONTROL",
            "FACTURA",
            "PUNTO",
            "FECHA NETVALLE",
            "TOTAL FACTURA NETVALLE Bs",
            "QUÉ PASÓ",
            "ASIENTO SAP",
            "FECHA SAP",
            "IVA ESPERADO Bs",
            "IVA SAP Bs",
            "IT ESPERADO Bs",
            "IT SAP Bs",
            "QUÉ REVISAR",
        ],
    )

    pendientes_sap = len(observaciones_amigables)

    # Monto de facturas NETVALLE que realmente quedan pendientes.
    total_facturas_pendientes = round(
        sum(
            float(c["total"])
            for c in casos.values()
        ),
        2,
    )

    # ------------------------------------------------------------
    # ESTADOS DE LECTURA SIMPLE
    # ------------------------------------------------------------
    if total_siat is not None and abs(diferencia_net_siat) > TOLERANCIA:
        estado_cruce = "REVISAR IMPORTES"
    elif alertas_cruce:
        estado_cruce = "CON OBSERVACIONES"
    else:
        estado_cruce = "TODO CUADRA"

    estado_sap = (
        "TODO CUADRA"
        if pendientes_sap == 0
        else f"REVISAR {pendientes_sap} CASO(S)"
    )

    estado_general = (
        "TODO CUADRA"
        if estado_cruce == "TODO CUADRA" and pendientes_sap == 0
        else "REVISAR"
    )

    if total_siat is not None:
        dato_siat = (
            f"SIAT Bs {total_siat:,.2f} | "
            f"Diferencia Bs {diferencia_net_siat:,.2f}"
        )
    else:
        dato_siat = "Consultar el cruce NETVALLE vs SIAT"

    if pendientes_sap == 0:
        texto_sap = (
            "No quedan diferencias pendientes en las facturas válidas "
            "revisadas contra las cuentas tributarias de SAP."
        )
    elif pendientes_sap == 1:
        unico = observaciones_amigables.iloc[0]

        texto_sap = (
            f"Queda 1 caso para revisar: factura "
            f"{unico['FACTURA']} ({unico['PUNTO']}). "
            f"El detalle está en OBSERVACIONES."
        )
    else:
        texto_sap = (
            f"Quedan {pendientes_sap} casos para revisar. "
            f"El detalle está en OBSERVACIONES."
        )

    if ajustes_neutralizados:
        texto_ajustes = (
            f"Se identificaron {len(ajustes_neutralizados)} referencia(s) "
            "SAP donde el asiento original y su reverso se cancelan "
            "exactamente. No se consideran venta adicional ni diferencia pendiente."
        )
        resultado_ajustes = "SIN EFECTO NETO"
    else:
        texto_ajustes = (
            "No se identificaron pares de asiento + reverso fuera de la llave "
            "NETVALLE que requieran explicación adicional."
        )
        resultado_ajustes = "INFORMATIVO"

    # ------------------------------------------------------------
    # RESUMEN EJECUTIVO FINAL
    # ------------------------------------------------------------
    ejecutivo = pd.DataFrame([
        (
            "RESULTADO GENERAL",
            estado_general,
            cantidad_validas,
            total_net,
            (
                f"NETVALLE vs SIAT: {estado_cruce} | "
                f"NETVALLE vs SAP: {estado_sap}"
            ),
            (
                f"Se controlaron {cantidad_validas} facturas válidas "
                f"por un total de Bs {total_net:,.2f}."
            ),
            (
                "Revisar únicamente las filas marcadas como REVISAR."
                if estado_general != "TODO CUADRA"
                else "Sin acciones pendientes."
            ),
        ),
        (
            "NETVALLE vs SIAT",
            estado_cruce,
            cantidad_validas,
            total_net,
            dato_siat,
            (
                "Compara el total de las facturas válidas de NETVALLE "
                "contra el total reportado al SIAT."
            ),
            (
                "Revisar el archivo CRUCE original."
                if estado_cruce != "TODO CUADRA"
                else "Sin diferencias pendientes."
            ),
        ),
        (
            "NETVALLE vs SAP",
            estado_sap,
            cantidad_sap_ok,
            total_facturas_sap_ok,
            f"{pendientes_sap} caso(s) pendiente(s)",
            (
                f"{cantidad_sap_ok} factura(s), por Bs "
                f"{total_facturas_sap_ok:,.2f}, tienen la carga tributaria "
                "esperada en SAP."
            ),
            (
                "Revisar la pestaña OBSERVACIONES."
                if pendientes_sap
                else "Sin diferencias pendientes."
            ),
        ),
        (
            "FACTURAS PARA REVISAR",
            (
                f"REVISAR {pendientes_sap} CASO(S)"
                if pendientes_sap
                else "SIN PENDIENTES"
            ),
            pendientes_sap,
            total_facturas_pendientes if pendientes_sap else 0.0,
            (
                f"Bs {total_facturas_pendientes:,.2f} en facturas NETVALLE "
                "con observación."
                if total_facturas_pendientes
                else "No hay facturas NETVALLE pendientes."
            ),
            texto_sap,
            (
                "Ir a OBSERVACIONES."
                if pendientes_sap
                else "Sin acción."
            ),
        ),
        (
            "AJUSTES SAP NEUTRALIZADOS",
            resultado_ajustes,
            len(ajustes_neutralizados),
            float("nan"),
            "Asiento original + reverso = saldo cero",
            texto_ajustes,
            (
                "Conservar como trazabilidad; no requiere corrección."
                if ajustes_neutralizados
                else "Sin acción."
            ),
        ),
        (
            "LIBROS EXENTOS",
            "INFORMATIVO",
            int(exentas.sum()),
            total_exentas,
            "No requieren IVA ni IT",
            (
                f"{int(exentas.sum())} registro(s) válido(s) por "
                f"Bs {total_exentas:,.2f} fueron identificados como libros exentos."
            ),
            "Dato informativo.",
        ),
    ], columns=[
        "CONTROL",
        "RESULTADO",
        "CANTIDAD",
        "TOTAL FACTURAS Bs",
        "DATO CLAVE",
        "QUÉ SIGNIFICA",
        "QUÉ HACER",
    ])

    hojas = [

        ("RESUMEN_EJECUTIVO", ejecutivo, AZUL),

        ("OBSERVACIONES", observaciones_amigables, ROJO),

        ("NETVALLE", exportar, AZUL),

        ("SAP", sap_exportado, CELESTE),

    ]



    with pd.ExcelWriter(



        ARCHIVO_FINAL,



        engine="xlsxwriter",



        engine_kwargs={"options": {"strings_to_urls": False}},



    ) as writer:



        for nombre, dataframe, _color in hojas:



            dataframe.to_excel(writer, sheet_name=nombre, index=False)



        wb = writer.book



        for nombre, dataframe, color in hojas:



            formatear_hoja(writer.sheets[nombre], wb, dataframe, color)







    print("\n============================================")



    print("   CONTROL FINALIZADO")



    print("============================================\n")



    display(ejecutivo)

    print(f"\nCasos para revisar en SAP: {pendientes_sap}")

    print("Revisa la pestaña OBSERVACIONES si necesitas el detalle.")

    print(f"Tiempo: {perf_counter() - inicio:.1f} s")



    return ARCHIVO_FINAL











def ejecutar_control_sap():



    actualizar_progreso(0, "Selecciona los 2 archivos...")



    print("Selecciona juntos:")



    print("  1. Resultado del cruce NETVALLE–SIAT")



    print("  2. Mayor SAP combinado con IVA e IT\n")







    subidos = files.upload()



    if not subidos:



        actualizar_progreso(0, "No se seleccionaron archivos.")



        return None







    actualizar_progreso(10, f"Archivos recibidos: {len(subidos)}")



    clasificados = clasificar_archivos(list(subidos.keys()))



    print("\nClasificación automática:")



    print("  NETVALLE:", clasificados["NETVALLE"][0])



    print("  SAP combinado:", " / ".join(clasificados["SAP"]))







    actualizar_progreso(20, "Procesando NETVALLE y SAP combinado...")



    resultado = generar_control(



        clasificados["NETVALLE"][0],



        clasificados["SAP"],



    )



    actualizar_progreso(95, "Preparando una única descarga...")



    files.download(resultado)



    actualizar_progreso(100, "Descarga completada.")



    return resultado











# ============================================================



# PANEL DE CONTROL



# ============================================================







titulo = widgets.HTML(value="""



<div style="background:#1F4E78;color:white;padding:20px;border-radius:14px;



text-align:center;font-size:24px;font-weight:bold;margin-bottom:16px;



box-shadow:0 3px 8px rgba(0,0,0,0.18);">



    📘 CONTROL TRIBUTARIO INTEGRAL V3.1 — NETVALLE/SIAT + SAP



</div>



""")







instrucciones = widgets.HTML(value="""



<div style="text-align:center;font-size:14px;margin-bottom:18px;color:#555;">



    Carga el CRUCE depurado (motor 1) y el mayor SAP de IVA e IT.



</div>



""")







btn_procesar = widgets.Button(



    description="🚀 GENERAR CONTROL NETVALLE VS SAP",



    tooltip="Cruza NETVALLE contra los mayores SAP de IVA e IT",



    button_style="primary",



    layout=widgets.Layout(width="540px", height="70px", margin="6px 0px"),



)







barra = widgets.IntProgress(



    value=0, min=0, max=100, description="Progreso:",



    bar_style="info", layout=widgets.Layout(width="540px", margin="10px 0px"),



)



estado_panel = widgets.HTML(value="")



salida = widgets.Output(layout=widgets.Layout(width="100%", margin="18px 0px 0px 0px"))











def actualizar_progreso(valor, mensaje=""):



    barra.value = int(valor)



    barra.bar_style = "success" if valor >= 100 else "info"



    estado_panel.value = f"<div style='text-align:center;color:#555;'>{mensaje}</div>"











proceso_en_curso = False











def click_procesar(_boton):



    global proceso_en_curso



    if proceso_en_curso:



        return



    proceso_en_curso = True



    btn_procesar.disabled = True



    barra.bar_style = "info"



    with salida:



        clear_output()



        try:



            resultado = ejecutar_control_sap()



            if resultado:



                print("\n✅ CONTROL TERMINADO CORRECTAMENTE")



        except Exception as exc:



            barra.bar_style = "danger"



            estado_panel.value = "<div style='text-align:center;color:#C00000;'>Proceso detenido.</div>"



            print("\n❌ ERROR AL GENERAR EL CONTROL\n")



            print(str(exc))



        finally:



            proceso_en_curso = False



            btn_procesar.disabled = False











btn_procesar.on_click(click_procesar)







panel = widgets.VBox(



    [titulo, instrucciones, btn_procesar, barra, estado_panel, salida],



    layout=widgets.Layout(width="100%", align_items="center", padding="10px"),



)







display(panel)
