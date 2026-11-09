# Arquitectura

`core/` (pandas puro) → `api/` (FastAPI) → `web/` (Next.js). `legacy/` es solo referencia.

## Trazabilidad core ↔ original
Los nombres de función son idénticos a `legacy/control_tributario_colab.py`. `core/` se extrajo del original
sin cambiar lógica; después se aplicaron solo las decisiones listadas en `docs/HALLAZGOS.md`.

| Módulo | Funciones |
|---|---|
| `constantes.py` | reglas y paleta |
| `texto.py` | texto_limpio, normalizar_texto, normalizar_entero, normalizar_estado, buscar_columna, unir_unicos |
| `impuestos.py` | redondear_impuesto |
| `llaves.py` | construir_llaves, extraer_factura_sap |
| `clasificacion.py` | hojas_archivo, contiene_base_netvalle, cuentas_en_archivo, clasificar_archivos |
| `netvalle.py` | leer_netvalle, preparar_netvalle |
| `sap.py` | leer_sap, separar_cuentas_sap, preparar_sap, vincular_reversos_manuales, resumir_sap, agregar_datos_sap, grupo_sap_neutralizado, construir_errores_sap, exportar_sap_legible |
| `control.py` | evaluar_fila, construir_exportacion_netvalle, generar_control, `ResultadoControl` |
| `excel.py` | formatear_hoja, escribir_excel |

Diferencias deliberadas: `generar_control(netvalle, sap, archivo_salida=None)` devuelve `ResultadoControl`
(el original devolvía el nombre del archivo) y solo escribe el Excel si se indica `archivo_salida`.
Se omiten `actualizar_progreso`, `click_procesar`, `ejecutar_control_sap` y el panel de widgets (interfaz Colab).

## Pruebas
`pytest` (datos sintéticos en `tests/datos_sinteticos.py`). `tests/test_equivalencia_legacy.py` ejecuta el original
con Colab simulado y compara las 4 hojas y formatos. `tests/test_regresion_real.py` queda omitida hasta recibir muestras.
