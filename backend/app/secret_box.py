"""Cifrado en reposo de las claves de API propias de cada docente.

Se usa Fernet (AES-128-CBC + HMAC-SHA256, de la librería `cryptography`) con
una llave dedicada, API_KEYS_ENCRYPTION_KEY, distinta del SECRET_KEY de las
sesiones: así se puede rotar una sin perder la otra.

Los valores cifrados se guardan con el prefijo "enc:v1:" para distinguirlos
sin ambigüedad de claves antiguas guardadas en texto plano.
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from .config import settings

PREFIX = "enc:v1:"
log = logging.getLogger("secret_box")
_fernet = Fernet(settings.API_KEYS_ENCRYPTION_KEY.encode())


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return PREFIX + _fernet.encrypt(value.encode()).decode()


def is_encrypted(value: str | None) -> bool:
    return bool(value) and value.startswith(PREFIX)


def decrypt_secret(value: str | None) -> str | None:
    """Devuelve la clave en claro, o None si no hay clave o no se puede descifrar."""
    if not value:
        return None
    if not is_encrypted(value):
        return value  # valor antiguo en texto plano (se migra al arrancar)
    try:
        return _fernet.decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        # La llave de cifrado cambió o el valor está dañado: se trata como si no
        # hubiera clave; el docente verá el aviso para volver a pegarla.
        log.warning("No se pudo descifrar una clave de API guardada (¿cambió API_KEYS_ENCRYPTION_KEY?)")
        return None


KEY_COLUMNS = ("openai_api_key", "gemini_api_key", "anthropic_api_key")


def encrypt_legacy_plaintext_keys(db) -> int:
    """Cifra las claves que quedaron guardadas en texto plano por versiones anteriores."""
    from . import models

    changed = 0
    for user in db.query(models.User).all():
        for col in KEY_COLUMNS:
            val = getattr(user, col)
            if val and not is_encrypted(val):
                setattr(user, col, encrypt_secret(val))
                changed += 1
    if changed:
        db.commit()
    return changed
