from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


def normalize_database_url(url: str) -> str:
    """Acepta la cadena tal como la copia Supabase ("postgresql://..." o
    "postgres://...") y la convierte al driver psycopg 3 que usa el proyecto."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = normalize_database_url(settings.DATABASE_URL)
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
elif DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,      # descarta conexiones que el pooler de Supabase ya cerró
        pool_recycle=300,
        pool_size=5,
        max_overflow=5,
        # Sin "prepared statements": el pooler en modo transacción de Supabase
        # (puerto 6543) no los admite. Con el pooler de sesión (5432) no afecta.
        connect_args={"prepare_threshold": None},
    )
else:  # MySQL u otros
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ping_database() -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def lock_public_api_access():
    """En PostgreSQL (Supabase): activa la seguridad a nivel de filas (RLS) en todas las
    tablas del esquema public, sin políticas. Así la API REST automática de Supabase
    (PostgREST, con la clave pública "anon") no puede leer ni modificar nada.

    El backend no se ve afectado: se conecta como el dueño de las tablas, que no está
    sujeto a RLS. Es idempotente: se ejecuta en cada arranque y cubre tablas nuevas."""
    if not DATABASE_URL.startswith("postgresql"):
        return 0
    import logging
    try:
        with engine.begin() as conn:
            tables = [r[0] for r in conn.execute(text(
                "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT c.relrowsecurity"))]
            for t in tables:
                conn.execute(text(f'ALTER TABLE public."{t}" ENABLE ROW LEVEL SECURITY'))
        return len(tables)
    except Exception as e:  # p. ej., el usuario no es dueño de alguna tabla
        logging.getLogger("database").warning("No se pudo activar RLS automáticamente: %s", e)
        return 0


# Índices que faltaban en las claves foráneas (el «Performance Advisor» de Supabase los señaló)
FK_INDEXES = [
    ("ix_chat_messages_session_id", "chat_messages", "session_id"),
    ("ix_chat_sessions_user_id", "chat_sessions", "user_id"),
    ("ix_class_events_user_id", "class_events", "user_id"),
    ("ix_message_files_file_id", "message_files", "file_id"),
    ("ix_page_views_user_id", "page_views", "user_id"),
    ("ix_uploaded_files_session_id", "uploaded_files", "session_id"),
    ("ix_uploaded_files_user_id", "uploaded_files", "user_id"),
]


def upgrade_schema():
    """Cambios de esquema seguros e idempotentes sobre bases existentes (create_all solo crea
    tablas nuevas, no columnas ni índices en tablas que ya existen)."""
    from sqlalchemy import inspect

    insp = inspect(engine)
    with engine.begin() as conn:
        if "users" in insp.get_table_names():
            cols = {c["name"] for c in insp.get_columns("users")}
            if "password_changed_at" not in cols:
                tipo = "TIMESTAMP" if not IS_SQLITE else "DATETIME"
                conn.execute(text(f"ALTER TABLE users ADD COLUMN password_changed_at {tipo}"))
        for name, table, col in FK_INDEXES:
            if table in insp.get_table_names():
                conn.execute(text(f'CREATE INDEX IF NOT EXISTS {name} ON "{table}" ({col})'))
