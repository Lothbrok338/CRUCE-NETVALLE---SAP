# Despliegue en Railway

Proyecto `CONTROL-TRIBUTARIO-INTEGRAL`, entorno `production`, dos servicios conectados a este repositorio (rama `main`).

| Servicio | Dockerfile | Público | Health check | Variables |
|---|---|---|---|---|
| `api` | `Dockerfile.api` | **No** (solo red privada `api.railway.internal`) | `/health` | `AUTH_ENABLED=false`, `RESULT_TTL_HOURS=24`, `MAX_UPLOAD_MB=50`, `PORT=8000` |
| `web` | `Dockerfile.web` | Sí (dominio `*.up.railway.app`) | `/` | `API_URL=http://api.railway.internal:8000`, `PORT=3000` |

## Decisiones de seguridad
- La API no tiene dominio público: solo la web puede llamarla por la red privada. Por eso `AUTH_ENABLED=false` es aceptable aquí.
  Si algún día se le da dominio público a la API, **activar** `AUTH_ENABLED=true`, definir `AUTH_TOKEN` en la API y el mismo valor en `API_TOKEN` de la web.
- La web no pide contraseña por decisión del dueño. Para activarla: variable `WEB_ACCESS_PASSWORD` en el servicio `web`.
- Los resultados viven en memoria/disco temporal del contenedor y se borran a las 24 h; al reiniciar el servicio se pierden.
- El repositorio es público: nunca subir `.xlsx`, `.env` ni datos reales (`.gitignore` ya los excluye).

## Rama de despliegue
Ambos servicios siguen la rama `main`: cada merge a `main` redespliega solo.

## Variables
Todas están documentadas en `.env.example`. Se editan en Railway → servicio → Variables.

## Dominio propio
Railway → servicio `web` → Settings → Networking → Custom Domain, y crear en el DNS el registro CNAME que indique.

## Verificación
1. `GET https://<dominio-web>/` responde 200.
2. En la web: subir CRUCE + SAP, ver las 6 tarjetas, entrar a Observaciones y descargar el Excel.
3. Logs: Railway → servicio → Logs (solo ids y estados; sin datos de facturas).
