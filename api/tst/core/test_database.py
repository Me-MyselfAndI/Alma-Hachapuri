"""Tests for `src.core.database` wiring.

Scope: pure structural checks — no live Postgres required.

* engine URL comes from settings
* `get_db()` yields a session and closes it (try/finally)
* `Base.metadata` registers every expected table once all domain models load
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

import src.domains  # noqa: F401  -- side-effect: register all ORM models
from src.core import database
from src.core.config import settings


EXPECTED_TABLES: frozenset[str] = frozenset(
    {
        "accounts",
        "prospects",
        "leads",
        "resume_files",
        "lead_state_history",
        "email_notifications",
        "lead_intake_pending",
    }
)


def test_engine_uses_settings_url() -> None:
    """The module-level engine must be built from `settings.database_url`.

    SQLAlchemy masks the password in ``str(url)``; render with the password
    visible so the comparison against the raw settings value succeeds.
    """

    assert database.engine.url.render_as_string(hide_password=False) == settings.database_url


def test_get_db_yields_session_and_closes() -> None:
    """`get_db` yields exactly one session and closes it on generator exit."""

    fake_session = MagicMock(spec=Session)
    with patch.object(database, "SessionLocal", return_value=fake_session):
        gen = database.get_db()
        session = next(gen)
        assert session is fake_session
        fake_session.close.assert_not_called()

        with pytest.raises(StopIteration):
            next(gen)
        fake_session.close.assert_called_once()


def test_get_db_closes_on_exception() -> None:
    """If the consumer raises, the session is still closed (try/finally)."""

    fake_session = MagicMock(spec=Session)
    with patch.object(database, "SessionLocal", return_value=fake_session):
        gen = database.get_db()
        next(gen)
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("boom"))
        fake_session.close.assert_called_once()


def test_base_has_all_tables() -> None:
    """`Base.metadata` must include every entity table after domain import."""

    registered = set(database.Base.metadata.tables.keys())
    missing = EXPECTED_TABLES - registered
    assert not missing, f"Missing tables in Base.metadata: {sorted(missing)}"


def test_lead_table_has_expected_columns() -> None:
    """Spot-check key columns from docs/entities/lead.md are wired."""

    lead_columns = database.Base.metadata.tables["leads"].c
    for col in (
        "id",
        "prospect_id",
        "resume_file_id",
        "state",
        "state_changed_at",
        "assigned_account_id",
        "archived_at",
        "custom_fields",
    ):
        assert col in lead_columns, f"leads.{col} missing"


def test_lead_intake_pending_token_hash_unique() -> None:
    """`lead_intake_pending.token_hash` must be unique to prevent replay."""

    table = database.Base.metadata.tables["lead_intake_pending"]
    assert table.c.token_hash.unique is True
