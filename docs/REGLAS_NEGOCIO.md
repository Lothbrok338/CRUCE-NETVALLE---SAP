# Reglas de negocio (no se cambian)

Fuente: `legacy/control_tributario_colab.py`. Constantes en `core/constantes.py`.

- `CUENTA_IVA = "210106001"`, `CUENTA_IT = "610501001"`, `TOLERANCIA = 0.01`.
- `PUNTOS_SOUVENIRS = {"SFC103", "SFC204", "SFC503", "SFC303", "SFC403"}`.
- IVA 13% para ventas gravadas y souvenirs; IT 3% solo souvenirs. `Decimal` + `ROUND_HALF_UP`, 2 decimales.
- Estados NETVALLE: V (válida), A (anulada), I (incompleta).
- Tratamiento: ANULADA, INCOMPLETA - REVISAR, SOUVENIR - IVA 13% + IT 3%, LIBRO - EXENTO IVA E IT, VENTA GRAVADA - IVA 13%.
  Un libro válido no souvenir con débito fiscal ≤ tolerancia es exento y queda fuera del control.
- Llave de cruce: `PUNTO|FACTURA|AAAAMMDD`.
- Reversos: claves 50/40 en IVA (original/reverso) y 40/50 en IT. Vínculo manual solo si el candidato es único
  (factura + fecha + importe absoluto).
- Grupo SAP con original y reverso que suman cero: no es alerta ("AJUSTES SAP NEUTRALIZADOS").
- Motor 1 (RESUMEN_CRUCE, NETVALLE, SIAT) es fuente de verdad: no se recalcula.

## Orden de evaluación de `evaluar_fila`
1. Sin llave → `NETVALLE SIN LLAVE COMPLETA - REVISAR`
2. Estado A (souvenir → anuladas con IVA e IT; luego movimiento, reversos, originales sin reverso, reversos sin original)
3. Estado ≠ V → `INCOMPLETA O ESTADO NO RECONOCIDO - REVISAR`
4. Exento → `LIBRO EXENTO ...`
5. Falta/duplicada/reverso/diferencia de IVA (en ese orden); si es souvenir, lo mismo para IT.

## Textos de resultado (contrato; no cambiar)
CARGADA CORRECTAMENTE · SOUVENIR - IVA E IT CORRECTOS · LIBRO EXENTO - SIN IMPUESTOS ·
LIBRO EXENTO CON PARTIDA TRIBUTARIA - REVISAR · FALTA EN SAP IVA · FALTA EN SAP IT ·
DUPLICADA EN SAP IVA - REVISAR · DUPLICADA EN SAP IT - REVISAR · DIFERENCIA IMPORTE IVA · DIFERENCIA IMPORTE IT ·
FACTURA VÁLIDA CON REVERSO IVA - REVISAR · SOUVENIR VÁLIDO CON REVERSO IT - REVISAR ·
ANULADA Y REVERTIDA CORRECTAMENTE · ANULADA SIN MOVIMIENTO TRIBUTARIO · ANULADA SIN REVERSO IVA/IT - REVISAR ·
REVERSO IVA/IT SIN ORIGINAL - REVISAR · ANULADA SOUVENIR - REVISAR IVA/IT ·
INCOMPLETA O ESTADO NO RECONOCIDO - REVISAR · NETVALLE SIN LLAVE COMPLETA - REVISAR.
(`tests/test_evaluar_fila.py` falla si aparece un texto no probado.)
