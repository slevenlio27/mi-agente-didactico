import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Valores de ejemplo que han aparecido en este repositorio. Son públicos, así
# que nunca se aceptan como SECRET_KEY aunque alguien los copie tal cual.
_KNOWN_PLACEHOLDERS = {
    "changeme-please-generate-a-random-secret",
    "change-this-to-a-long-random-string",
}
_MIN_SECRET_LENGTH = 32


def _load_secret_key() -> str:
    key = (os.getenv("SECRET_KEY") or "").strip()
    problem = None
    if not key:
        problem = "falta SECRET_KEY"
    elif key in _KNOWN_PLACEHOLDERS or key.lower().startswith(("change", "your-", "tu-")):
        problem = "SECRET_KEY tiene un valor de ejemplo, que es público"
    elif len(key) < _MIN_SECRET_LENGTH:
        problem = f"SECRET_KEY es demasiado corto (mínimo {_MIN_SECRET_LENGTH} caracteres)"

    if problem:
        # Fallar al arrancar es preferible a correr con un secreto adivinable:
        # con él, cualquiera podría forjar sesiones de cualquier usuario,
        # incluidos los administradores.
        sys.exit(
            f"ERROR: {problem} en backend/.env.\n"
            "Genéralo automáticamente con:  python scripts/generate_secrets.py"
        )
    return key


def _load_encryption_key() -> str:
    key = (os.getenv("API_KEYS_ENCRYPTION_KEY") or "").strip()
    try:
        import base64
        if len(base64.urlsafe_b64decode(key.encode())) != 32:
            raise ValueError
    except Exception:
        sys.exit(
            "ERROR: falta API_KEYS_ENCRYPTION_KEY en backend/.env, o no es válida.\n"
            "Genérala automáticamente con:  python scripts/generate_secrets.py"
        )
    return key


class Settings:
    SECRET_KEY = _load_secret_key()
    # Cifra las claves de API propias de los docentes guardadas en la base de datos.
    API_KEYS_ENCRYPTION_KEY = _load_encryption_key()
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))

    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or None
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or None
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or None

    # gemini-1.5-flash fue retirado por Google (respondía 404). Modelo estable vigente:
    # https://ai.google.dev/gemini-api/docs/models — cámbialo aquí sin tocar código.
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    # Segundos de espera a Gemini. Un PDF largo con un modelo que "razona" puede tardar.
    GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "120"))

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or None

    # Supabase Storage (opcional). Si están vacíos, los archivos se guardan en disco local.
    SUPABASE_URL = os.getenv("SUPABASE_URL") or None
    # Clave secreta "sb_secret_…" (Settings > API Keys). Los proyectos nuevos ya no tienen la
    # antigua service_role; si la tuya la tiene, SUPABASE_SERVICE_ROLE_KEY también funciona.
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "uploads")

    # Tope del total de adjuntos enviados a la IA en un mensaje. Gemini admite 20 MB por
    # petición y base64 agrega ~33 %, así que 13 MB de archivos deja margen.
    MAX_ATTACHMENTS_MB = float(os.getenv("MAX_ATTACHMENTS_MB", "13"))

    # Correos separados por coma que se marcan automáticamente como
    # administradores al registrarse o iniciar sesión por primera vez.
    _admin_emails_raw = os.getenv("ADMIN_EMAILS", "")
    ADMIN_EMAILS = {e.strip().lower() for e in _admin_emails_raw.split(",") if e.strip()}


settings = Settings()
