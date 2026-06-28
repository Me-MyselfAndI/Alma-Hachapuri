"""Account domain precondition tests (F2.6).

Data/state rules only — permission checks are bypassed via the conftest
``client`` fixture (see ``tests/conftest.py``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

AUTH_TOKEN_PATH = "/api/v1/auth/token"
ACCOUNTS_PATH = "/api/v1/accounts"


def _login(client: TestClient, email: str, password: str):
    return client.post(
        AUTH_TOKEN_PATH,
        data={"username": email, "password": password},
    )


def _create_account(client: TestClient, payload: dict):
    return client.post(ACCOUNTS_PATH, json=payload)


class TestLoginValidation:
    """Login (A1) — credential and account-state preconditions."""

    def test_login_rejects_invalid_credentials(self, client: TestClient) -> None:
        """Wrong email or password must return 401 with a generic message."""
        response = _login(client, "nobody@firm.com", "wrong-password")

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_login_rejects_inactive_account(self, client: TestClient) -> None:
        """Account must be active; is_active=false returns 403 even when password matches."""
        # Seed: active account exists; admin deactivates it before login attempt.
        email = "inactive@firm.com"
        password = "valid-password"
        create = _create_account(
            client,
            {
                "email": email,
                "password": password,
                "role": "readonly",
                "first_name": "Inactive",
                "last_name": "User",
            },
        )
        account_id = create.json()["id"]
        client.patch(f"{ACCOUNTS_PATH}/{account_id}", json={"is_active": False})

        response = _login(client, email, password)

        assert response.status_code == 403

    def test_login_rejects_missing_form_fields(self, client: TestClient) -> None:
        """OAuth2 password flow requires username and password form fields."""
        response = client.post(AUTH_TOKEN_PATH, data={})

        assert response.status_code == 422


class TestCreateAccountDuplicateEmail:
    """CreateAccount (A3) — email uniqueness (case-insensitive after D7 normalization)."""

    def test_create_account_rejects_duplicate_email(self, client: TestClient) -> None:
        """Duplicate email must return 409 after first account is created."""
        payload = {
            "email": "duplicate@firm.com",
            "password": "secure-pass",
            "role": "intake_coordinator",
            "first_name": "First",
            "last_name": "User",
        }
        first = _create_account(client, payload)
        assert first.status_code == 201

        second = _create_account(client, payload)

        assert second.status_code == 409

    def test_create_account_normalizes_email_lowercase(self, client: TestClient) -> None:
        """Email is stored lowercase (D7); mixed-case submit conflicts with existing row."""
        _create_account(
            client,
            {
                "email": "admin@firm.com",
                "password": "secure-pass",
                "role": "admin",
                "first_name": "Admin",
                "last_name": "User",
            },
        )

        response = _create_account(
            client,
            {
                "email": "Admin@Firm.com",
                "password": "other-pass",
                "role": "readonly",
                "first_name": "Other",
                "last_name": "User",
            },
        )

        assert response.status_code == 409


class TestDefaultAssigneeOnNonAttorney:
    """CreateAccount / UpdateAccount — is_default_assignee only valid for attorneys (D6)."""

    def test_create_account_rejects_default_assignee_on_admin(
        self, client: TestClient
    ) -> None:
        """is_default_assignee=true on role=admin must return 422."""
        response = _create_account(
            client,
            {
                "email": "admin-default@firm.com",
                "password": "secure-pass",
                "role": "admin",
                "first_name": "Admin",
                "last_name": "User",
                "is_default_assignee": True,
            },
        )

        assert response.status_code == 422

    def test_create_account_rejects_default_assignee_on_intake_coordinator(
        self, client: TestClient
    ) -> None:
        """is_default_assignee=true on role=intake_coordinator must return 422."""
        response = _create_account(
            client,
            {
                "email": "intake-default@firm.com",
                "password": "secure-pass",
                "role": "intake_coordinator",
                "first_name": "Intake",
                "last_name": "User",
                "is_default_assignee": True,
            },
        )

        assert response.status_code == 422

    def test_update_account_rejects_default_assignee_on_non_attorney(
        self, client: TestClient
    ) -> None:
        """UpdateAccount must reject is_default_assignee=true when target role is not attorney."""
        create = _create_account(
            client,
            {
                "email": "readonly-user@firm.com",
                "password": "secure-pass",
                "role": "readonly",
                "first_name": "Read",
                "last_name": "Only",
            },
        )
        account_id = create.json()["id"]

        response = client.patch(
            f"{ACCOUNTS_PATH}/{account_id}",
            json={"is_default_assignee": True},
        )

        assert response.status_code == 422


class TestResolveDefaultAssigneeActiveCheck:
    """ResolveDefaultAssignee (S3) — active attorney with is_default_assignee=true (D4/D5)."""

    def test_resolve_default_assignee_returns_active_attorney(
        self, db_session
    ) -> None:
        from src.core.permissions import Role
        from src.domains.account.schemas import AccountCreate
        from src.domains.account.service import AccountService

        AccountService.create_account(
            db_session,
            AccountCreate(
                email="default@firm.com",
                password="attorney-pass",
                role=Role.ATTORNEY,
                first_name="Default",
                last_name="Attorney",
                is_default_assignee=True,
            ),
        )

        assignee = AccountService.resolve_default_assignee(db_session)

        assert assignee.role == Role.ATTORNEY.value
        assert assignee.is_default_assignee is True
        assert assignee.is_active is True

    def test_resolve_default_assignee_rejects_inactive_default(
        self, db_session
    ) -> None:
        from fastapi import HTTPException
        from src.core.permissions import Role
        from src.domains.account.models import Account
        from src.domains.account.schemas import AccountCreate
        from src.domains.account.service import AccountService

        attorney = AccountService.create_account(
            db_session,
            AccountCreate(
                email="inactive-default@firm.com",
                password="attorney-pass",
                role=Role.ATTORNEY,
                first_name="Inactive",
                last_name="Attorney",
                is_default_assignee=True,
            ),
        )
        row = db_session.get(Account, attorney.id)
        assert row is not None
        row.is_active = False
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            AccountService.resolve_default_assignee(db_session)

        assert exc_info.value.status_code == 500

    def test_resolve_default_assignee_fails_when_none_configured(
        self, db_session
    ) -> None:
        from fastapi import HTTPException
        from src.domains.account.service import AccountService

        with pytest.raises(HTTPException) as exc_info:
            AccountService.resolve_default_assignee(db_session)

        assert exc_info.value.status_code == 500
