"""Datos 100% sintéticos (no reales) que cubren cada resultado de evaluar_fila,
reversos manuales, ajustes neutralizados, filas con error y SAP sin NETVALLE."""
from pathlib import Path

import pandas as pd

FECHA = pd.Timestamp("2026-01-10")
FECHA_DISTINTA = pd.Timestamp("2026-01-11")
NORMAL = "SFC001"
SOUVENIR = "SFC103"

# (punto, factura, estado, total, debito, resultado esperado)
NETVALLE = [
    (NORMAL, 1001, "V", 100.0, 13.0, "CARGADA CORRECTAMENTE"),
    (NORMAL, 1002, "V", 200.0, 26.0, "FALTA EN SAP IVA"),
    (NORMAL, 1003, "V", 100.0, 13.0, "DUPLICADA EN SAP IVA - REVISAR"),
    (NORMAL, 1004, "V", 100.0, 13.0, "FACTURA VÁLIDA CON REVERSO IVA - REVISAR"),
    (NORMAL, 1005, "V", 100.0, 13.0, "DIFERENCIA IMPORTE IVA"),
    (NORMAL, 1006, "V", 100.0, 0.0, "LIBRO EXENTO - SIN IMPUESTOS"),
    (NORMAL, 1007, "V", 100.0, 0.0, "LIBRO EXENTO CON PARTIDA TRIBUTARIA - REVISAR"),
    (SOUVENIR, 2001, "V", 100.0, 13.0, "SOUVENIR - IVA E IT CORRECTOS"),
    (SOUVENIR, 2002, "V", 100.0, 13.0, "FALTA EN SAP IT"),
    (SOUVENIR, 2003, "V", 100.0, 13.0, "DUPLICADA EN SAP IT - REVISAR"),
    (SOUVENIR, 2004, "V", 100.0, 13.0, "SOUVENIR VÁLIDO CON REVERSO IT - REVISAR"),
    (SOUVENIR, 2005, "V", 100.0, 13.0, "DIFERENCIA IMPORTE IT"),
    (NORMAL, 3001, "A", 100.0, 13.0, "ANULADA SIN MOVIMIENTO TRIBUTARIO"),
    (NORMAL, 3002, "A", 100.0, 13.0, "ANULADA Y REVERTIDA CORRECTAMENTE"),
    (NORMAL, 3003, "A", 100.0, 13.0, "ANULADA SIN REVERSO IVA - REVISAR"),
    (NORMAL, 3004, "A", 100.0, 13.0, "ANULADA SIN REVERSO IT - REVISAR"),
    (NORMAL, 3005, "A", 100.0, 13.0, "REVERSO IVA SIN ORIGINAL - REVISAR"),
    (NORMAL, 3006, "A", 100.0, 13.0, "REVERSO IT SIN ORIGINAL - REVISAR"),
    (SOUVENIR, 3007, "A", 100.0, 13.0, "ANULADA Y REVERTIDA CORRECTAMENTE"),
    (SOUVENIR, 3008, "A", 100.0, 13.0, "ANULADA SOUVENIR - REVISAR IVA/IT"),
    (NORMAL, 4001, "I", 100.0, 13.0, "INCOMPLETA O ESTADO NO RECONOCIDO - REVISAR"),
    (NORMAL, 4002, "I", 0.0, 0.0, "INCOMPLETA O ESTADO NO RECONOCIDO - REVISAR"),  # monto 0: no se observa
    (NORMAL, 5001, "A", 100.0, 13.0, "ANULADA Y REVERTIDA CORRECTAMENTE"),  # reverso manual
    (NORMAL, None, "V", 100.0, 13.0, "NETVALLE SIN LLAVE COMPLETA - REVISAR"),
    # anulada en NETVALLE; SAP la registra con OTRA fecha (hallazgo 2)
    (NORMAL, 6001, "A", 100.0, 13.0, "ANULADA SIN MOVIMIENTO TRIBUTARIO"),
]

CUENTA_IVA, CUENTA_IT = "210106001", "610501001"


def _sap(cuenta, punto, factura, clave, importe, asiento, texto=None, fecha=FECHA):
    return {
        "Cuenta de mayor": cuenta,
        "Txt.pos.reg.diario": texto if texto is not None else f"Venta F{factura}",
        "AC creado por": punto,
        "Fe.contab.": fecha,
        "Clave contab.": clave,
        "Impte.moneda socied.": importe,
        "Asiento contable": asiento,
    }


def iva(punto, factura, clave, importe, asiento, fecha=FECHA):
    return _sap(CUENTA_IVA, punto, factura, clave, importe, asiento, fecha=fecha)


def it(punto, factura, clave, importe, asiento):
    return _sap(CUENTA_IT, punto, factura, clave, importe, asiento)


