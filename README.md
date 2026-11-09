# Control Tributario Integral

Migración del control tributario (NETVALLE vs SIAT vs SAP) de Google Colab a una aplicación web.

**Estado:** Etapas 1–3 completas (`core/` + pruebas). `api/`, `web/` y despliegue pendientes. Ver `docs/HALLAZGOS.md`.

| Carpeta | Contenido |
|---|---|
| `core/` | Lógica pura en pandas (sin Colab, sin frameworks web) |
| `api/` | FastAPI: endpoints, jobs, descargas |
| `web/` | Next.js + TypeScript + Tailwind + shadcn/ui |
| `tests/` | pytest (core, api) y pruebas de web |
| `legacy/` | Código original de Colab. Solo lectura |
| `docs/` | HALLAZGOS, REGLAS_NEGOCIO, ARQUITECTURA, DESPLIEGUE |

Instrucciones de ejecución local y despliegue: se completan en la Etapa 8.

## Ejecutar pruebas
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```
