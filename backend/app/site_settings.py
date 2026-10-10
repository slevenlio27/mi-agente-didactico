"""Acceso a la configuración global del sitio y verificaciones de funciones.

Las funciones desactivadas desde el panel de admin se bloquean aquí, en el
servidor. Ocultar un botón en el frontend no basta: cualquiera puede llamar
a la API directamente.
"""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models

PROVIDER_FLAGS = {
    "anthropic": "provider_anthropic_enabled",
    "openai": "provider_openai_enabled",
    "gemini": "provider_gemini_enabled",
}


def get_site_settings(db: Session) -> models.SiteSettings:
    row = db.get(models.SiteSettings, 1)
    if row is None:
        # Normalmente ya existe (se crea al arrancar). Si dos peticiones simultáneas
        # intentan crearla a la vez, la segunda choca con la clave única: en ese caso
        # se descarta su intento y se lee la fila que creó la primera.
        try:
            row = models.SiteSettings(id=1)
            db.add(row)
            db.commit()
            db.refresh(row)
        except IntegrityError:
            db.rollback()
            row = db.get(models.SiteSettings, 1)
    return row


def require_feature(db: Session, flag: str, message: str) -> models.SiteSettings:
    settings = get_site_settings(db)
    if not getattr(settings, flag):
        raise HTTPException(status_code=403, detail=message)
    return settings


def require_provider(db: Session, provider: str) -> None:
    settings = get_site_settings(db)
    flag = PROVIDER_FLAGS.get(provider)
    if flag is None or not getattr(settings, flag):
        raise HTTPException(
            status_code=403,
            detail="Ese proveedor de IA está desactivado en este sitio. Elige otro en Preferencias de IA.",
        )
