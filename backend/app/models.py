import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    # Nula para cuentas creadas solo con "Iniciar sesión con Google"
    hashed_password = Column(String(255), nullable=True)
    # Al cambiar la contraseña, las sesiones emitidas antes dejan de valer
    password_changed_at = Column(DateTime, nullable=True)
    google_sub = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Claves de API propias del docente (opcionales). Si están presentes,
    # se usan en vez de la clave compartida del servidor para sus conversaciones.
    openai_api_key = Column(String(512), nullable=True)
    gemini_api_key = Column(String(512), nullable=True)
    anthropic_api_key = Column(String(512), nullable=True)

    chat_sessions = relationship(
        "ChatSession", back_populates="owner", cascade="all, delete-orphan"
    )
    files = relationship(
        "UploadedFile", back_populates="owner", cascade="all, delete-orphan"
    )
    events = relationship(
        "ClassEvent", back_populates="owner", cascade="all, delete-orphan"
    )
    profile = relationship(
        "TeacherProfile", back_populates="owner", uselist=False, cascade="all, delete-orphan"
    )
    reset_tokens = relationship("PasswordResetToken", cascade="all, delete-orphan")
    reset_requests = relationship("PasswordResetRequest", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), default="Nueva conversación")
    provider = Column(String(50), default="openai")  # openai | gemini | anthropic
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    owner = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


# Archivos adjuntos a cada mensaje del docente (tabla nueva: no modifica las existentes)
message_files = Table(
    "message_files",
    Base.metadata,
    Column("message_id", Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), primary_key=True),
    Column("file_id", Integer, ForeignKey("uploaded_files.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    session = relationship("ChatSession", back_populates="messages")
    files = relationship("UploadedFile", secondary=message_files, lazy="selectin")
    form = relationship("MessageForm", uselist=False, lazy="selectin", cascade="all, delete-orphan")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="files")


class ClassEvent(Base):
    __tablename__ = "class_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 0 = lunes ... 6 = domingo
    day_of_week = Column(Integer, nullable=False)
    title = Column(String(120), nullable=False)
    start_time = Column(String(5), nullable=False)  # "HH:MM"
    end_time = Column(String(5), nullable=False)  # "HH:MM"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="events")


class PageView(Base):
    """Visita anónima a una ruta del sitio, para las estadísticas del panel
    de administrador. No guarda IP ni ningún dato personal identificable."""

    __tablename__ = "page_views"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(255), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class SiteSettings(Base):
    """Configuración global del sitio, editable desde el panel de administrador.
    Siempre hay una sola fila (id=1)."""

    __tablename__ = "site_settings"

    id = Column(Integer, primary_key=True)

    # Identidad y colores
    site_name = Column(String(60), nullable=False, default="Mi Agente Didáctico")
    accent_light = Column(String(7), nullable=False, default="#1f8a73")  # "#rrggbb"
    accent_dark = Column(String(7), nullable=False, default="#5fcdb1")
    chat_color_anthropic = Column(String(7), nullable=True)  # None = color por defecto
    chat_color_openai = Column(String(7), nullable=True)
    chat_color_gemini = Column(String(7), nullable=True)
    materia_colors_enabled = Column(Boolean, nullable=False, default=True)

    # Funciones del sitio
    registration_enabled = Column(Boolean, nullable=False, default=True)
    google_login_enabled = Column(Boolean, nullable=False, default=True)
    chat_enabled = Column(Boolean, nullable=False, default=True)
    uploads_enabled = Column(Boolean, nullable=False, default=True)
    agenda_enabled = Column(Boolean, nullable=False, default=True)
    own_api_keys_enabled = Column(Boolean, nullable=False, default=True)
    # Por defecto solo Gemini; Claude y ChatGPT se pueden activar desde el panel de admin.
    provider_anthropic_enabled = Column(Boolean, nullable=False, default=False)
    provider_openai_enabled = Column(Boolean, nullable=False, default=False)
    provider_gemini_enabled = Column(Boolean, nullable=False, default=True)
    analytics_enabled = Column(Boolean, nullable=False, default=True)
    cookie_banner_enabled = Column(Boolean, nullable=False, default=True)

    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )


class TeacherProfile(Base):
    """Perfil del docente: se envía como contexto al asistente en cada conversación."""

    __tablename__ = "teacher_profiles"
    __table_args__ = (UniqueConstraint("user_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    materia = Column(String(120), nullable=True)
    nivel = Column(String(80), nullable=True)
    duracion_clase = Column(Integer, nullable=True)
    estilo = Column(String(200), nullable=True)
    indicaciones = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="profile")


class PasswordResetToken(Base):
    """Enlace de un solo uso para elegir una contraseña nueva. Solo se guarda el
    hash del código: con una copia de la base de datos no se puede usar."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)  # id del administrador que lo generó


class PasswordResetRequest(Base):
    """Solicitud de un docente que olvidó su contraseña; la atiende un administrador."""

    __tablename__ = "password_reset_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    handled_at = Column(DateTime, nullable=True)


class MessageForm(Base):
    """Análisis de un archivo + formulario de planificación, ligado al mensaje de la IA."""

    __tablename__ = "message_forms"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), unique=True, nullable=False)
    file_name = Column(String(255), nullable=True)
    payload = Column(Text, nullable=False)          # análisis validado (JSON)
    answers = Column(Text, nullable=True)           # respuestas del docente (JSON)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Propiedades que lee el esquema de la API (FormOut)
    @property
    def data(self):
        import json
        return json.loads(self.payload)

    @property
    def tipo_documento(self): return self.data["tipo_documento"]
    @property
    def titulo(self): return self.data["titulo"]
    @property
    def resumen(self): return self.data["resumen"]
    @property
    def hallazgos(self): return self.data["hallazgos"]
    @property
    def faltantes(self): return self.data["faltantes"]
    @property
    def preguntas(self): return self.data["preguntas"]

    @property
    def respuestas(self):
        import json
        return json.loads(self.answers) if self.answers else None

    @property
    def enviado(self): return self.submitted_at is not None
