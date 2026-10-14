import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_admin, get_db
from ..site_settings import get_site_settings
from ..storage import storage
from ..password_reset import create_reset_token

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=schemas.AdminStats)
def get_stats(db: Session = Depends(get_db), _admin: models.User = Depends(get_current_admin)):
    week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)

    total_users = db.query(func.count(models.User.id)).scalar() or 0
    total_sessions = db.query(func.count(models.ChatSession.id)).scalar() or 0
    total_messages = db.query(func.count(models.ChatMessage.id)).scalar() or 0
    total_files = db.query(func.count(models.UploadedFile.id)).scalar() or 0
    new_users_7d = (
        db.query(func.count(models.User.id)).filter(models.User.created_at >= week_ago).scalar() or 0
    )
    pageviews_7d = (
        db.query(func.count(models.PageView.id)).filter(models.PageView.created_at >= week_ago).scalar() or 0
    )

    # Vistas por día (últimos 7 días), calculado en Python para que funcione
    # igual en SQLite y en MySQL sin usar funciones de fecha específicas de un motor.
    raw_views = (
        db.query(models.PageView.created_at)
        .filter(models.PageView.created_at >= week_ago)
        .all()
    )
    by_day: dict[str, int] = {}
    for i in range(7):
        day = (datetime.datetime.utcnow() - datetime.timedelta(days=6 - i)).strftime("%Y-%m-%d")
        by_day[day] = 0
    for (created_at,) in raw_views:
        key = created_at.strftime("%Y-%m-%d")
        if key in by_day:
            by_day[key] += 1
    pageviews_by_day = [{"date": d, "views": c} for d, c in by_day.items()]

    top_paths_raw = (
        db.query(models.PageView.path, func.count(models.PageView.id).label("n"))
        .group_by(models.PageView.path)
        .order_by(func.count(models.PageView.id).desc())
        .limit(8)
        .all()
    )
    top_paths = [{"path": p, "views": n} for p, n in top_paths_raw]

    return schemas.AdminStats(
        total_users=total_users,
        total_sessions=total_sessions,
        total_messages=total_messages,
        total_files=total_files,
        new_users_7d=new_users_7d,
        pageviews_7d=pageviews_7d,
        pageviews_by_day=pageviews_by_day,
        top_paths=top_paths,
    )


@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(db: Session = Depends(get_db), _admin: models.User = Depends(get_current_admin)):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    out = []
    for u in users:
        out.append(
            schemas.AdminUserOut(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                is_admin=u.is_admin,
                created_at=u.created_at,
                session_count=len(u.chat_sessions),
                file_count=len(u.files),
            )
        )
    return out


@router.put("/users/{user_id}/toggle-admin", response_model=schemas.AdminUserOut)
def toggle_admin(
    user_id: int, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes quitarte tus propios permisos de administrador.")
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    user.is_admin = not user.is_admin
    db.commit()
    db.refresh(user)
    return schemas.AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        created_at=user.created_at,
        session_count=len(user.chat_sessions),
        file_count=len(user.files),
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta desde aquí.")
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    # Borrar también los archivos guardados (disco o Supabase Storage): la política
    # de privacidad promete que eliminar la cuenta elimina todos sus datos.
    for f in list(user.files):
        storage.delete(f"{user.id}/{f.stored_name}")
    # Desvincular archivos de conversaciones antes de borrar (clave foránea)
    db.query(models.UploadedFile).filter(models.UploadedFile.user_id == user.id).update(
        {models.UploadedFile.session_id: None}, synchronize_session=False)
    db.flush()
    db.delete(user)
    db.commit()
    return {"detail": "Usuario eliminado."}


@router.get("/settings", response_model=schemas.SiteSettingsOut)
def get_settings(db: Session = Depends(get_db), _admin: models.User = Depends(get_current_admin)):
    return get_site_settings(db)


@router.put("/settings", response_model=schemas.SiteSettingsOut)
def update_settings(
    payload: schemas.SiteSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin),
):
    row = get_site_settings(db)
    changes = payload.model_dump(exclude_unset=True)

    for key, value in changes.items():
        if value is None:
            continue
        if key.startswith("chat_color_"):
            value = value or None  # "" = volver al color por defecto
        if key == "site_name":
            value = value.strip()
            if not value:
                raise HTTPException(status_code=400, detail="El nombre del sitio no puede quedar vacío.")
        setattr(row, key, value)

    any_provider = row.provider_anthropic_enabled or row.provider_openai_enabled or row.provider_gemini_enabled
    if row.chat_enabled and not any_provider:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Deja al menos un proveedor de IA activo, o desactiva el asistente por completo.",
        )

    db.commit()
    db.refresh(row)
    return row



@router.get("/reset-requests", response_model=list[schemas.PasswordResetRequestOut])
def list_reset_requests(db: Session = Depends(get_db), _admin: models.User = Depends(get_current_admin)):
    rows = (
        db.query(models.PasswordResetRequest, models.User)
        .join(models.User, models.User.id == models.PasswordResetRequest.user_id)
        .filter(models.PasswordResetRequest.handled_at.is_(None))
        .order_by(models.PasswordResetRequest.created_at.desc())
        .all()
    )
    return [schemas.PasswordResetRequestOut(id=r.id, user_id=u.id, email=u.email, full_name=u.full_name, created_at=r.created_at)
            for r, u in rows]


@router.post("/users/{user_id}/reset-link", response_model=schemas.PasswordResetLinkOut)
def create_reset_link(user_id: int, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    token, expires = create_reset_token(db, user, admin_id=admin.id)
    # El enlace completo lo arma el navegador con su propia dirección (…/restablecer#token=…)
    return schemas.PasswordResetLinkOut(token=token, email=user.email, expires_at=expires)
