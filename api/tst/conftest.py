"""Shared pytest fixtures.

Precondition tests run WITHOUT permission enforcement — auth deps are overridden
so tests focus on data/state rules only (see F2.6).
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


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
def client(staff_account: MagicMock) -> Generator[TestClient, None, None]:
    """Test client with permission checks bypassed."""

    def override_current_account() -> MagicMock:
        return staff_account

    def override_require_permission(_key: str):
        def _dep() -> MagicMock:
            return staff_account

        return _dep

    from app.core import deps

    app.dependency_overrides[deps.get_current_account] = override_current_account
    # require_permission is a factory — override after routes wire it in PKG-6

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def utc_now() -> datetime:
    return datetime.now(timezone.utc)
