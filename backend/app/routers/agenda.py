from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db
from ..site_settings import require_feature

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("/events", response_model=list[schemas.ClassEventOut])
def list_events(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.ClassEvent)
        .filter(models.ClassEvent.user_id == user.id)
        .order_by(models.ClassEvent.day_of_week, models.ClassEvent.start_time)
        .all()
    )


@router.post("/events", response_model=schemas.ClassEventOut, status_code=201)
def create_event(
    payload: schemas.ClassEventCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    require_feature(db, "agenda_enabled", "La agenda está desactivada en este sitio.")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="La hora de fin debe ser posterior a la de inicio.")

    event = models.ClassEvent(
        user_id=user.id,
        day_of_week=payload.day_of_week,
        title=payload.title,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/events/{event_id}")
def delete_event(
    event_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    event = (
        db.query(models.ClassEvent)
        .filter(models.ClassEvent.id == event_id, models.ClassEvent.user_id == user.id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado.")
    db.delete(event)
    db.commit()
    return {"detail": "Evento eliminado."}
