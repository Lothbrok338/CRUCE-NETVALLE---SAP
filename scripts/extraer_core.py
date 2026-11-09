# Herramienta de trazabilidad: regenera core/ desde legacy/ (uso: python scripts/extraer_core.py .)
"""Extrae core/ desde legacy/control_tributario_colab.py cortando funciones por AST.

Solo se normalizan líneas en blanco repetidas (artefacto del pegado). La lógica no se toca,
salvo los reemplazos puntuales y verificados que se listan abajo (quitar print/display/escritura).
"""
import ast
import re
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
legacy = (REPO / "legacy/control_tributario_colab.py").read_text(encoding="utf-8")

# Quitar solo la línea mágica de Colab para poder parsear.
lineas = legacy.splitlines()
lineas = ["" if l.startswith("!pip") else l for l in lineas]
fuente = "\n".join(lineas) + "\n"
tree = ast.parse(fuente)


def colapsar(txt: str) -> str:
    txt = "\n".join(l.rstrip() for l in txt.splitlines())
    return re.sub(r"\n{3,}", "\n\n", txt)


funcs = {}
for n in tree.body:
    if isinstance(n, ast.FunctionDef):
        funcs[n.name] = colapsar(ast.get_source_segment(fuente, n))


def reemplazar(txt, viejo, nuevo, veces=1):
    assert txt.count(viejo) == veces, (viejo, txt.count(viejo))
    return txt.replace(viejo, nuevo)


def modulo(nombre, doc, imports, nombres, extra_antes=""):
    cuerpo = "\n\n\n".join(funcs[n] for n in nombres)
    txt = f'"""{doc}"""\n\n{imports}\n\n{extra_antes}\n\n{cuerpo}\n'
    txt = re.sub(r"\n{4,}", "\n\n\n", txt)
    (REPO / "core" / nombre).write_text(txt, encoding="utf-8")


def eq(nombre):  # etiqueta de trazabilidad
    return nombre


# ---------------- texto.py ----------------
modulo(
    "texto.py",
    "Limpieza y normalización de texto/estado/enteros. Origen: legacy, sección LIMPIEZA Y NORMALIZACIÓN.",
    "import re\nimport unicodedata\n\nimport numpy as np\nimport pandas as pd",
    ["texto_limpio", "normalizar_texto", "normalizar_entero", "normalizar_estado",
     "buscar_columna", "unir_unicos"],
)

# ---------------- impuestos.py ----------------
modulo(
    "impuestos.py",
    "Cálculo de impuestos con Decimal y ROUND_HALF_UP. Origen: legacy.redondear_impuesto.",
    "from decimal import Decimal, ROUND_HALF_UP\n\nimport numpy as np\nimport pandas as pd",
    ["redondear_impuesto"],
)

# ---------------- llaves.py ----------------
modulo(
    "llaves.py",
    "Llave de cruce punto|factura|AAAAMMDD y extracción de factura desde texto SAP. "
    "Origen: legacy.construir_llaves / extraer_factura_sap.",
    "import re\n\nimport pandas as pd\n\nfrom core.texto import texto_limpio",
    ["construir_llaves", "extraer_factura_sap"],
)

# ---------------- clasificacion.py ----------------
modulo(
    "clasificacion.py",
    "Clasificación automática de archivos. Origen: legacy, sección CLASIFICACIÓN AUTOMÁTICA.",
    "import pandas as pd\n\nfrom core.constantes import CUENTA_IT, CUENTA_IVA\n"
    "from core.texto import buscar_columna, normalizar_texto, texto_limpio",
    ["hojas_archivo", "contiene_base_netvalle", "cuentas_en_archivo", "clasificar_archivos"],
)

# ---------------- netvalle.py ----------------
modulo(
    "netvalle.py",
    "Lectura y preparación de NETVALLE. Origen: legacy, sección LECTURA Y PREPARACIÓN DE NETVALLE.",
    "import numpy as np\nimport pandas as pd\n\n"
    "from core.clasificacion import hojas_archivo\n"
    "from core.constantes import PUNTOS_SOUVENIRS, TOLERANCIA\n"
    "from core.impuestos import redondear_impuesto\n"
    "from core.llaves import construir_llaves\n"
    "from core.texto import buscar_columna, normalizar_entero, normalizar_estado, normalizar_texto",
    ["leer_netvalle", "preparar_netvalle"],
)

