# Hallazgos del código original

Cada hallazgo se verificó con pruebas (`tests/test_hallazgos.py`). **`core/` conserva el comportamiento
original**: ningún hallazgo se corrigió. Las decisiones marcadas **PENDIENTE** esperan confirmación del usuario.

| # | Hallazgo | Decisión del usuario | Estado |
|---|---|---|---|
| 1 | Filas con error de lectura SAP no llegan a OBSERVACIONES | Probar incluirlas (CONTROL = "SAP error de lectura"); revertir si no convence | **En prueba** |
| 2 | Dos cálculos de "SAP sin NETVALLE" | Si la factura está anulada en NETVALLE y también en SAP, no se observa | **Resuelto**: se conserva el criterio exportado; se eliminó el duplicado |
| 3 | Código calculado y no exportado | "Lo más lógico" | **Resuelto**: eliminado (`resumen`, `determinar_dictamen`, `observaciones`, `construir_sap_sin_netvalle`) |
| 4 | Escapes en regex | OK | **Sin cambio** |
| 5 | Dependencias de Colab | n/a | **Resuelto** |
| 6 | Anuladas/incompletas "REVISAR" no se exportan | Incompletas SÍ a OBSERVACIONES; anuladas se ignoran siempre | **Resuelto** |
| 7 | Encabezados sin color en el Excel | Corregir | **Resuelto** |
| 8 | *(nuevo)* `QUÉ PASÓ` no refleja el motivo real | Poner el motivo real | **Resuelto** |

Los detalles del análisis original siguen abajo. Las secciones 2, 3, 6 y 7 describen el comportamiento
**original**; el código actual de `core/` ya refleja las decisiones de la tabla.

## Qué son los "errores de lectura" (hallazgo 1)
Filas del mayor SAP que el programa no puede interpretar. Se detectan en `preparar_sap` y se marcan con un texto:
cuenta distinta a la esperada, punto de emisión vacío, texto sin número de factura (`Txt.pos.reg.diario` sin `F123`),
fecha vacía, clave contable distinta de 40/50, importe vacío, o reverso manual ambiguo. Esas filas se excluyen del cruce,
y hoy solo se ven en la hoja `SAP` (columna `ERROR DE LECTURA`). **Recomendación:** listarlas en OBSERVACIONES para que
nadie las pase por alto. Pendiente de tu respuesta.

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

## Cambios aplicados respecto al original (por decisión del usuario)
- Hallazgo 2/3: `core/` ya no contiene `construir_sap_sin_netvalle`, `determinar_dictamen` ni las tablas no exportadas.
- Hallazgo 6: las facturas con estado incompleto o no reconocido entran a OBSERVACIONES con motivo
  "Factura INCOMPLETA en NETVALLE" (texto nuevo; no existía en el original). Las anuladas nunca se observan.
  Esto cambia el conteo de "FACTURAS PARA REVISAR" y el resultado general cuando hay incompletas.
- Hallazgo 7: los encabezados se escriben con el color de cada hoja (azul 1F4E78, rojo C00000, celeste 5B9BD5), letra blanca.
- `scripts/extraer_core.py` se eliminó: `core/` ya no es una copia exacta del original.

## 8. `QUÉ PASÓ` en OBSERVACIONES no dice el motivo real (nuevo)
En OBSERVACIONES, `QUÉ PASÓ` solo tiene dos textos para facturas de NETVALLE: "Misma referencia en SAP, pero los
datos no coinciden" o "No se encontró la contabilización esperada en SAP". El motivo real calculado
(`FALTA EN SAP IT`, `DUPLICADA EN SAP IT - REVISAR`, `DIFERENCIA IMPORTE IT`, `FACTURA VÁLIDA CON REVERSO IVA - REVISAR`…)
se guarda en `caso["motivos"]` pero **nunca se escribe**. Efecto: una factura con IT duplicada o con diferencia de importe
aparece como "No se encontró la contabilización esperada", aunque SAP sí la tiene (la hoja NETVALLE sí muestra el motivo exacto).
**Propuesta:** agregar el motivo real al texto de `QUÉ PASÓ` (p. ej. "DUPLICADA EN SAP IT - REVISAR"). No se cambió.

**Aplicado (hallazgo 8):** `QUÉ PASÓ` ahora lleva el resultado exacto (p. ej. `DUPLICADA EN SAP IT - REVISAR`); si hay varios, separados por ` / `.
