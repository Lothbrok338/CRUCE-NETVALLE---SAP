# Control Tributario Integral

Migración del control tributario (NETVALLE vs SIAT vs SAP) de Google Colab a una aplicación web.

**Estado:** Etapa 1 (preparación). Ver el plan de trabajo en `docs/`.

| Carpeta | Contenido |
|---|---|
| `core/` | Lógica pura en pandas (sin Colab, sin frameworks web) |
| `api/` | FastAPI: endpoints, jobs, descargas |
| `web/` | Next.js + TypeScript + Tailwind + shadcn/ui |
| `tests/` | pytest (core, api) y pruebas de web |
| `legacy/` | Código original de Colab. Solo lectura |
| `docs/` | HALLAZGOS, REGLAS_NEGOCIO, ARQUITECTURA, DESPLIEGUE |

Instrucciones de ejecución local y despliegue: se completan en la Etapa 8.
