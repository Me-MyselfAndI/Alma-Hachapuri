"""Invoke catalog routes against the real app with a given account."""

from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.core.permissions import Role
from src.domains.account.models import Account
from src.domains.lead.preconditions import LeadState
from tst.rbac.catalog import RouteSpec
from tst.rbac.seed import RbacWorld, account_for_role


@contextmanager
def client_as(db_session: Session, account: Account) -> Generator[TestClient, None, None]:
    from src.core import database, deps
    from src.main import app

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_current_account() -> Account:
        row = db_session.get(Account, account.id)
        assert row is not None
        return row

    app.dependency_overrides[deps.get_current_account] = override_current_account
    app.dependency_overrides[database.get_db] = override_get_db
    app.dependency_overrides[deps.get_db] = override_get_db

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()


def path_for(spec: RouteSpec, world: RbacWorld) -> str:
    mapping = {
        "{lead_id}": str(world.lead.id),
        "{prospect_id}": str(world.prospect.id),
        "{email_id}": str(world.failed_email.id),
        "{account_id}": str(world.owner_attorney.id),
    }
    path = spec.path
    for key, value in mapping.items():
        path = path.replace(key, value)
    return path


def body_for(spec: RouteSpec, world: RbacWorld) -> dict[str, Any] | None:
    if spec.route_id == "A3":
        return {
            "email": "new-user@firm.com",
            "password": "new-pass1",
            "role": Role.ATTORNEY.value,
            "first_name": "New",
            "last_name": "User",
        }
    if spec.route_id == "A6":
        return {"first_name": "Updated"}
    if spec.route_id == "L4":
        return {"state": LeadState.REACHED_OUT.value}
    if spec.route_id == "L10":
        return {"to_state": LeadState.REACHED_OUT.value}
    if spec.route_id in ("E2",):
        return {
            "template": "prospect_follow_up",
            "recipient": world.lead.email,
            "subject": "Hello",
            "body": "Follow up message",
        }
    if spec.route_id == "E2_PREVIEW":
        return {"template": "prospect_follow_up"}
    return None


def invoke(
    client: TestClient,
    spec: RouteSpec,
    world: RbacWorld,
    *,
    extra_path: str | None = None,
) -> Any:
    path = extra_path or path_for(spec, world)
    body = body_for(spec, world)

    if spec.route_id in ("E2", "E2_PREVIEW"):
        with patch("src.domains.email.service.EmailService._send_smtp"):
            if spec.method == "GET":
                return client.get(path)
            if spec.method == "POST":
                return client.post(path, json=body)
            if spec.method == "PATCH":
                return client.patch(path, json=body)
            if spec.method == "DELETE":
                return client.delete(path)
    if spec.route_id == "E3":
        with patch("src.domains.email.service.EmailService._send_smtp"):
            return client.post(path)
    if spec.route_id == "L1a":
        return client.post(
            path,
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "public@example.com",
            },
            files={"resume": ("cv.pdf", b"%PDF-1.4", "application/pdf")},
        )
    if spec.route_id == "L1b_GET":
        return client.get(f"{path}?token=invalid-token-for-auth-test")
    if spec.route_id == "L1b_POST":
        return client.post(path, json={"token": "invalid-token-for-auth-test"})
    if spec.route_id == "A1":
        return client.post(
            path,
            data={"username": "rbac-admin@firm.com", "password": "wrong-password"},
        )

    if spec.method == "GET":
        return client.get(path)
    if spec.method == "POST":
        return client.post(path, json=body) if body is not None else client.post(path)
    if spec.method == "PATCH":
        return client.patch(path, json=body) if body is not None else client.patch(path)
    if spec.method == "DELETE":
        return client.delete(path)
    raise ValueError(f"Unsupported method {spec.method} for {spec.route_id}")


def invoke_as(
    db_session: Session,
    account: Account,
    spec: RouteSpec,
    world: RbacWorld,
) -> Any:
    with client_as(db_session, account) as client:
        return invoke(client, spec, world)
