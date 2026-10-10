from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db

router = APIRouter(prefix="/profile", tags=["profile"])


def _clean(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


@router.get("", response_model=schemas.TeacherProfileOut)
def get_profile(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    profile = db.query(models.TeacherProfile).filter(models.TeacherProfile.user_id == user.id).first()
    return profile or schemas.TeacherProfileOut()


@router.put("", response_model=schemas.TeacherProfileOut)
def update_profile(
    payload: schemas.TeacherProfileIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    profile = db.query(models.TeacherProfile).filter(models.TeacherProfile.user_id == user.id).first()
    if profile is None:
        profile = models.TeacherProfile(user_id=user.id)
        db.add(profile)
    for field, value in payload.model_dump().items():
        setattr(profile, field, _clean(value))
    db.commit()
    db.refresh(profile)
    return profile