# ---------------- sap.py ----------------
sap_funcs = ["leer_sap", "separar_cuentas_sap", "preparar_sap", "vincular_reversos_manuales",
             "resumir_sap", "agregar_datos_sap", "grupo_sap_neutralizado",
             "construir_sap_sin_netvalle", "construir_errores_sap", "exportar_sap_legible"]
funcs["separar_cuentas_sap"] = reemplazar(
    funcs["separar_cuentas_sap"],
    '        print(f"⚠ Se ignoraron {otras:,} partidas de otras cuentas SAP.")',
    '        logger.warning("Se ignoraron %s partidas de otras cuentas SAP.", f"{otras:,}")',
)
modulo(
    "sap.py",
    "Lectura, preparación, reversos y resúmenes de los mayores SAP. "
    "Origen: legacy, secciones SAP.",
    "import logging\nimport os\n\nimport pandas as pd\n\n"
    "from core.clasificacion import hojas_archivo\n"
    "from core.constantes import CUENTA_IT, CUENTA_IVA, TOLERANCIA\n"
    "from core.llaves import construir_llaves\n"
    "from core.texto import buscar_columna, normalizar_texto, texto_limpio, unir_unicos\n\n"
    "logger = logging.getLogger(__name__)",
    sap_funcs,
)

# ---------------- control.py ----------------
gc = funcs["generar_control"]
# 1) firma y retorno: ya no escribe en disco ni depende de Colab
gc = reemplazar(gc, "def generar_control(netvalle_archivo, sap_archivos):",
                "def generar_control(netvalle_archivo, sap_archivos, archivo_salida=None):")
# 2) cortar desde la escritura del Excel hasta el final de la función
corte = gc.index("    with pd.ExcelWriter(")
gc = gc[:corte] + '''    resultado = ResultadoControl(
        hojas=hojas,
        ejecutivo=ejecutivo,
        observaciones=observaciones_amigables,
        netvalle=exportar,
        sap=sap_exportado,
        pendientes_sap=pendientes_sap,
        # Salidas calculadas por el original que NO se escriben en el Excel (hallazgo 3).
        diagnostico={
            "resumen": resumen,
            "dictamen": dictamen,
            "observaciones_originales": observaciones,
            "sap_sin_netvalle": sap_sin_net,
            "errores_sap": errores_sap,
        },
    )

    if archivo_salida:
        escribir_excel(hojas, archivo_salida)

    _log("Tiempo: %.1f s", perf_counter() - inicio)

    return resultado
'''
# 3) prints de cabecera / conteos → logging DEBUG (sin datos en logs de producción)
bloque_banner_ini = '''    print("\\n============================================")

    print("   CONTROL TRIBUTARIO INTEGRAL V3 — NETVALLE/SIAT + SAP")

    print("============================================\\n")
'''
# tras colapsar, los banners quedan separados por 1 línea en blanco
import re as _re
gc = _re.sub(r'    print\("\\n=+"\)\n\n    print\("   CONTROL TRIBUTARIO INTEGRAL V3[^\n]*\n\n    print\("=+\\n"\)\n',
             "", gc, count=1)
assert "CONTROL TRIBUTARIO INTEGRAL V3" not in gc
for viejo, nuevo in [
    ('print(f"✓ NETVALLE: {len(net_raw):,} registros (hoja {hoja_net})")',
     '_log("NETVALLE: %s registros", f"{len(net_raw):,}")'),
    ('print(f"✓ SAP combinado: {len(sap_raw):,} partidas ({origen_sap})")',
     '_log("SAP combinado: %s partidas", f"{len(sap_raw):,}")'),
    ('print(f"  · IVA: {len(iva_raw):,} partidas")', '_log("IVA: %s partidas", f"{len(iva_raw):,}")'),
    ('print(f"  · IT:  {len(it_raw):,} partidas")', '_log("IT: %s partidas", f"{len(it_raw):,}")'),
]:
    gc = reemplazar(gc, viejo, nuevo)
