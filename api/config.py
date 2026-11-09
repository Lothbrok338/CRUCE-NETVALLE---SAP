"""Configuración por variables de entorno (ver .env.example). Se lee en cada llamada para poder probarla."""
import os
from dataclasses import dataclass


def _bool(valor: str, defecto: bool) -> bool:
    if valor is None or valor == "":
        return defecto
    return valor.strip().lower() in {"1", "true", "yes", "si", "sí"}


@dataclass(frozen=True)
class Settings:
    auth_enabled: bool = True          # seguro por defecto; desactivar solo en desarrollo
    auth_token: str = ""
    result_ttl_hours: float = 24.0
    max_upload_mb: int = 50
    cors_origins: tuple = ("http://localhost:3000",)
    workers: int = 2

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def get_settings() -> Settings:
    e = os.environ
    return Settings(
        auth_enabled=_bool(e.get("AUTH_ENABLED"), True),
        auth_token=e.get("AUTH_TOKEN", ""),
        result_ttl_hours=float(e.get("RESULT_TTL_HOURS", "24")),
        max_upload_mb=int(e.get("MAX_UPLOAD_MB", "50")),
        cors_origins=tuple(x.strip() for x in e.get("CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip()),
        workers=int(e.get("API_WORKERS", "2")),
    )
