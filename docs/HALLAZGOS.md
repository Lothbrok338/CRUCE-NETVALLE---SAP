# Hallazgos del código original

Cada hallazgo se verificó con pruebas (`tests/test_hallazgos.py`). **`core/` conserva el comportamiento
original**: ningún hallazgo se corrigió. Las decisiones marcadas **PENDIENTE** esperan confirmación del usuario.

| # | Hallazgo | Estado | Decisión |
|---|---|---|---|
| 1 | Filas con error de lectura SAP no llegan a OBSERVACIONES | Confirmado (matizado) | **PENDIENTE** |
| 2 | Dos cálculos de "SAP sin NETVALLE" | Confirmado: NO equivalentes | **No unificar** (ver abajo) |
| 3 | Código calculado y no exportado | Confirmado | **Conservado** hasta decisión |
| 4 | Escapes sospechosos en regex | Efecto inofensivo | **Sin cambio** (propuesto) |
| 5 | Dependencias de Colab | Resuelto | Eliminadas de `core/` |
| 6 | *(nuevo)* Anuladas/incompletas "REVISAR" no se exportan | Confirmado | **PENDIENTE** |
| 7 | *(nuevo)* El color de encabezado del Excel no se ve | Confirmado (pandas 2.3.3) | **PENDIENTE** |

## 1. Filas con error de lectura SAP (`_ERROR != ""`)
Matiz respecto a lo reportado: **sí se exportan**, pero solo en la hoja `SAP` (columna `ERROR DE LECTURA`).
No aparecen en `OBSERVACIONES` ni en las tarjetas de `RESUMEN_EJECUTIVO`; solo suman al dictamen interno
(`ERRORES O DUPLICADOS SAP`), que tampoco se escribe. Un usuario que mire solo `OBSERVACIONES` no las verá.
**Propuesta:** incluirlas en `OBSERVACIONES` (CONTROL = "SAP sin coincidencia" o un valor nuevo "SAP error de lectura").
Cambiaría el conteo de "FACTURAS PARA REVISAR". **Requiere tu confirmación.**

## 2. Dos cálculos de "SAP sin NETVALLE"
`construir_sap_sin_netvalle` (solo alimenta el dictamen) y `sap_sin_justificar` (el que va a OBSERVACIONES)
**dan resultados distintos**. Caso demostrado (`test_h2`): una factura anulada en NETVALLE que SAP registró
con otra fecha. El primero la cuenta como "sin respaldo"; el segundo la omite porque NETVALLE la tiene anulada.
Como el resultado cambia, **no se unificó**. Para unificar hay que decidir cuál criterio es el correcto.

## 3. Código sin uso en la salida final
`resumen`, `determinar_dictamen`, `observaciones` y la parte de `construir_errores_sap` no llegan al Excel.
En `core/` se calculan igual y se devuelven en `ResultadoControl.diagnostico` (no se eliminó nada).
**Propuesta:** eliminarlos tras tu OK, o promoverlos a salida si el dictamen te sirve.

## 4. Escapes en regex
Probado con `F-123`, `F 123`, `F.123`, `F123`, `1234.0`, `1234,0`, `1234`: **todos dan el resultado esperado**.
El doble escape `[\\\\.:#-]` / `[\\\\.,]` solo agrega aceptar una barra invertida literal (`F\123`, `1234\0`),
algo que nunca aparece en la práctica. **Propuesta:** dejarlo como está (cero riesgo de regresión).

## 5. Dependencias de Colab
`google.colab.files`, `ipywidgets`, `IPython.display` y `!pip install` no existen en `core/`
(`test_h5` lo verifica). `print`/`display` pasaron a `logging.DEBUG` y sin datos de facturas.
Las dependencias van en `requirements.txt` (`pandas<3` para igualar el comportamiento de Colab).

## 6. Anuladas e incompletas con resultado "REVISAR" no se exportan (nuevo)
`OBSERVACIONES` se construye solo con facturas **válidas** (`validas & observaciones_mask`).
Resultados como `ANULADA SIN REVERSO IVA - REVISAR`, `REVERSO IVA SIN ORIGINAL - REVISAR`,
`ANULADA SOUVENIR - REVISAR IVA/IT` o `INCOMPLETA O ESTADO NO RECONOCIDO - REVISAR` quedan solo en la hoja
`NETVALLE`; no aparecen en `OBSERVACIONES` ni cuentan en "FACTURAS PARA REVISAR", aunque dicen REVISAR.
Con los datos sintéticos: 6 facturas en esa situación. **Puede ocultar pendientes reales. Requiere tu decisión.**

## 7. Color de encabezado (nuevo)
`formatear_hoja` aplica el color con `ws.set_row(0, 42, encabezado)`, pero pandas escribe cada celda de
encabezado con su propio formato, que anula el de la fila. Resultado: en las columnas con datos el encabezado
va en negrita y **sin relleno** (en `OBSERVACIONES` solo se pinta el resto de la fila). Se replica igual para
mantener paridad. **Verificar contra un Excel real del original;** si lo quieres coloreado, es un cambio visual menor.
