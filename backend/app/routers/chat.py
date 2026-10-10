from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..ai_providers import AIProviderError, get_ai_response
from ..deps import get_current_user, get_db
from ..site_settings import require_feature, require_provider
from ..secret_box import decrypt_secret
from ..prompts import build_system_prompt
from ..config import settings
from ..storage import StorageError, storage

router = APIRouter(prefix="/chat", tags=["chat"])


def _history_with_files(messages, user_id):
    """Historial para la IA. La IA no recuerda entre peticiones, así que se reenvían
    los adjuntos de la conversación: primero los más recientes, hasta el tope de
    tamaño; los que no caben se mencionan para que la IA sepa que existen."""
    budget = settings.MAX_ATTACHMENTS_MB * 1024 * 1024
    included = set()
    for m in reversed(messages):
        for f in m.files:
            if f.size_bytes <= budget:
                included.add(f.id)
                budget -= f.size_bytes
    history = []
    for m in messages:
        files, notes = [], []
        for f in m.files:
            data = storage.read(f"{user_id}/{f.stored_name}") if f.id in included else None
            if data is not None:
                files.append({"name": f.original_name, "mime": f.content_type, "data": data})
            else:
                notes.append(f"(El archivo «{f.original_name}» se adjuntó antes en esta conversación pero no se "
                             "reenvió por tamaño; si lo necesitas, pide al docente que lo adjunte de nuevo.)")
        content = "\n".join(notes + [m.content]) if notes else m.content
        history.append({"role": m.role, "content": content, "files": files})
    return history


@router.get("/sessions", response_model=list[schemas.ChatSessionOut])
def list_sessions(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = db.query(models.ChatSession).filter(models.ChatSession.user_id == user.id)
    if q:
        query = query.filter(models.ChatSession.title.ilike(f"%{q}%"))
    return query.order_by(models.ChatSession.updated_at.desc()).all()


@router.post("/sessions", response_model=schemas.ChatSessionOut)
def create_session(
    payload: schemas.ChatSessionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    require_feature(db, "chat_enabled", "El asistente está desactivado en este sitio.")
    require_provider(db, payload.provider)
    session = models.ChatSession(
        user_id=user.id,
        provider=payload.provider,
        model=payload.model,
        title="Nueva conversación",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _get_owned_session(session_id: int, db: Session, user: models.User) -> models.ChatSession:
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return session


@router.get("/sessions/{session_id}", response_model=schemas.ChatSessionDetail)
def get_session(
    session_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    return _get_owned_session(session_id, db, user)


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    session = _get_owned_session(session_id, db, user)
    # Los archivos subidos en esta conversación siguen en la galería del docente:
    # solo se desvinculan. Sin esto, PostgreSQL/MySQL rechazan el borrado (clave foránea).
    db.query(models.UploadedFile).filter(models.UploadedFile.session_id == session.id).update(
        {models.UploadedFile.session_id: None}, synchronize_session=False)
    db.delete(session)
    db.commit()
    return {"detail": "Conversación eliminada."}


@router.post("/sessions/{session_id}/messages", response_model=schemas.ChatMessageOut)
def send_message(
    session_id: int,
    payload: schemas.ChatMessageCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    site = require_feature(db, "chat_enabled", "El asistente está desactivado en este sitio.")
    session = _get_owned_session(session_id, db, user)
    # También se revisa aquí: una conversación creada antes de que el
    # administrador apagara ese proveedor no debe poder seguir usándolo.
    require_provider(db, session.provider)

    # Adjuntos: solo archivos propios; quedan vinculados a esta conversación
    attach = []
    if payload.file_ids:
        ids = list(dict.fromkeys(payload.file_ids))
        attach = (
            db.query(models.UploadedFile)
            .filter(models.UploadedFile.id.in_(ids), models.UploadedFile.user_id == user.id)
            .all()
        )
        if len(attach) != len(ids):
            raise HTTPException(status_code=404, detail="Alguno de los archivos adjuntos no existe.")
        budget = settings.MAX_ATTACHMENTS_MB * 1024 * 1024
        if sum(f.size_bytes for f in attach) > budget:
            raise HTTPException(
                status_code=400,
                detail=f"Los adjuntos de este mensaje superan {settings.MAX_ATTACHMENTS_MB:g} MB en total. Envía menos archivos a la vez.",
            )
        for f in attach:
            if f.session_id is None:
                f.session_id = session.id

    user_msg = models.ChatMessage(session_id=session.id, role="user", content=payload.content)
    user_msg.files.extend(attach)
    db.add(user_msg)

    # La primera pregunta se usa como título automático de la conversación
    if session.title == "Nueva conversación":
        session.title = payload.content[:60]

    db.commit()
    db.refresh(session)

    try:
        history = _history_with_files(session.messages, user.id)
    except StorageError as e:
        raise HTTPException(status_code=502, detail=str(e))
    profile = db.query(models.TeacherProfile).filter(models.TeacherProfile.user_id == user.id).first()
    system_prompt = build_system_prompt(profile)

    user_key_by_provider = {
        "openai": user.openai_api_key,
        "gemini": user.gemini_api_key,
        "anthropic": user.anthropic_api_key,
    }
    # Si el admin desactivó las claves propias, se usa siempre la del servidor.
    own_key = decrypt_secret(user_key_by_provider.get(session.provider)) if site.own_api_keys_enabled else None

    try:
        reply = get_ai_response(session.provider, history, session.model, api_key=own_key, system=system_prompt)
    except AIProviderError as e:
        # Mensaje de error amigable en vez de un fallo silencioso o un 500 genérico
        raise HTTPException(status_code=502, detail=str(e))

    assistant_msg = models.ChatMessage(session_id=session.id, role="assistant", content=reply)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg
