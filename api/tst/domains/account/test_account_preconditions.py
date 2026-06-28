"""Account domain tests aligned with docs/entities/account.md Preconditions.

HTTP routes use the ``client`` fixture (admin, permissions bypassed) or
``role_client`` for self-service (A7/A8). Service rules use ``db_session``.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from src.core.permissions import Role

AUTH_TOKEN_PATH = "/api/v1/auth/token"
ACCOUNTS_PATH = "/api/v1/accounts"
AUTH_ME_PATH = "/api/v1/auth/me"
AUTH_PASSWORD_PATH = "/api/v1/auth/me/password"


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


class TestResolveIntakeAssignee:
    """Auto-assign on lead create — fewest in-process leads among active attorneys."""

    def test_picks_attorney_with_fewest_in_process_leads(self, db_session) -> None:
        import uuid
        from datetime import datetime, timezone

        from src.core.permissions import Role
        from src.domains.account.schemas import AccountCreate
        from src.domains.account.service import AccountService
        from src.domains.lead.models import Lead
        from src.domains.lead.preconditions import LeadState
        from src.domains.prospect.models import Prospect
        from src.domains.resume_file.models import ResumeFile

        busy = AccountService.create_account(
            db_session,
            AccountCreate(
                email="busy@firm.com",
                password="attorney-pass",
                role=Role.ATTORNEY,
                first_name="Busy",
                last_name="Attorney",
                is_default_assignee=True,
            ),
        )
        light = AccountService.create_account(
            db_session,
            AccountCreate(
                email="light@firm.com",
                password="attorney-pass",
                role=Role.ATTORNEY,
                first_name="Light",
                last_name="Attorney",
                is_default_assignee=False,
            ),
        )

        prospect = Prospect(
            id=uuid.uuid4(),
            email="existing@example.com",
            first_name="Existing",
            last_name="Lead",
        )
        db_session.add(prospect)
        resume = ResumeFile(
            storage_key="busy.pdf",
            original_filename="cv.pdf",
            mime_type="application/pdf",
            size_bytes=100,
        )
        db_session.add(resume)
        db_session.flush()
        now = datetime.now(timezone.utc)
        db_session.add(
            Lead(
                prospect_id=prospect.id,
                first_name="Existing",
                last_name="Lead",
                email=prospect.email,
                resume_file_id=resume.id,
                state=LeadState.PENDING.value,
                state_changed_at=now,
                assigned_account_id=busy.id,
                created_at=now,
                updated_at=now,
            )
        )
        db_session.commit()

        assignee = AccountService.resolve_intake_assignee(db_session)

        assert assignee.id == light.id

    def test_fails_with_503_when_no_active_attorney(self, db_session) -> None:
        from fastapi import HTTPException
        from src.domains.account.service import AccountService

        with pytest.raises(HTTPException) as exc_info:
            AccountService.resolve_intake_assignee(db_session)

        assert exc_info.value.status_code == 503
        assert "No active attorney" in exc_info.value.detail


class TestGetAccountFailures:
    """GetAccount (A5) — docs/entities/account.md Preconditions."""

    def test_get_account_404_when_missing(self, client: TestClient) -> None:
        response = client.get(f"{ACCOUNTS_PATH}/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_account_422_malformed_uuid(self, client: TestClient) -> None:
        response = client.get(f"{ACCOUNTS_PATH}/not-a-uuid")
        assert response.status_code == 422


class TestUpdateAccountFailures:
    """UpdateAccount (A6)."""

    def test_update_account_404_when_missing(self, client: TestClient) -> None:
        response = client.patch(
            f"{ACCOUNTS_PATH}/{uuid.uuid4()}",
            json={"first_name": "Ghost"},
        )
        assert response.status_code == 404

    def test_update_account_422_role_immutable(self, client: TestClient) -> None:
        create = _create_account(
            client,
            {
                "email": "immutable-role@firm.com",
                "password": "secure-pass1",
                "role": "readonly",
                "first_name": "Read",
                "last_name": "Only",
            },
        )
        assert create.status_code == 201

        response = client.patch(
            f"{ACCOUNTS_PATH}/{create.json()['id']}",
            json={"role": "admin"},
        )
        assert response.status_code == 422


class TestCreateAccountValidationFailures:
    def test_create_account_422_short_password(self, client: TestClient) -> None:
        response = _create_account(
            client,
            {
                "email": "short-pass@firm.com",
                "password": "short",
                "role": "readonly",
                "first_name": "Short",
                "last_name": "Pass",
            },
        )
        assert response.status_code == 422


class TestListAccountsFailures:
    def test_list_accounts_422_invalid_page_size(self, client: TestClient) -> None:
        response = client.get(f"{ACCOUNTS_PATH}?page_size=0")
        assert response.status_code == 422


class TestChangeOwnEmailFailures:
    """ChangeOwnEmail (A7)."""

    def test_change_own_email_401_wrong_password(self, role_client) -> None:
        client, _ = role_client(
            Role.READONLY,
            email="self@firm.com",
            password="correct-pass1",
        )
        response = client.patch(
            AUTH_ME_PATH,
            json={"email": "new@firm.com", "current_password": "wrong-pass1"},
        )
        assert response.status_code == 401

    def test_change_own_email_409_duplicate(self, client: TestClient, role_client) -> None:
        assert (
            _create_account(
                client,
                {
                    "email": "taken@firm.com",
                    "password": "secure-pass1",
                    "role": "readonly",
                    "first_name": "Taken",
                    "last_name": "Email",
                },
            ).status_code
            == 201
        )

        me_client, _ = role_client(
            Role.READONLY,
            email="owner-self@firm.com",
            password="owner-pass1",
        )
        response = me_client.patch(
            AUTH_ME_PATH,
            json={"email": "taken@firm.com", "current_password": "owner-pass1"},
        )
        assert response.status_code == 409


class TestChangeOwnPasswordFailures:
    """ChangeOwnPassword (A8)."""

    def test_change_own_password_401_wrong_password(self, role_client) -> None:
        client, _ = role_client(
            Role.READONLY,
            email="pwd-self@firm.com",
            password="correct-pass1",
        )
        response = client.patch(
            AUTH_PASSWORD_PATH,
            json={
                "current_password": "wrong-pass1",
                "new_password": "new-pass1234",
            },
        )
        assert response.status_code == 401

    def test_change_own_password_422_too_short(self, role_client) -> None:
        client, _ = role_client(
            Role.READONLY,
            email="pwd-short@firm.com",
            password="correct-pass1",
        )
        response = client.patch(
            AUTH_PASSWORD_PATH,
            json={
                "current_password": "correct-pass1",
                "new_password": "short",
            },
        )
        assert response.status_code == 422
