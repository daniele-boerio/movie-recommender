"""Fixture condivise: app FastAPI su un SQLite in-memory, senza scheduler né rate limit.

Stessa ricetta del vecchio harness in-process, ma versionata: override di get_db, PRAGMA
foreign_keys per testare le cascate, codice di verifica fisso per i flussi email.
"""

import os

# DEVONO stare prima di importare l'app: config.py e auth.py li leggono all'import.
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, main
from app.database import Base, get_db

# StaticPool + un'unica connessione: tutte le sessioni vedono lo stesso DB in-memory.
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine, "connect")
def _fk_on(dbapi_conn, _rec):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


TestingSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


main.app.dependency_overrides[get_db] = _override_get_db
main.app.state.limiter.enabled = False
# Codice di verifica deterministico per registrazione / reset / cambio email.
auth.generate_code = lambda length=6: "ABCDEF"


@pytest.fixture(autouse=True)
def _schema():
    """Schema pulito per ogni test."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def db():
    s = TestingSession()
    try:
        yield s
    finally:
        s.close()
