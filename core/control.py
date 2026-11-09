"""Evaluación del control y motor principal. Origen: legacy, secciones EVALUACIÓN DEL CONTROL y MOTOR PRINCIPAL. generar_control ya no escribe a disco por defecto, no imprime ni usa Colab: devuelve un ResultadoControl y escribe el Excel solo si se pasa archivo_salida."""

import logging
from dataclasses import dataclass, field
from time import perf_counter

import pandas as pd

from core.clasificacion import hojas_archivo
from core.constantes import AZUL, CELESTE, ROJO, TOLERANCIA
from core.excel import escribir_excel
from core.netvalle import leer_netvalle, preparar_netvalle
from core.sap import (
    agregar_datos_sap, construir_errores_sap,
    exportar_sap_legible, grupo_sap_neutralizado, leer_sap, preparar_sap,
    resumir_sap, separar_cuentas_sap, vincular_reversos_manuales,
)
from core.texto import buscar_columna, normalizar_estado, normalizar_texto, unir_unicos

logger = logging.getLogger(__name__)
_log = logger.debug


@dataclass
class ResultadoControl:
    """Salida de generar_control (el original solo devolvía el nombre del archivo)."""

    hojas: list  # [(nombre_hoja, DataFrame, color_hex)] en el orden del Excel original
    ejecutivo: pd.DataFrame
    observaciones: pd.DataFrame
    netvalle: pd.DataFrame
    sap: pd.DataFrame
    pendientes_sap: int
    diagnostico: dict = field(default_factory=dict)


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


def generar_control(netvalle_archivo, sap_archivos, archivo_salida=None):

    inicio = perf_counter()


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

    _log("NETVALLE: %s registros", f"{len(net_raw):,}")

    _log("SAP combinado: %s partidas", f"{len(sap_raw):,}")

    _log("IVA: %s partidas", f"{len(iva_raw):,}")

    _log("IT: %s partidas", f"{len(it_raw):,}")

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

    incompletas_mask = ~net["_ESTADO"].isin(["V", "A"])

    resultados_sin_observacion = {

        "CARGADA CORRECTAMENTE", "SOUVENIR - IVA E IT CORRECTOS",

        "LIBRO EXENTO - SIN IMPUESTOS", "ANULADA Y REVERTIDA CORRECTAMENTE",

        "ANULADA SIN MOVIMIENTO TRIBUTARIO",

    }

    observaciones_mask = ~net["_RESULTADO"].isin(resultados_sin_observacion)

    llaves_net = set(net.loc[net["_LLAVE"] != "", "_LLAVE"])

    errores_sap = construir_errores_sap(iva, it, resumen_iva, resumen_it)

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
    observables = net.loc[(validas | incompletas_mask) & observaciones_mask].copy()

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
                "incompleta": False,
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

        if n["_ESTADO"] != "V":
            caso["incompleta"] = True

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

        if c["incompleta"]:
            motivo = "Factura INCOMPLETA en NETVALLE"

            detalle = (
                f"Factura NETVALLE de Bs {c['total']:,.2f}, "
                f"fecha {fecha_net}, con estado incompleto o no reconocido. "
                f"Completar o regularizar el registro en NETVALLE."
            )

        elif c["sap"]:
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

            motivo = " / ".join(sorted(c["motivos"])) + " (misma referencia en SAP con otros datos)"

            detalle = (
                f"Factura NETVALLE de Bs {c['total']:,.2f}, "
                f"fecha {fecha_net}. "
                f"SAP tiene referencia en "
                f"{', '.join(fecha_sap) if fecha_sap else 'fecha no identificada'}."
            )

        else:
            motivo = " / ".join(sorted(c["motivos"]))

            detalle = (
                f"Factura NETVALLE de Bs {c['total']:,.2f}, "
                f"fecha {fecha_net}. "
                f"Revisar sus partidas en los mayores tributarios SAP."
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

    # ------------------------------------------------------------
    # ERRORES DE LECTURA SAP (decisión del usuario, a prueba): filas del mayor que no se pudieron
    # interpretar. Antes solo se veían en la hoja SAP; ahora también se listan aquí.
    # ------------------------------------------------------------
    for movimientos in (iva, it):
        for _, e in movimientos[movimientos["_ERROR"] != ""].iterrows():
            fecha_e = (
                pd.to_datetime(e["_FECHA"]).strftime("%d/%m/%Y")
                if pd.notna(e["_FECHA"])
                else ""
            )
            importe_e = (
                abs(float(e["_IMPORTE"])) if pd.notna(e["_IMPORTE"]) else float("nan")
            )

            obs_amigables.append({
                "CONTROL": "SAP error de lectura",
                "FACTURA": str(e["_FACTURA"]) if pd.notna(e["_FACTURA"]) else "",
                "PUNTO": e["_PUNTO"],
                "FECHA NETVALLE": "",
                "TOTAL FACTURA NETVALLE Bs": float("nan"),
                "QUÉ PASÓ": "Fila SAP que no se pudo interpretar y quedó fuera del cruce",
                "ASIENTO SAP": e["_ASIENTO"],
                "FECHA SAP": fecha_e,
                "IVA ESPERADO Bs": float("nan"),
                "IVA SAP Bs": importe_e if e["_TIPO"] == "IVA" else float("nan"),
                "IT ESPERADO Bs": float("nan"),
                "IT SAP Bs": importe_e if e["_TIPO"] == "IT" else float("nan"),
                "QUÉ REVISAR": (
                    f"Motivo: {e['_ERROR']}. "
                    "Revisar la fila en el mayor SAP (cuenta "
                    f"{'IVA' if e['_TIPO'] == 'IVA' else 'IT'}) y corregir el dato o el asiento."
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

    resultado = ResultadoControl(
        hojas=hojas,
        ejecutivo=ejecutivo,
        observaciones=observaciones_amigables,
        netvalle=exportar,
        sap=sap_exportado,
        pendientes_sap=pendientes_sap,
        # Salidas calculadas por el original que NO se escriben en el Excel (hallazgo 3).
        # Filas SAP no interpretables (hoja SAP, columna ERROR DE LECTURA); pendiente decidir si van a OBSERVACIONES.
        diagnostico={"errores_sap": errores_sap},
    )

    if archivo_salida:
        escribir_excel(hojas, archivo_salida)

    _log("Tiempo: %.1f s", perf_counter() - inicio)

    return resultado

