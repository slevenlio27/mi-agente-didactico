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
from ..rate_limit import rate_limit
from .. import planning
from ..plan_docx import build_plan_docx, fecha_hoy, first_heading
from fastapi.responses import Response
from urllib.parse import quote
import re as _re
import datetime
import json

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
    session = _get_owned_session(session_id, db, user)
    _mark_plans(session.messages)
    return session


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

    return _generate_reply(db, session, user, site)


def _own_key(user, site, provider):
    keys = {"openai": user.openai_api_key, "gemini": user.gemini_api_key, "anthropic": user.anthropic_api_key}
    # Si el admin desactivó las claves propias, se usa siempre la del servidor.
    return decrypt_secret(keys.get(provider)) if site.own_api_keys_enabled else None


def _system_prompt(db, user, extra=None):
    profile = db.query(models.TeacherProfile).filter(models.TeacherProfile.user_id == user.id).first()
    base = build_system_prompt(profile)
    return f"{base}\n\n{extra}" if extra else base


def _generate_reply(db, session, user, site, extra_system=None):
    """Pide la respuesta a la IA con todo el historial (y sus adjuntos) y la guarda."""
    db.refresh(session)
    try:
        history = _history_with_files(session.messages, user.id)
    except StorageError as e:
        raise HTTPException(status_code=502, detail=str(e))
    try:
        reply = get_ai_response(session.provider, history, session.model, api_key=_own_key(user, site, session.provider),
                                system=_system_prompt(db, user, extra_system))
    except AIProviderError as e:
        # Mensaje de error amigable en vez de un fallo silencioso o un 500 genérico
        raise HTTPException(status_code=502, detail=str(e))
    assistant_msg = models.ChatMessage(session_id=session.id, role="assistant", content=reply)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


