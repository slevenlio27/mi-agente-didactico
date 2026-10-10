from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import get_db
from ..config import settings
from ..site_settings import get_site_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/public", response_model=schemas.SiteSettingsOut)
def public_settings(db: Session = Depends(get_db)):
    # Público a propósito: colores, nombre y funciones activas los necesita
    # el sitio antes de que nadie inicie sesión. No contiene nada sensible.
    out = schemas.SiteSettingsOut.model_validate(get_site_settings(db))
    out.google_client_id = settings.GOOGLE_CLIENT_ID
    return out
