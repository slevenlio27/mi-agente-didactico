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
