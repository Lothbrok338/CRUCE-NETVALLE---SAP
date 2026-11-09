"""Autenticación por token Bearer, activable con AUTH_ENABLED.

Estructura lista para reemplazar por OIDC/JWT más adelante: solo cambia `verificar_acceso`.
"""
import hmac

from fastapi import HTTPException, Request, status


def verificar_acceso(request: Request) -> None:
    settings = request.app.state.settings
    if not settings.auth_enabled:
        return
    if not settings.auth_token:
        # Falla cerrado: con la autenticación activa y sin token configurado nadie entra.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Autenticación activada pero AUTH_TOKEN no está configurado.")
    cabecera = request.headers.get("Authorization", "")
    esquema, _, token = cabecera.partition(" ")
    if esquema.lower() != "bearer" or not hmac.compare_digest(token.encode(), settings.auth_token.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autorizado.", headers={"WWW-Authenticate": "Bearer"})