@router.post("/sessions/{session_id}/analyze", response_model=schemas.ChatMessageOut)
def analyze_file(
    session_id: int,
    payload: schemas.AnalyzeFileIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    _rl=Depends(rate_limit("analyze_file", max_attempts=20, window_seconds=600)),
):
    """«Analizar»: la IA lee el archivo y devuelve un análisis con un formulario de planificación."""
    site = require_feature(db, "chat_enabled", "El asistente está desactivado en este sitio.")
    session = _get_owned_session(session_id, db, user)
    require_provider(db, session.provider)
    if session.provider != "gemini":
        raise HTTPException(status_code=400, detail="El análisis de archivos funciona con Gemini. Abre una conversación nueva con Gemini.")
    f = db.query(models.UploadedFile).filter(models.UploadedFile.id == payload.file_id, models.UploadedFile.user_id == user.id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    if f.size_bytes > settings.MAX_ATTACHMENTS_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"El archivo supera {settings.MAX_ATTACHMENTS_MB:g} MB, el máximo que se puede analizar.")
    try:
        data = storage.read(f"{user.id}/{f.stored_name}")
    except StorageError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if data is None:
        raise HTTPException(status_code=404, detail="El archivo ya no existe en el almacenamiento.")

    try:
        raw = get_ai_response(
            "gemini",
            [{"role": "user", "content": planning.ANALYSIS_PROMPT.format(nombre=f.original_name),
              "files": [{"name": f.original_name, "mime": f.content_type, "data": data}]}],
            session.model, api_key=_own_key(user, site, "gemini"), system=_system_prompt(db, user),
            json_schema=planning.ANALYSIS_SCHEMA,
        )
    except AIProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))
    try:
        analysis = planning.sanitize_analysis(json.loads(raw))
    except (ValueError, TypeError):
        raise HTTPException(status_code=502, detail="No se pudo interpretar el análisis de la IA. Vuelve a intentarlo.")

    # Se guarda solo si el análisis salió bien: el mensaje del docente (con el archivo) y la respuesta con el formulario
    if f.session_id is None:
        f.session_id = session.id
    user_msg = models.ChatMessage(session_id=session.id, role="user", content=f"Analizar «{f.original_name}» para planificar")
    user_msg.files.append(f)
    db.add(user_msg)
    if session.title == "Nueva conversación":
        session.title = f"Planificación: {analysis['titulo'] or f.original_name}"[:60]
    msg = models.ChatMessage(session_id=session.id, role="assistant", content=planning.analysis_to_text(analysis, f.original_name))
    msg.form = models.MessageForm(file_name=f.original_name, payload=json.dumps(analysis, ensure_ascii=False))
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.post("/sessions/{session_id}/forms/{form_id}/submit", response_model=schemas.ChatMessageOut)
def submit_planning_form(
    session_id: int,
    form_id: int,
    payload: schemas.FormSubmitIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """El docente envía el formulario: la IA genera el plan de clase o la secuencia didáctica."""
    site = require_feature(db, "chat_enabled", "El asistente está desactivado en este sitio.")
    session = _get_owned_session(session_id, db, user)
    require_provider(db, session.provider)
    form = (db.query(models.MessageForm).join(models.ChatMessage, models.ChatMessage.id == models.MessageForm.message_id)
            .filter(models.MessageForm.id == form_id, models.ChatMessage.session_id == session.id).first())
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado.")
    if form.enviado:
        raise HTTPException(status_code=409, detail="Este formulario ya se envió.")
    try:
        answers = planning.validate_answers(form.preguntas, payload.answers)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    form.answers = json.dumps(answers, ensure_ascii=False)
    form.submitted_at = datetime.datetime.utcnow()
    summary = models.ChatMessage(session_id=session.id, role="user", content=planning.answers_summary(form.preguntas, answers))
    db.add(summary)
    db.commit()
    try:
        reply = _generate_reply(db, session, user, site, extra_system=planning.generation_instructions(answers))
        reply.es_plan = True
        return reply
    except HTTPException:
        # Si la IA falla, el formulario vuelve a quedar disponible y se quita el mensaje de respuestas,
        # para que al reintentar no quede duplicado
        form.submitted_at = None
        form.answers = None
        db.delete(summary)
        db.commit()
        raise


PLAN_PREFIX = "Respuestas del formulario:"


def _mark_plans(messages):
    """Marca como planificación la respuesta de la IA que sigue a las respuestas de un formulario."""
    prev = None
    for m in messages:
        m.es_plan = bool(m.role == "assistant" and prev is not None and prev.role == "user"
                         and prev.content.startswith(PLAN_PREFIX))
        prev = m


@router.get("/sessions/{session_id}/messages/{message_id}/docx")
def download_plan_docx(
    session_id: int, message_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    """Descarga una respuesta de la IA (normalmente la planificación) como Word editable."""
    session = _get_owned_session(session_id, db, user)
    msgs = list(session.messages)
    idx = next((i for i, m in enumerate(msgs) if m.id == message_id), None)
    if idx is None or msgs[idx].role != "assistant":
        raise HTTPException(status_code=404, detail="Respuesta no encontrada.")
    msg = msgs[idx]

    # El formulario más reciente antes de esta respuesta aporta el contexto de la planificación
    # El formulario solo aporta sus datos cuando esta respuesta salió de él (justo después de sus respuestas)
    _mark_plans(msgs)
    form = next((m.form for m in reversed(msgs[:idx]) if m.form is not None and m.form.enviado), None) if msg.es_plan else None
    profile = db.query(models.TeacherProfile).filter(models.TeacherProfile.user_id == user.id).first()
    respuestas = (form.respuestas or {}) if form else {}
    # Con formulario: el tipo de planificación elegido. Sin formulario (respuesta normal del chat):
    # el título de la conversación, que la app genera a partir de la primera pregunta del docente.
    salida = respuestas.get("salida") or first_heading(msg.content) or \
        (session.title if session.title != "Nueva conversación" else "Respuesta del asistente")
    datos = [("Docente", user.full_name or user.email)]
    if profile and profile.materia:
        datos.append(("Materia", profile.materia))
    if profile and profile.nivel:
        datos.append(("Nivel", profile.nivel))
    if form:
        datos.append(("Documento base", form.file_name or form.titulo))
        for q in form.preguntas:
            if q["id"] != "salida" and q["id"] in respuestas:
                v = respuestas[q["id"]]
                datos.append((q["pregunta"], ", ".join(v) if isinstance(v, list) else v))
    datos.append(("Fecha", fecha_hoy()))

    contenido = build_plan_docx(
        msg.content, titulo_doc=salida,
        subtitulo=(form.titulo if form else "") or "", datos=datos,
        titulo_datos="Datos de la planificación" if form else "Datos del documento",
    )
    base = _re.sub(r"[^\w\-]+", "_", f"{salida} {form.titulo if form else ''}", flags=_re.UNICODE).strip("_")[:80] or "respuesta"
    nombre = f"{base}.docx"
    ascii_nombre = nombre.encode("ascii", "ignore").decode() or "planificacion.docx"
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=\"{ascii_nombre}\"; filename*=UTF-8''{quote(nombre)}",
                 "Cache-Control": "no-store"},
    )
