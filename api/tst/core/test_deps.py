"""Tests for `src.core.deps` — `get_current_account` and `require_permission`.

We build an in-test FastAPI app rather than reuse `src.main.app` so the deps
are exercised end-to-end (OAuth2 scheme, DB lookup, permission check) without
coupling to whatever routes happen to be wired in `main.py`.

`get_db` is overridden to return a fake Session whose `.execute(...).scalar_one_or_none()`
yields an in-memory account stand-in. No real Postgres required.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.core import deps
from src.core.database import get_db
from src.core.permissions import ROLE_PERMISSIONS, Role
from src.core.security import create_access_token


class _FakeScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _FakeSession:
    """Minimal Session stub: returns a preset account from any `execute()`."""

    def __init__(self, account: Any) -> None:
        self._account = account

    def execute(self, _stmt: Any) -> _FakeScalarResult:
        return _FakeScalarResult(self._account)

    def close(self) -> None:  # pragma: no cover - generator cleanup
        pass


class _FakeAccount:
    def __init__(self, *, role: str = "attorney", is_active: bool = True) -> None:
        self.id = uuid.uuid4()
        self.role = role
        self.is_active = is_active


def _build_app(account: Any | None) -> FastAPI:
    app = FastAPI()

    @app.get("/me")
    def me(current=Depends(deps.get_current_account)) -> dict[str, str]:
        return {"id": str(current.id), "role": current.role}

    @app.get("/leads")
    def list_leads(current=Depends(deps.require_permission("read_leads"))) -> dict[str, str]:
        return {"ok": "true", "id": str(current.id)}

    @app.get("/admin")
    def admin_only(current=Depends(deps.require_permission("manage_users"))) -> dict[str, str]:
        return {"ok": "true", "id": str(current.id)}

    @app.get("/either")
    def either(
        current=Depends(deps.require_any_permission("manage_users", "read_leads")),
    ) -> dict[str, str]:
        return {"ok": "true", "id": str(current.id)}

    def override_get_db():
        yield _FakeSession(account)

    app.dependency_overrides[get_db] = override_get_db
    return app


def _token_for(account: _FakeAccount) -> str:
    perms = sorted(ROLE_PERMISSIONS[Role(account.role)])
    return create_access_token(account.id, role=account.role, permissions=perms)


def test_missing_token_returns_401() -> None:
    app = _build_app(account=None)
    client = TestClient(app)
    response = client.get("/me")
    assert response.status_code == 401


def test_bad_token_returns_401() -> None:
    app = _build_app(account=None)
    client = TestClient(app)
    response = client.get("/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_unknown_account_returns_401() -> None:
    """Valid signed token whose `sub` doesn't resolve to a row — 401, not 404."""

    app = _build_app(account=None)
    client = TestClient(app)
    token = create_access_token(uuid.uuid4(), role="admin", permissions=[])
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_inactive_account_returns_403() -> None:
    account = _FakeAccount(role="attorney", is_active=False)
    app = _build_app(account=account)
    client = TestClient(app)
    token = _token_for(account)
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive account"


def test_valid_token_returns_account() -> None:
    account = _FakeAccount(role="attorney")
    app = _build_app(account=account)
    client = TestClient(app)
    token = _token_for(account)
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == str(account.id)


def test_stale_token_permissions_rejected() -> None:
    account = _FakeAccount(role="attorney")
    app = _build_app(account=account)
    client = TestClient(app)
    stale = create_access_token(
        account.id,
        role="attorney",
        permissions=sorted(ROLE_PERMISSIONS[Role.ADMIN]),
    )
    response = client.get("/me", headers={"Authorization": f"Bearer {stale}"})
    assert response.status_code == 401


def test_stale_token_role_rejected() -> None:
    account = _FakeAccount(role="attorney")
    app = _build_app(account=account)
    client = TestClient(app)
    stale = create_access_token(
        account.id,
        role="admin",
        permissions=sorted(ROLE_PERMISSIONS[Role.ATTORNEY]),
    )
    response = client.get("/me", headers={"Authorization": f"Bearer {stale}"})
    assert response.status_code == 401


def test_require_permission_grants_when_role_has_key() -> None:
    account = _FakeAccount(role="attorney")
    app = _build_app(account=account)
    client = TestClient(app)
    token = _token_for(account)
    response = client.get("/leads", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_require_permission_403_when_role_lacks_key() -> None:
    account = _FakeAccount(role="attorney")
    app = _build_app(account=account)
    client = TestClient(app)
    token = _token_for(account)
    response = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_require_permission_admin_passes_admin_only_route() -> None:
    account = _FakeAccount(role="admin")
    app = _build_app(account=account)
    client = TestClient(app)
    token = _token_for(account)
    response = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_require_any_permission_passes_when_one_matches() -> None:
    account = _FakeAccount(role="attorney")  # has read_leads, not manage_users
    app = _build_app(account=account)
    client = TestClient(app)
    token = _token_for(account)
    response = client.get("/either", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_require_any_permission_403_when_none_match() -> None:
    account = _FakeAccount(role="readonly")  # has neither manage_users nor write_lead
    app = _build_app(account=account)
    client = TestClient(app)
    token = _token_for(account)

    @app.get("/none")
    def none_match(
        current=Depends(deps.require_any_permission("manage_users", "write_lead")),
    ) -> dict[str, str]:
        return {"id": str(current.id)}

    response = client.get("/none", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["admin", "attorney", "intake_coordinator", "readonly"])
def test_get_current_account_returns_account_for_each_role(role: str) -> None:
    account = _FakeAccount(role=role)
    app = _build_app(account=account)
    client = TestClient(app)
    token = _token_for(account)
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == role
