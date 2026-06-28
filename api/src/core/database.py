"""SQLAlchemy engine, session factory, declarative Base, and FastAPI dependency.

Spec: docs/entities/API_CATALOG.md (database foundation slice).

The engine is built from `settings.database_url` (see `src/core/config.py`),
which defaults to the docker-compose Postgres URL. Tests that need a real DB
override the URL via environment; tests that only inspect schema work with
the in-process `Base.metadata`.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.config import settings


engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base for all ORM models. Holds shared `MetaData`."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a single SQLAlchemy session per request.

    The session is closed (returning its connection to the pool) once the
    request handler finishes, even on exception.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
