"""Un caso por cada resultado posible de evaluar_fila (textos = contrato con los usuarios)."""
import ast
import inspect

import pytest

from core.control import evaluar_fila


def fila(**kw):
    base = {
        "_ESTADO": "V", "_LLAVE": "SFC001|1|20260110", "_SOUVENIR": False, "_EXENTO": False,
        "_IVA_CANT_ORIGINAL": 1, "_IVA_CANT_REVERSO": 0, "_IT_CANT_ORIGINAL": 0, "_IT_CANT_REVERSO": 0,
        "_IVA_SALDO": 0.0, "_IT_SALDO": 0.0, "_DIF_IVA": 0.0, "_DIF_IT": 0.0,
    }
    base.update(kw)
    return base


CASOS = [
    ("NETVALLE SIN LLAVE COMPLETA - REVISAR", fila(_LLAVE="")),
    # --- anuladas
    ("ANULADA Y REVERTIDA CORRECTAMENTE", fila(_ESTADO="A", _SOUVENIR=True, _IVA_CANT_ORIGINAL=1, _IVA_CANT_REVERSO=1, _IT_CANT_ORIGINAL=1, _IT_CANT_REVERSO=1)),
    ("ANULADA SOUVENIR - REVISAR IVA/IT", fila(_ESTADO="A", _SOUVENIR=True, _IVA_CANT_ORIGINAL=1, _IVA_CANT_REVERSO=1, _IT_CANT_ORIGINAL=0)),
    ("ANULADA SIN MOVIMIENTO TRIBUTARIO", fila(_ESTADO="A", _IVA_CANT_ORIGINAL=0)),
    ("ANULADA SIN REVERSO IVA - REVISAR", fila(_ESTADO="A", _IVA_CANT_ORIGINAL=1, _IVA_CANT_REVERSO=0)),
    ("ANULADA SIN REVERSO IT - REVISAR", fila(_ESTADO="A", _IVA_CANT_ORIGINAL=0, _IT_CANT_ORIGINAL=1, _IT_CANT_REVERSO=0)),
    ("REVERSO IVA SIN ORIGINAL - REVISAR", fila(_ESTADO="A", _IVA_CANT_ORIGINAL=0, _IVA_CANT_REVERSO=1)),
    ("REVERSO IT SIN ORIGINAL - REVISAR", fila(_ESTADO="A", _IVA_CANT_ORIGINAL=0, _IT_CANT_ORIGINAL=0, _IT_CANT_REVERSO=1)),
    ("ANULADA Y REVERTIDA CORRECTAMENTE", fila(_ESTADO="A", _IVA_CANT_ORIGINAL=1, _IVA_CANT_REVERSO=1)),
    # --- estado no válido
    ("INCOMPLETA O ESTADO NO RECONOCIDO - REVISAR", fila(_ESTADO="I")),
    # --- exentos
    ("LIBRO EXENTO CON PARTIDA TRIBUTARIA - REVISAR", fila(_EXENTO=True, _IVA_CANT_ORIGINAL=1)),
    ("LIBRO EXENTO - SIN IMPUESTOS", fila(_EXENTO=True, _IVA_CANT_ORIGINAL=0)),
    # --- válidas gravadas
    ("FALTA EN SAP IVA", fila(_IVA_CANT_ORIGINAL=0)),
    ("DUPLICADA EN SAP IVA - REVISAR", fila(_IVA_CANT_ORIGINAL=2)),
    ("FACTURA VÁLIDA CON REVERSO IVA - REVISAR", fila(_IVA_CANT_REVERSO=1)),
    ("DIFERENCIA IMPORTE IVA", fila(_DIF_IVA=1.0)),
    ("CARGADA CORRECTAMENTE", fila()),
    # --- souvenirs
    ("FALTA EN SAP IT", fila(_SOUVENIR=True, _IT_CANT_ORIGINAL=0)),
    ("DUPLICADA EN SAP IT - REVISAR", fila(_SOUVENIR=True, _IT_CANT_ORIGINAL=2)),
    ("SOUVENIR VÁLIDO CON REVERSO IT - REVISAR", fila(_SOUVENIR=True, _IT_CANT_ORIGINAL=1, _IT_CANT_REVERSO=1)),
    ("DIFERENCIA IMPORTE IT", fila(_SOUVENIR=True, _IT_CANT_ORIGINAL=1, _DIF_IT=-1.0)),
    ("SOUVENIR - IVA E IT CORRECTOS", fila(_SOUVENIR=True, _IT_CANT_ORIGINAL=1)),
]


@pytest.mark.parametrize("esperado,datos", CASOS, ids=[f"{i:02d}-{c[0][:40]}" for i, c in enumerate(CASOS)])
def test_evaluar_fila(esperado, datos):
    import pandas as pd
    assert evaluar_fila(pd.Series(datos)) == esperado


def test_cobertura_de_todos_los_resultados():
    """Si el original devolviera un texto que no probamos, esta prueba falla."""
    arbol = ast.parse(inspect.getsource(evaluar_fila).lstrip())
    literales = {n.value.value for n in ast.walk(arbol)
                 if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)}
    # los return multi-línea con conditional-expression
    for n in ast.walk(arbol):
        if isinstance(n, ast.IfExp):
            for ramal in (n.body, n.orelse):
                if isinstance(ramal, ast.Constant):
                    literales.add(ramal.value)
    assert literales == {esperado for esperado, _ in CASOS}


def test_orden_de_evaluacion_anulada_gana_a_exento():
    import pandas as pd
    # _EXENTO sólo se evalúa si estado == "V"; una anulada exenta se trata como anulada
    assert evaluar_fila(pd.Series(fila(_ESTADO="A", _EXENTO=True, _IVA_CANT_ORIGINAL=0))) == "ANULADA SIN MOVIMIENTO TRIBUTARIO"


def test_orden_de_evaluacion_iva_antes_que_it():
    import pandas as pd
    # souvenir con IVA duplicado y sin IT: se reporta primero el IVA
    r = evaluar_fila(pd.Series(fila(_SOUVENIR=True, _IVA_CANT_ORIGINAL=2, _IT_CANT_ORIGINAL=0)))
    assert r == "DUPLICADA EN SAP IVA - REVISAR"
