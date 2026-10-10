"""Almacenamiento de los archivos que suben los docentes.

- Sin configuración: disco local (carpeta UPLOAD_DIR), útil para desarrollo.
- Con SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY: Supabase Storage, en un bucket
  PRIVADO. Los archivos nunca se exponen con una URL pública: el backend los
  descarga y se los entrega solo a su dueño, después de verificar la sesión.

Se usa la API REST de Supabase Storage directamente (con requests), sin
agregar otra dependencia.
"""

import os
from urllib.parse import quote

import requests

from .config import settings


class StorageError(Exception):
    """El almacenamiento no respondió como se esperaba."""


class LocalStorage:
    name = "local"

    def _path(self, key: str) -> str:
        # La clave siempre es "<user_id>/<nombre aleatorio>"; se valida igual
        # para que nunca pueda salir de la carpeta de subidas.
        user_part, _, file_part = key.partition("/")
        if not user_part.isdigit() or not file_part or "/" in file_part or ".." in file_part:
            raise StorageError("Ruta de archivo inválida.")
        return os.path.join(settings.UPLOAD_DIR, user_part, file_part)

    def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def read(self, key: str):
        path = self._path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def check(self):
        return True, "disco local"

    def delete(self, key: str) -> None:
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)


class SupabaseStorage:
    name = "supabase"

    def __init__(self, url: str, service_key: str, bucket: str):
        self.base = url.rstrip("/") + "/storage/v1"
        self.bucket = bucket
        # La clave secreta da acceso total: solo vive en el servidor. Las claves nuevas
        # (sb_secret_…) no son JWT; Supabase acepta que vayan también en Authorization
        # solo si el valor es idéntico al de apikey, igual que hace su librería oficial.
        self.headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}

    def _object_url(self, key: str, authenticated: bool = False) -> str:
        middle = "object/authenticated" if authenticated else "object"
        return f"{self.base}/{middle}/{quote(self.bucket)}/{quote(key)}"

    def save(self, key: str, data: bytes, content_type: str) -> None:
        try:
            r = requests.post(self._object_url(key), data=data, timeout=60,
                              headers={**self.headers, "Content-Type": content_type, "x-upsert": "false"})
        except requests.exceptions.RequestException as e:
            raise StorageError(f"No se pudo conectar con Supabase Storage: {type(e).__name__}")
        if r.status_code not in (200, 201):
            raise StorageError(f"Supabase Storage rechazó la subida ({r.status_code}). ¿Existe el bucket '{self.bucket}'?")

    def read(self, key: str):
        try:
            r = requests.get(self._object_url(key, authenticated=True), headers=self.headers, timeout=60)
        except requests.exceptions.RequestException as e:
            raise StorageError(f"No se pudo conectar con Supabase Storage: {type(e).__name__}")
        if r.status_code == 200:
            return r.content
        if r.status_code in (400, 404):
            return None
        raise StorageError(f"Supabase Storage respondió {r.status_code} al leer un archivo.")

    def check(self):
        """Comprueba la clave y que el bucket exista. Devuelve (ok, detalle)."""
        try:
            r = requests.get(f"{self.base}/bucket/{quote(self.bucket)}", headers=self.headers, timeout=15)
        except requests.exceptions.RequestException as e:
            return False, f"sin conexión con Supabase ({type(e).__name__})"
        if r.status_code == 200:
            return True, f"bucket '{self.bucket}' accesible"
        if r.status_code in (400, 401, 403):
            return False, "Supabase rechazó la clave: revisa SUPABASE_SECRET_KEY"
        if r.status_code == 404:
            return False, f"no existe el bucket '{self.bucket}': créalo en Storage (privado)"
        return False, f"Supabase respondió {r.status_code}"

    def delete(self, key: str) -> None:
        try:
            requests.delete(self._object_url(key), headers=self.headers, timeout=30)
        except requests.exceptions.RequestException:
            pass  # si falla, queda un archivo huérfano en el bucket, no un error para el docente


def get_storage():
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        return SupabaseStorage(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY, settings.SUPABASE_BUCKET)
    return LocalStorage()


storage = get_storage()
