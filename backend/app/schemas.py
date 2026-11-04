import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

# Nombre de modelo de IA: letras, números, puntos, guiones y dos puntos
# solamente. Se usa para construir la URL de la API de Gemini
# (f"...{model}:generateContent"), así que debe quedar imposible inyectar
# "/", "?", "#" u otros caracteres que cambien la ruta o los parámetros de
# esa petición saliente.
_MODEL_PATTERN = r"^[A-Za-z0-9._:-]{1,100}$"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class GoogleAuthRequest(BaseModel):
    # El JWT ("credential") que devuelve el botón de Google Identity Services
    # en el navegador. El backend lo valida contra Google antes de confiar en él.
    credential: str = Field(min_length=1, max_length=4096)


class ApiKeysUpdate(BaseModel):
    # None = no tocar ese campo. "" (cadena vacía) = borrar la clave guardada.
    openai_api_key: Optional[str] = Field(default=None, max_length=512)
    gemini_api_key: Optional[str] = Field(default=None, max_length=512)
    anthropic_api_key: Optional[str] = Field(default=None, max_length=512)


class ApiKeysStatus(BaseModel):
    # Nunca se devuelve el valor real de la clave, solo si está configurada.
    has_openai_key: bool
    has_gemini_key: bool
    has_anthropic_key: bool
    # Si el servidor tiene su propia clave para cada IA (solo sí/no).
    server_has_openai_key: bool = False
    server_has_gemini_key: bool = False
    server_has_anthropic_key: bool = False


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_admin: bool = False
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    # Literal en vez de str: Pydantic rechaza con un 422 cualquier valor que
    # no sea uno de estos tres, antes de que llegue a ai_providers.py.
    provider: Literal["openai", "gemini", "anthropic"] = "gemini"
    model: Optional[str] = Field(default=None, pattern=_MODEL_PATTERN)


class AttachmentOut(BaseModel):
    id: int
    original_name: str
    content_type: str

    class Config:
        from_attributes = True


class FormQuestionOut(BaseModel):
    id: str
    pregunta: str
    tipo: str
    opciones: List[str] = []
    sugerencia: str = ""
    requerida: bool = False


class FormFindingOut(BaseModel):
    etiqueta: str
    detalle: str


class FormOut(BaseModel):
    id: int
    file_name: Optional[str] = None
    tipo_documento: str
    titulo: str
    resumen: str
    hallazgos: List[FormFindingOut] = []
    faltantes: List[str] = []
    preguntas: List[FormQuestionOut] = []
    respuestas: Optional[dict] = None
    enviado: bool = False

    class Config:
        from_attributes = True


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime.datetime
    files: List[AttachmentOut] = []
    form: Optional[FormOut] = None
    # Planificación generada desde el formulario: se puede descargar en Word
    es_plan: bool = False

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    # Tope generoso para un mensaje de chat; evita que un solo mensaje
    # dispare un costo desproporcionado en la API de IA de pago, o un
    # payload excesivo hacia la base de datos.
    content: str = Field(min_length=1, max_length=8000)
    # Archivos ya subidos (de la galería o del botón de adjuntar) que acompañan al mensaje
    file_ids: List[int] = Field(default_factory=list, max_length=5)


class ChatSessionOut(BaseModel):
    id: int
    title: str
    provider: str
    model: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class ChatSessionDetail(ChatSessionOut):
    messages: List[ChatMessageOut] = []


class UploadedFileOut(BaseModel):
    id: int
    original_name: str
    content_type: str
    size_bytes: int
    created_at: datetime.datetime
    session_id: Optional[int] = None

    class Config:
        from_attributes = True


class ClassEventCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    title: str = Field(min_length=1, max_length=120)
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class ClassEventOut(BaseModel):
    id: int
    day_of_week: int
    title: str
    start_time: str
    end_time: str

    class Config:
        from_attributes = True


class PageViewCreate(BaseModel):
    path: str = Field(min_length=1, max_length=255)


class AdminUserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_admin: bool
    created_at: datetime.datetime
    session_count: int = 0
    file_count: int = 0

    class Config:
        from_attributes = True


class AdminStats(BaseModel):
    total_users: int
    total_sessions: int
    total_messages: int
    total_files: int
    new_users_7d: int
    pageviews_7d: int
    pageviews_by_day: List[dict]
    top_paths: List[dict]


# ─── Configuración del sitio ───────────────────────────────────────────
# Los colores se inyectan como variables CSS en el navegador de todos los
# visitantes, así que solo se acepta el formato exacto "#rrggbb": nada de
# nombres, funciones ni texto libre que pudiera colar otra regla CSS.
_HEX_COLOR = r"^#[0-9a-fA-F]{6}$"
_HEX_COLOR_OR_EMPTY = r"^(#[0-9a-fA-F]{6})?$"  # "" = volver al color por defecto


class SiteSettingsOut(BaseModel):
    # Solo se rellena en /api/settings/public (es público por naturaleza: va en la página)
    google_client_id: Optional[str] = None
    site_name: str
    accent_light: str
    accent_dark: str
    chat_color_anthropic: Optional[str] = None
    chat_color_openai: Optional[str] = None
    chat_color_gemini: Optional[str] = None
    materia_colors_enabled: bool
    registration_enabled: bool
    google_login_enabled: bool
    chat_enabled: bool
    uploads_enabled: bool
    agenda_enabled: bool
    own_api_keys_enabled: bool
    provider_anthropic_enabled: bool
    provider_openai_enabled: bool
    provider_gemini_enabled: bool
    analytics_enabled: bool
    cookie_banner_enabled: bool

    class Config:
        from_attributes = True


class SiteSettingsUpdate(BaseModel):
    # Todo opcional: solo se cambia lo que venga en la petición.
    site_name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    accent_light: Optional[str] = Field(default=None, pattern=_HEX_COLOR)
    accent_dark: Optional[str] = Field(default=None, pattern=_HEX_COLOR)
    chat_color_anthropic: Optional[str] = Field(default=None, pattern=_HEX_COLOR_OR_EMPTY)
    chat_color_openai: Optional[str] = Field(default=None, pattern=_HEX_COLOR_OR_EMPTY)
    chat_color_gemini: Optional[str] = Field(default=None, pattern=_HEX_COLOR_OR_EMPTY)
    materia_colors_enabled: Optional[bool] = None
    registration_enabled: Optional[bool] = None
    google_login_enabled: Optional[bool] = None
    chat_enabled: Optional[bool] = None
    uploads_enabled: Optional[bool] = None
    agenda_enabled: Optional[bool] = None
    own_api_keys_enabled: Optional[bool] = None
    provider_anthropic_enabled: Optional[bool] = None
    provider_openai_enabled: Optional[bool] = None
    provider_gemini_enabled: Optional[bool] = None
    analytics_enabled: Optional[bool] = None
    cookie_banner_enabled: Optional[bool] = None



class TeacherProfileIn(BaseModel):
    materia: Optional[str] = Field(default=None, max_length=120)
    nivel: Optional[str] = Field(default=None, max_length=80)
    duracion_clase: Optional[int] = Field(default=None, ge=10, le=600)
    estilo: Optional[str] = Field(default=None, max_length=200)
    indicaciones: Optional[str] = Field(default=None, max_length=1000)


class TeacherProfileOut(TeacherProfileIn):
    class Config:
        from_attributes = True



# ─── Restablecer contraseña ───────────────────────────────────────────
class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetTokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class PasswordResetConfirmIn(PasswordResetTokenIn):
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetValidateOut(BaseModel):
    valid: bool
    email_hint: Optional[str] = None


class PasswordResetLinkOut(BaseModel):
    token: str
    email: EmailStr
    expires_at: datetime.datetime


class PasswordResetRequestOut(BaseModel):
    id: int
    user_id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime.datetime



class AnalyzeFileIn(BaseModel):
    file_id: int


class FormSubmitIn(BaseModel):
    answers: dict = Field(default_factory=dict)
