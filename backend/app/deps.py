import datetime
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from . import models, security
from .database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado."
        )

    payload = security.decode_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada.",
        )

    user = db.get(models.User, payload["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado."
        )
    # Sesión anterior a un cambio de contraseña → ya no vale (p. ej., una sesión robada)
    if user.password_changed_at is not None:
        changed = int(user.password_changed_at.replace(tzinfo=datetime.timezone.utc).timestamp())
        if int(payload.get("iat", 0)) < changed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tu contraseña cambió. Vuelve a iniciar sesión.",
            )

    return user


def get_current_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere permisos de administrador.",
        )
    return current_user
