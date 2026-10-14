"""Lógica compartida de los enlaces para restablecer la contraseña."""

import datetime
import hashlib
import secrets

from . import models

TOKEN_HOURS = 24


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_reset_token(db, user: models.User, admin_id=None) -> tuple[str, datetime.datetime]:
    """Genera un enlace nuevo, anula los anteriores sin usar y cierra las solicitudes pendientes."""
    now = datetime.datetime.utcnow()
    for t in db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id, models.PasswordResetToken.used_at.is_(None)
    ):
        t.used_at = now
    for r in db.query(models.PasswordResetRequest).filter(
        models.PasswordResetRequest.user_id == user.id, models.PasswordResetRequest.handled_at.is_(None)
    ):
        r.handled_at = now
    token = secrets.token_urlsafe(32)
    expires = now + datetime.timedelta(hours=TOKEN_HOURS)
    db.add(models.PasswordResetToken(user_id=user.id, token_hash=hash_token(token), expires_at=expires, created_by=admin_id))
    db.commit()
    return token, expires


def find_valid_token(db, token: str):
    row = db.query(models.PasswordResetToken).filter(models.PasswordResetToken.token_hash == hash_token(token)).first()
    if row is None or row.used_at is not None or row.expires_at < datetime.datetime.utcnow():
        return None
    return row


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    # Siempre tres asteriscos: así no se revela el largo del nombre de usuario
    return f"{name[0]}***@{domain}" if name else email
