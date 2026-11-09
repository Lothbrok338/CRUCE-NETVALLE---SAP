"""Ejecuta el código ORIGINAL de Colab (legacy/) simulando google.colab, ipywidgets e IPython.

Solo sirve para pruebas de equivalencia: el original no se modifica; se le sustituyen en
memoria los módulos de Colab por simulacros y se omite la línea `!pip`.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

RUTA = Path(__file__).resolve().parents[1] / "legacy" / "control_tributario_colab.py"


def cargar_legacy():
    for nombre in ("google", "google.colab", "IPython", "IPython.display", "ipywidgets"):
        sys.modules[nombre] = MagicMock()
    codigo = "\n".join("" if l.startswith("!pip") else l for l in RUTA.read_text(encoding="utf-8").splitlines())
    espacio = {"__name__": "legacy_colab"}
    exec(compile(codigo, str(RUTA), "exec"), espacio)
    return espacio
