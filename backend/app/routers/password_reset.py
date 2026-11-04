import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..deps import get_db
from ..password_reset import find_valid_token, mask_email
from ..rate_limit import rate_limit

router = APIRouter(prefix="/auth/password-reset", tags=["password-reset"])

GENERIC = ("Si existe una cuenta con ese correo, el administrador recibirá tu solicitud y te "
           "enviará un enlace para elegir una contraseña nueva.")


@router.post("/request")
def request_reset(
    payload: schemas.PasswordResetRequestIn,
    db: Session = Depends(get_db),
    _rl=Depends(rate_limit("reset_request", max_attempts=5, window_seconds=900)),
):
    # La respuesta es siempre la misma, exista o no la cuenta: así no se puede
    # averiguar qué correos están registrados.
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user:
        pending = db.query(models.PasswordResetRequest).filter(
            models.PasswordResetRequest.user_id == user.id, models.PasswordResetRequest.handled_at.is_(None)
        ).first()
        if not pending:
            db.add(models.PasswordResetRequest(user_id=user.id))
            db.commit()
    return {"detail": GENERIC}


@router.post("/validate", response_model=schemas.PasswordResetValidateOut)
def validate(
    payload: schemas.PasswordResetTokenIn,
    db: Session = Depends(get_db),
    _rl=Depends(rate_limit("reset_validate", max_attempts=30, window_seconds=300)),
):
    row = find_valid_token(db, payload.token)
    if not row:
        return schemas.PasswordResetValidateOut(valid=False)
    user = db.get(models.User, row.user_id)
    return schemas.PasswordResetValidateOut(valid=True, email_hint=mask_email(user.email))


@router.post("/confirm")
def confirm(
    payload: schemas.PasswordResetConfirmIn,
    db: Session = Depends(get_db),
    _rl=Depends(rate_limit("reset_confirm", max_attempts=10, window_seconds=300)),
):
    row = find_valid_token(db, payload.token)
    if not row:
        raise HTTPException(status_code=400, detail="El enlace no es válido, ya se usó o venció. Pide uno nuevo al administrador.")
    user = db.get(models.User, row.user_id)
    user.hashed_password = security.hash_password(payload.new_password)
    now = datetime.datetime.utcnow()
    user.password_changed_at = now          # cierra todas las sesiones abiertas
    # Este enlace y cualquier otro pendiente quedan inutilizados
    for t in db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id, models.PasswordResetToken.used_at.is_(None)
    ):
        t.used_at = now
    db.commit()
    return {"detail": "Tu contraseña se actualizó. Ya puedes iniciar sesión con ella."}
