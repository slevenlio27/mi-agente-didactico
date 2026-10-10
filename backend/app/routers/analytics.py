from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db
from ..rate_limit import rate_limit
from ..site_settings import get_site_settings

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/pageview", status_code=204)
def log_pageview(
    payload: schemas.PageViewCreate,
    db: Session = Depends(get_db),
    _rl=Depends(rate_limit("pageview", max_attempts=60, window_seconds=60)),
):
    # Endpoint público a propósito: registra visitas de cualquiera, con o sin
    # sesión iniciada, igual que cualquier analítica de sitio web básica.
    # No guarda IP ni user-agent — solo la ruta y, si hay sesión, el usuario.
    if not get_site_settings(db).analytics_enabled:
        return None  # el admin apagó las estadísticas: no se guarda nada
    view = models.PageView(path=payload.path[:255])
    db.add(view)
    db.commit()
    return None