assert "print(" not in gc and "display(" not in gc, [l for l in gc.splitlines() if "print(" in l or "display(" in l]
funcs["generar_control"] = gc

# helpers que viven junto a generar_control
modulo(
    "control.py",
    "Evaluación del control y motor principal. Origen: legacy, secciones EVALUACIÓN DEL CONTROL y "
    "MOTOR PRINCIPAL. generar_control ya no escribe a disco por defecto, no imprime ni usa Colab: "
    "devuelve un ResultadoControl y escribe el Excel solo si se pasa archivo_salida.",
    "import logging\nfrom dataclasses import dataclass, field\nfrom time import perf_counter\n\n"
    "import numpy as np\nimport pandas as pd\n\n"
    "from core.clasificacion import hojas_archivo\n"
    "from core.constantes import AZUL, CELESTE, ROJO, TOLERANCIA\n"
    "from core.excel import escribir_excel\n"
    "from core.netvalle import leer_netvalle, preparar_netvalle\n"
    "from core.sap import (\n    agregar_datos_sap, construir_errores_sap, construir_sap_sin_netvalle,\n"
    "    exportar_sap_legible, grupo_sap_neutralizado, leer_sap, preparar_sap,\n"
    "    resumir_sap, separar_cuentas_sap, vincular_reversos_manuales,\n)\n"
    "from core.texto import buscar_columna, normalizar_estado, normalizar_texto, unir_unicos\n\n"
    "logger = logging.getLogger(__name__)\n_log = logger.debug",
    ["evaluar_fila", "construir_exportacion_netvalle", "determinar_dictamen", "generar_control"],
    extra_antes='''
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
''',
)

# ---------------- excel.py ----------------
modulo(
    "excel.py",
    "Formato del Excel final. Origen: legacy.formatear_hoja y el bloque ExcelWriter de generar_control.",
    "import pandas as pd\n\nfrom core.constantes import BLANCO\n"
    "from core.texto import normalizar_texto, texto_limpio",
    ["formatear_hoja"],
)
with open(REPO / "core" / "excel.py", "a", encoding="utf-8") as f:
    f.write('''

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
''')

# ---------------- constantes.py ----------------
consts = [n for n in tree.body if isinstance(n, ast.Assign)
          and isinstance(n.targets[0], ast.Name)
          and n.targets[0].id in {"ARCHIVO_FINAL", "CUENTA_IVA", "CUENTA_IT", "TOLERANCIA", "PUNTOS_SOUVENIRS",
                                  "AZUL", "ROJO", "VERDE", "NARANJA", "CELESTE", "GRIS", "MORADO", "BLANCO"}]
cuerpo = "\n".join(ast.get_source_segment(fuente, n) for n in consts)
(REPO / "core" / "constantes.py").write_text(
    '"""Reglas confirmadas y paleta. Origen: legacy, sección CONFIGURACIÓN Y REGLAS CONFIRMADAS.\n\n'
    'NO cambiar estos valores sin autorización (ver docs/REGLAS_NEGOCIO.md).\n"""\n\n'
    + cuerpo + "\n", encoding="utf-8")

# ---------------- __init__.py ----------------
(REPO / "core" / "__init__.py").write_text(
    '"""Lógica pura del Control Tributario Integral (sin Colab, ipywidgets ni frameworks web)."""\n\n'
    "import warnings\n\n"
    'warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")\n',
    encoding="utf-8")

print("OK:", sorted(p.name for p in (REPO / "core").glob("*.py")))
print("Funciones no asignadas a ningún módulo:",
      sorted(set(funcs) - {"texto_limpio","normalizar_texto","normalizar_entero","normalizar_estado","buscar_columna",
      "unir_unicos","redondear_impuesto","construir_llaves","extraer_factura_sap","hojas_archivo",
      "contiene_base_netvalle","cuentas_en_archivo","clasificar_archivos","leer_netvalle","preparar_netvalle",
      *sap_funcs,"evaluar_fila","construir_exportacion_netvalle","determinar_dictamen","generar_control",
      "formatear_hoja"}))
