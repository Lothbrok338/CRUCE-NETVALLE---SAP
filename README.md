# Control Tributario Integral

Migración del control tributario (NETVALLE vs SIAT vs SAP) de Google Colab a una aplicación web.

**Estado:** `core/`, `api/` y `web/` listos y desplegados en Railway (ver `docs/DESPLIEGUE.md`). Pendiente: regresión con archivos reales. Ver `docs/HALLAZGOS.md`.

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

## Levantar la API
```bash
pip install -r requirements-api.txt
AUTH_ENABLED=false uvicorn api.main:crear_app --factory --reload   # docs en http://localhost:8000/docs
```
Con `AUTH_ENABLED=true` (valor por defecto) hay que definir `AUTH_TOKEN` y enviar `Authorization: Bearer <token>`.

| Endpoint | Función |
|---|---|
| `POST /api/clasificar` | Vista previa de la clasificación (NETVALLE/SAP) sin crear control |
| `POST /api/controles` | Sube archivos, clasifica, valida y crea el job (acepta `netvalle` y `sap` para corregir) |
| `GET /api/controles/{id}` | Estado (en cola, procesando, listo, error) y las 6 tarjetas |
| `GET /api/controles/{id}/observaciones` | Tabla paginada: `pagina, por_pagina, q, control, punto, orden, direccion` |
| `GET /api/controles/{id}/excel` | Descarga el Excel |
| `GET /health` | Health check (Railway) |

## Levantar la web
```bash
cd web && npm install
API_URL=http://localhost:8000 npm run dev      # con la API corriendo en el puerto 8000
```

## Documentación
`docs/HALLAZGOS.md` (decisiones sobre el código original) · `docs/REGLAS_NEGOCIO.md` · `docs/ARQUITECTURA.md` · `docs/DESPLIEGUE.md`.