def filas_sap(incluir_errores=True):
    n, s = NORMAL, SOUVENIR
    f = []
    f += [iva(n, 1001, "50", -13.0, "A1001")]
    f += [iva(n, 1003, "50", -13.0, "A1003a"), iva(n, 1003, "50", -13.0, "A1003b")]
    f += [iva(n, 1004, "50", -13.0, "A1004a"), iva(n, 1004, "40", 13.0, "A1004b")]
    f += [iva(n, 1005, "50", -12.0, "A1005")]
    f += [iva(n, 1007, "50", -13.0, "A1007")]
    f += [iva(s, 2001, "50", -13.0, "A2001"), it(s, 2001, "40", 3.0, "T2001")]
    f += [iva(s, 2002, "50", -13.0, "A2002")]
    f += [iva(s, 2003, "50", -13.0, "A2003"), it(s, 2003, "40", 3.0, "T2003a"), it(s, 2003, "40", 3.0, "T2003b")]
    f += [iva(s, 2004, "50", -13.0, "A2004"), it(s, 2004, "40", 3.0, "T2004a"), it(s, 2004, "50", -3.0, "T2004b")]
    f += [iva(s, 2005, "50", -13.0, "A2005"), it(s, 2005, "40", 2.0, "T2005")]
    f += [iva(n, 3002, "50", -13.0, "A3002a"), iva(n, 3002, "40", 13.0, "A3002b")]
    f += [iva(n, 3003, "50", -13.0, "A3003")]
    f += [it(n, 3004, "40", 3.0, "T3004")]
    f += [iva(n, 3005, "40", 13.0, "A3005")]
    f += [it(n, 3006, "50", -3.0, "T3006")]
    f += [iva(s, 3007, "50", -13.0, "A3007a"), iva(s, 3007, "40", 13.0, "A3007b"),
          it(s, 3007, "40", 3.0, "T3007a"), it(s, 3007, "50", -3.0, "T3007b")]
    f += [iva(s, 3008, "50", -13.0, "A3008")]
    # reverso manual: el usuario SAP del reverso reemplazó al punto de emisión
    f += [iva(n, 5001, "50", -13.0, "A5001a"), iva("USUARIO1", 5001, "40", 13.0, "A5001b")]
    # ajuste neutralizado (original + reverso = 0) sin NETVALLE
    f += [iva(n, 9001, "50", -13.0, "A9001a"), iva(n, 9001, "40", 13.0, "A9001b")]
    f += [iva(n, 6001, "50", -13.0, "A6001", fecha=FECHA_DISTINTA)]
    # SAP sin NETVALLE (alerta real)
    f += [iva(n, 9002, "50", -13.0, "A9002")]
    # fila no interpretable (sin número de factura)
    if incluir_errores:
        f += [_sap(CUENTA_IVA, n, 0, "50", -5.0, "A9999", texto="SIN REFERENCIA DE FACTURA")]
    # otra cuenta: se ignora
    f += [_sap("999999999", n, 7777, "50", -1.0, "X1")]
    return f


def crear_archivos(directorio: Path, incluir_incompletas: bool = True):
    """Crea CRUCE.xlsx (RESUMEN_CRUCE/NETVALLE/SIAT) y SAP.xlsx. Devuelve (ruta_cruce, ruta_sap)."""
    directorio = Path(directorio)
    net = pd.DataFrame(
        [
            {
                "PUNTO DE EMISIÓN": p, "Nº DE FACTURA": fa, "FECHA": FECHA,
                "TOTAL FACTURA (A)": t, "DÉBITO FISCAL": d, "ESTADO": e,
            }
            for p, fa, e, t, d, _ in NETVALLE
            if incluir_incompletas or e != "I"
        ]
    )
    resumen_cruce = pd.DataFrame(
        {"CONTROL": ["FALTAN EN NETVALLE", "FALTAN EN SIAT", "DIFERENCIAS DE ESTADO"], "CANTIDAD": [0, 0, 0]}
    )
    total_v = float(net.loc[net["ESTADO"].eq("V"), "TOTAL FACTURA (A)"].sum())
    siat = pd.DataFrame({"ESTADO": ["V", "V"], "IMPORTE TOTAL DE LA VENTA": [total_v - 50.0, 50.0]})

    ruta_cruce = directorio / "CRUCE.xlsx"
    with pd.ExcelWriter(ruta_cruce, engine="openpyxl") as w:
        resumen_cruce.to_excel(w, sheet_name="RESUMEN_CRUCE", index=False)
        net.to_excel(w, sheet_name="NETVALLE", index=False)
        siat.to_excel(w, sheet_name="SIAT", index=False)

    ruta_sap = directorio / "SAP.xlsx"
    pd.DataFrame(filas_sap(incluir_errores=incluir_incompletas)).to_excel(ruta_sap, sheet_name="Hoja1", index=False)
    return str(ruta_cruce), str(ruta_sap)
