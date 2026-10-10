from fastapi import APIRouter, Depends, HTTPException, status, Response
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import settings
from ..deps import get_db, get_current_user
from ..rate_limit import rate_limit
from ..site_settings import get_site_settings, require_feature
from ..ai_providers import validate_gemini_key
from ..secret_box import decrypt_secret, encrypt_secret

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "access_token"


def set_auth_cookie(response: Response, token: str):
    # HttpOnly: JavaScript en el navegador nunca puede leer esta cookie,
    # lo que reduce el riesgo de robo de sesión por XSS.
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def _sync_admin_status(user: models.User, db: Session) -> None:
    """Promueve automáticamente a administrador si el correo está en
    ADMIN_EMAILS (variable de entorno). Nunca degrada a alguien que ya
    tenía is_admin=True por otro medio (ej. un script manual)."""
    should_be_admin = user.email.lower() in settings.ADMIN_EMAILS
    if should_be_admin and not user.is_admin:
        user.is_admin = True
        db.commit()
        db.refresh(user)


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: schemas.UserCreate,
    response: Response,
    db: Session = Depends(get_db),
    _rl=Depends(rate_limit("register", max_attempts=10, window_seconds=300)),
):
    require_feature(db, "registration_enabled", "El registro de cuentas nuevas está desactivado en este sitio.")
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo.")

    user = models.User(
        email=payload.email,
        hashed_password=security.hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _sync_admin_status(user, db)

    token = security.create_access_token({"user_id": user.id})
    set_auth_cookie(response, token)
    return user


@router.post("/login", response_model=schemas.UserOut)
def login(
    payload: schemas.UserLogin,
    response: Response,
    db: Session = Depends(get_db),
    _rl=Depends(rate_limit("login", max_attempts=10, window_seconds=300)),
):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not user.hashed_password or not security.verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")

    _sync_admin_status(user, db)

    token = security.create_access_token({"user_id": user.id})
    set_auth_cookie(response, token)
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"detail": "Sesión cerrada."}


@router.post("/google", response_model=schemas.UserOut)
def google_auth(
    payload: schemas.GoogleAuthRequest,
    response: Response,
    db: Session = Depends(get_db),
    _rl=Depends(rate_limit("google_auth", max_attempts=20, window_seconds=300)),
):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="El inicio de sesión con Google no está configurado en el servidor (falta GOOGLE_CLIENT_ID).",
        )

    try:
        # Verifica la firma, el emisor y la audiencia del token contra los
        # servidores de Google. Si esto falla, el token es inválido o fue
        # emitido para otra aplicación.
        idinfo = google_id_token.verify_oauth2_token(
            payload.credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Token de Google inválido o expirado.")

    google_sub = idinfo["sub"]
    email = idinfo.get("email")
    full_name = idinfo.get("name")

    if not email:
        raise HTTPException(status_code=400, detail="La cuenta de Google no tiene un correo asociado.")
    if idinfo.get("email_verified") is not True:
        # Sin esto, una cuenta de Google con un correo NO verificado igual a
        # otro ajeno podría vincularse a (y tomar) la cuenta local de ese correo.
        raise HTTPException(status_code=403, detail="Google no ha verificado el correo de esa cuenta.")

    site = get_site_settings(db)
    user = db.query(models.User).filter(models.User.google_sub == google_sub).first()
    linked_by_email = None if user else db.query(models.User).filter(models.User.email == email).first()
    existing = user or linked_by_email

    if not site.google_login_enabled:
        # Los administradores conservan el acceso con Google aunque esté
        # apagado para el resto, para que nadie se quede fuera de su propio panel.
        is_admin = existing is not None and (existing.is_admin or email.lower() in settings.ADMIN_EMAILS)
        if not is_admin:
            raise HTTPException(status_code=403, detail="El inicio de sesión con Google está desactivado en este sitio.")

    if not user:
        if linked_by_email:
            # Ya existía una cuenta local con ese correo (verificado por
            # Google): se vincula en vez de crear una duplicada.
            user = linked_by_email
            user.google_sub = google_sub
        else:
            if not site.registration_enabled:
                raise HTTPException(status_code=403, detail="El registro de cuentas nuevas está desactivado en este sitio.")
            user = models.User(email=email, full_name=full_name, google_sub=google_sub)
            db.add(user)
        db.commit()
        db.refresh(user)

    _sync_admin_status(user, db)

    token = security.create_access_token({"user_id": user.id})
    set_auth_cookie(response, token)
    return user


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


def _keys_status(user: models.User) -> schemas.ApiKeysStatus:
    return schemas.ApiKeysStatus(
        has_openai_key=bool(decrypt_secret(user.openai_api_key)),
        has_gemini_key=bool(decrypt_secret(user.gemini_api_key)),
        has_anthropic_key=bool(decrypt_secret(user.anthropic_api_key)),
        server_has_openai_key=bool(settings.OPENAI_API_KEY),
        server_has_gemini_key=bool(settings.GEMINI_API_KEY),
        server_has_anthropic_key=bool(settings.ANTHROPIC_API_KEY),
    )


@router.get("/me/api-keys", response_model=schemas.ApiKeysStatus)
def get_api_keys_status(current_user: models.User = Depends(get_current_user)):
    return _keys_status(current_user)


@router.put("/me/api-keys", response_model=schemas.ApiKeysStatus)
def update_api_keys(
    payload: schemas.ApiKeysUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _rl=Depends(rate_limit("api_keys", max_attempts=20, window_seconds=300)),
):
    # None = no tocar; "" = borrar; cualquier otro valor = guardar esa clave.
    wants_to_save = any([payload.openai_api_key, payload.gemini_api_key, payload.anthropic_api_key])
    if wants_to_save and not get_site_settings(db).own_api_keys_enabled:
        raise HTTPException(status_code=403, detail="Las claves de API propias están desactivadas en este sitio.")

    gemini = (payload.gemini_api_key or "").strip()
    if gemini:
        # Se comprueba con Google antes de guardar, para que un error al copiar se
        # detecte ahora y no a mitad de una conversación.
        if validate_gemini_key(gemini) is False:
            raise HTTPException(
                status_code=400,
                detail="Google rechazó esa clave de Gemini. Revisa que la copiaste completa desde aistudio.google.com/apikey.",
            )

    for field in ("openai_api_key", "gemini_api_key", "anthropic_api_key"):
        value = getattr(payload, field)
        if value is not None:
            # Se guarda siempre cifrada; vacío = quitar la clave.
            setattr(current_user, field, encrypt_secret(value.strip()) if value.strip() else None)
    db.commit()
    db.refresh(current_user)
    return _keys_status(current_user)
