"""
HAIA Agent — Gestión del ciclo de vida de la sesión de base de datos.
Usa SQLAlchemy 2.0 con context manager para garantizar cierre de sesiones.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.models import Base

_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
    **({} if _is_sqlite else {"pool_size": 10, "max_overflow": 20}),
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Crea todas las tablas si no existen (solo para desarrollo/tests)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency para inyectar sesión de BD."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
