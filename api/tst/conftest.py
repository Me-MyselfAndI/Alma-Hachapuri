"""Shared pytest fixtures.

Precondition tests run WITHOUT permission enforcement — auth deps are overridden
so tests focus on data/state rules only (see F2.6).

Service-layer tests that need a live SQLAlchemy session use the ``db_session``
fixture (SQLite in-memory). Postgres-specific column types (``UUID``, ``JSONB``)
are compiled to portable equivalents so the same ORM models load cleanly on
SQLite without forking the model layer.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.domains  # noqa: F401  -- side-effect: register every ORM model on Base
from src.core.database import Base
from src.main import app

# Disable the startup seed during tests — the lifespan opens a real DB session
# against ``SessionLocal`` (production engine), which would try to connect to
# Postgres. Tests that need seeded accounts call ``SeedService`` against the
# in-memory SQLite session directly.
import os
os.environ.setdefault("DISABLE_STARTUP_SEED", "true")
from src.core import config as _config
_config.settings.disable_startup_seed = True


@compiles(PgUUID, "sqlite")
def _compile_pg_uuid_sqlite(  # type: ignore[no-untyped-def]
    element, compiler, **kw
):
    """Render ``postgresql.UUID`` as CHAR(36) under the SQLite test dialect.

    SQLAlchemy's PG ``UUID`` type already converts to/from ``uuid.UUID`` at the
    binding layer, so we only need a portable storage type to satisfy DDL.
    """

    return "CHAR(36)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(  # type: ignore[no-untyped-def]
    element, compiler, **kw
):
    """Render ``postgresql.JSONB`` as JSON text under SQLite (read/write as str)."""

    return "JSON"


def _mock_staff_account(**overrides: Any) -> MagicMock:
    account = MagicMock()
    account.id = overrides.get("id", uuid.uuid4())
    account.email = overrides.get("email", "staff@example.com")
    account.role = overrides.get("role", "admin")
    account.is_active = overrides.get("is_active", True)
    account.permissions = overrides.get(
        "permissions",
        [
            "read_leads",
            "write_lead",
            "assign_lead",
            "read_prospect",
            "manage_users",
            "send_email",
            "read_emails",
            "export_leads",
        ],
    )
    return account


@pytest.fixture
def staff_account() -> MagicMock:
    return _mock_staff_account()


@pytest.fixture
def client(
    staff_account: MagicMock, db_session: Session
) -> Generator[TestClient, None, None]:
    """Test client backed by SQLite + permission checks bypassed.

    The conftest overrides ``get_current_account`` to return an admin mock and
    swaps ``get_db`` for the per-test SQLite session so HTTP routes run end
    to end without Postgres. ``require_permission`` is a factory whose inner
    closure depends on ``get_current_account`` — overriding that one dep is
    enough; manage_users etc. all derive from ``account.role`` on the mock.
    """

    def override_current_account() -> MagicMock:
        return staff_account

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    from src.core import database, deps

    app.dependency_overrides[deps.get_current_account] = override_current_account
    app.dependency_overrides[database.get_db] = override_get_db
    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def role_client(db_session: Session) -> Generator:
    """HTTP client with real ``Account`` rows and RBAC enforced.

    Returns a factory ``role_client(role, **create_kwargs) -> (TestClient, Account)``.
    Unlike ``client``, this does not bypass permission checks — it injects a
    real account from SQLite so ``require_permission`` reads the true role.
    """

    from src.core import database, deps
    from src.core.permissions import Role
    from src.domains.account.models import Account
    from src.domains.account.schemas import AccountCreate
    from src.domains.account.service import AccountService

    holders: list[TestClient] = []

    def _make(role: Role, **overrides: Any) -> tuple[TestClient, Account]:
        suffix = uuid.uuid4().hex[:8]
        account = AccountService.create_account(
            db_session,
            AccountCreate(
                email=overrides.pop("email", f"{role.value}-{suffix}@firm.com"),
                password=overrides.pop("password", "test-pass1"),
                role=role,
                first_name=overrides.pop("first_name", "Test"),
                last_name=overrides.pop("last_name", "User"),
                is_default_assignee=overrides.pop("is_default_assignee", False),
                **overrides,
            ),
        )

        def override_current_account() -> Account:
            row = db_session.get(Account, account.id)
            assert row is not None
            return row

        def override_get_db() -> Generator[Session, None, None]:
            yield db_session

        app.dependency_overrides[deps.get_current_account] = override_current_account
        app.dependency_overrides[database.get_db] = override_get_db
        app.dependency_overrides[deps.get_db] = override_get_db

        test_client = TestClient(app)
        holders.append(test_client)
        return test_client, account

    yield _make

    for holder in holders:
        holder.close()
    app.dependency_overrides.clear()


@pytest.fixture
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def sqlite_engine() -> Generator[Engine, None, None]:
    """Fresh in-memory SQLite engine with the full schema loaded.

    One engine per test gives strong isolation without the cost of Postgres.
    The PG ``UUID`` / ``JSONB`` compile hooks above are what make this work
    against the production ORM models unchanged.
    """

    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(sqlite_engine: Engine) -> Generator[Session, None, None]:
    """SQLAlchemy session bound to the per-test SQLite engine."""

    factory = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False, future=True)
    session = factory()
    try:
        yield session
    finally:
        session.close()
