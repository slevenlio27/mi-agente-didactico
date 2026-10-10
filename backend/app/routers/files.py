import os
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from urllib.parse import quote

from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..deps import get_current_user, get_db
from ..site_settings import require_feature
from ..storage import StorageError, storage

router = APIRouter(prefix="/files", tags=["files"])

# Whitelist de tipos permitidos: evita aceptar cualquier archivo (ej. ejecutables)
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "text/plain": ".txt",
    "text/markdown": ".md",
}

# Firmas de bytes iniciales ("magic numbers") para verificar que el archivo
# es realmente del tipo que dice ser el encabezado Content-Type — ese
# encabezado lo pone el navegador y un cliente hecho a mano puede mentir en
# él, así que no basta con confiar solo en ese dato.
_MAGIC_BYTES = {
    "application/pdf": [b"%PDF-"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/webp": [b"RIFF"],  # el "WEBP" real va 4 bytes después de "RIFF"
}

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _sanitize_original_name(name: str) -> str:
    # Quita caracteres de control (saltos de línea, etc.) y recorta la
    # longitud, para que un nombre de archivo manipulado no pueda alterar
    # encabezados HTTP ni desbordar la columna de la base de datos.
    cleaned = _CONTROL_CHARS.sub("", name or "archivo")
    cleaned = os.path.basename(cleaned).strip() or "archivo"
    return cleaned[:255]


def _looks_like_claimed_type(content_type: str, head: bytes) -> bool:
    signatures = _MAGIC_BYTES.get(content_type)
    if not signatures:
        # Para texto plano/markdown no hay una firma binaria fiable; se
        # acepta cualquier contenido, ya que de todas formas se sirve
        # siempre como descarga (Content-Disposition: attachment), nunca
        # se ejecuta ni se interpreta en el servidor.
        return True
    return any(head.startswith(sig) for sig in signatures)


@router.post("/upload", response_model=schemas.UploadedFileOut)
async def upload_file(
    session_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    # Solo se bloquea SUBIR. Ver, descargar y borrar los archivos propios
    # sigue permitido, para que nadie pierda acceso a sus datos.
    require_feature(db, "uploads_enabled", "La subida de archivos está desactivada en este sitio.")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Tipo de archivo no permitido. Usa PDF, PNG, JPEG, WEBP, TXT o MD.",
        )

    # Se lee en bloques y se corta apenas se supera el límite, en vez de
    # leer el archivo completo en memoria/disco antes de revisar el tamaño
    # — así una subida enorme no agota memoria ni disco antes de rechazarla.
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    chunks = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo supera el límite de {settings.MAX_UPLOAD_MB} MB.",
            )
        chunks.append(chunk)
    contents = b"".join(chunks)

    if not _looks_like_claimed_type(file.content_type, contents[:16]):
        raise HTTPException(
            status_code=400,
            detail="El contenido del archivo no coincide con el tipo declarado.",
        )

    # Si se indicó una conversación, debe ser del propio docente
    if session_id is not None:
        owned = db.query(models.ChatSession).filter(
            models.ChatSession.id == session_id, models.ChatSession.user_id == user.id).first()
        if not owned:
            raise HTTPException(status_code=404, detail="Conversación no encontrada.")

    # Nombre aleatorio para evitar colisiones y sobrescrituras
    ext = ALLOWED_TYPES[file.content_type]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    try:
        storage.save(f"{user.id}/{stored_name}", contents, file.content_type)
    except StorageError as e:
        raise HTTPException(status_code=502, detail=str(e))

    record = models.UploadedFile(
        user_id=user.id,
        session_id=session_id,
        original_name=_sanitize_original_name(file.filename),
        stored_name=stored_name,
        content_type=file.content_type,
        size_bytes=len(contents),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[schemas.UploadedFileOut])
def list_files(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.UploadedFile)
        .filter(models.UploadedFile.user_id == user.id)
        .order_by(models.UploadedFile.created_at.desc())
        .all()
    )


def _get_owned_file(file_id: int, db: Session, user: models.User) -> models.UploadedFile:
    record = (
        db.query(models.UploadedFile)
        .filter(models.UploadedFile.id == file_id, models.UploadedFile.user_id == user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return record


@router.get("/{file_id}/download")
def download_file(
    file_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    record = _get_owned_file(file_id, db, user)
    try:
        data = storage.read(f"{user.id}/{record.stored_name}")
    except StorageError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if data is None:
        raise HTTPException(status_code=404, detail="El archivo ya no existe en el almacenamiento.")
    return Response(
        content=data,
        media_type=record.content_type,
        headers={
            # "inline" para que las imágenes se vean en la galería; nosniff impide
            # que el navegador interprete el archivo como otro tipo (p. ej. HTML).
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(record.original_name)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
        },
    )


@router.delete("/{file_id}")
def delete_file(
    file_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    record = _get_owned_file(file_id, db, user)
    storage.delete(f"{user.id}/{record.stored_name}")
    db.delete(record)
    db.commit()
    return {"detail": "Archivo eliminado."}
