import time
import datetime

import bcrypt
import jwt

from .config import settings

# bcrypt tiene un límite real de 72 bytes por contraseña; lo recortamos de
# forma explícita para evitar el error "password cannot be longer than 72
# bytes" en vez de dejar que reviente más adelante.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except ValueError:
        # hash con formato inválido/corrupto: tratarlo como contraseña incorrecta
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    # «iat» (emitido en): permite invalidar las sesiones anteriores a un cambio de contraseña
    to_encode.update({"exp": expire, "iat": int(time.time())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
