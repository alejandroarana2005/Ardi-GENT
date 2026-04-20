"""
Fixtures de pytest compartidas para tests de HAIA.
Usa SQLite en memoria para tests sin necesidad de PostgreSQL.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.models import Base
from tests.fixtures.sample_data import build_minimal_instance, build_sample_instance


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine) -> Session:
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def minimal_instance():
    return build_minimal_instance()


@pytest.fixture
def sample_instance():
    return build_sample_instance()
