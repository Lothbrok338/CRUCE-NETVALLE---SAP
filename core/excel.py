"""Formato del Excel final. Origen: legacy.formatear_hoja y el bloque ExcelWriter de generar_control."""

import pandas as pd

from core.constantes import BLANCO
from core.texto import normalizar_texto, texto_limpio


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

    # CAMBIO vs original (hallazgo 7): pandas escribe los encabezados con su propio formato, que anulaba el
    # color de la fila. Se reescriben con el formato de color para que el encabezado realmente se vea.
    for indice, columna in enumerate(dataframe.columns):
        ws.write(0, indice, str(columna), encabezado)

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


def escribir_excel(hojas, ruta):
    """Escribe el libro con xlsxwriter. Origen: bloque `with pd.ExcelWriter(...)` de generar_control."""
    with pd.ExcelWriter(
        ruta,
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_urls": False}},
    ) as writer:
        for nombre, dataframe, _color in hojas:
            dataframe.to_excel(writer, sheet_name=nombre, index=False)

        wb = writer.book

        for nombre, dataframe, color in hojas:
            formatear_hoja(writer.sheets[nombre], wb, dataframe, color)

    return ruta
