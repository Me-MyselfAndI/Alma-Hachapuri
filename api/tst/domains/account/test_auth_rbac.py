"""End-to-end RBAC tests with real JWT auth (no get_current_account override).

These catch permission bugs that ``role_client`` misses because it injects the
account directly and skips token validation.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.permissions import ALL_PERMISSIONS, Role, permissions_for_role
from src.domains.account.schemas import AccountCreate
from src.domains.account.service import AccountService
from tst.conftest import auth_headers, issue_token

ATTORNEY_PERMS = sorted(permissions_for_role(Role.ATTORNEY))
ADMIN_PERMS = sorted(permissions_for_role(Role.ADMIN))


def _create_admin(db: Session, *, email: str, password: str = "admin-pass1"):
    return AccountService.create_account(
        db,
        AccountCreate(
            email=email,
            password=password,
            role=Role.ADMIN,
            first_name="Admin",
            last_name="User",
        ),
    )


def _create_attorney(
    db: Session,
    *,
    email: str | None = None,
    password: str = "attorney-pass1",
    **kwargs,
):
    return AccountService.create_account(
        db,
        AccountCreate(
            email=email or f"attorney-{uuid.uuid4().hex[:8]}@firm.com",
            password=password,
            role=Role.ATTORNEY,
            first_name="New",
            last_name="Attorney",
            is_default_assignee=kwargs.pop("is_default_assignee", False),
            **kwargs,
        ),
    )


class TestAuthMePermissions:
    def test_newly_created_attorney_me_has_five_permissions(
        self, jwt_client: TestClient, db_session: Session
    ) -> None:
        attorney = _create_attorney(db_session, password="new-attorney1")
        token = issue_token(jwt_client, attorney.email, "new-attorney1")

        response = jwt_client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert response.status_code == 200
        body = response.json()
        assert body["email"] == attorney.email
        assert body["role"] == Role.ATTORNEY.value
        assert body["permissions"] == ATTORNEY_PERMS
        assert "manage_users" not in body["permissions"]
        assert "assign_lead" not in body["permissions"]

    def test_admin_me_has_all_eight_permissions(
        self, jwt_client: TestClient, db_session: Session
    ) -> None:
        admin = _create_admin(db_session, email="admin-me@firm.com")
        token = issue_token(jwt_client, admin.email, "admin-pass1")

        response = jwt_client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == Role.ADMIN.value
        assert body["permissions"] == ADMIN_PERMS
        assert len(body["permissions"]) == len(ALL_PERMISSIONS)

    def test_diagnostics_agree_for_new_attorney(
        self, jwt_client: TestClient, db_session: Session
    ) -> None:
        attorney = _create_attorney(db_session, password="diag-pass1")
        token = issue_token(jwt_client, attorney.email, "diag-pass1")

        response = jwt_client.get(
            "/api/v1/auth/diagnostics", headers=auth_headers(token)
        )

        assert response.status_code == 200
        body = response.json()
        assert body["db_role"] == Role.ATTORNEY.value
        assert body["permissions_from_db_role"] == ATTORNEY_PERMS
        assert body["me_permissions"] == ATTORNEY_PERMS
        assert body["jwt_permissions"] == ATTORNEY_PERMS
        assert body["jwt_matches_db"] is True
        assert body["me_permissions_match_matrix"] is True


class TestAttorneyDeniedAdminCapabilities:
    @pytest.fixture
    def attorney_token(self, jwt_client: TestClient, db_session: Session) -> str:
        attorney = _create_attorney(db_session, password="deny-pass1")
        return issue_token(jwt_client, attorney.email, "deny-pass1")

    def test_attorney_cannot_list_all_accounts(
        self, jwt_client: TestClient, attorney_token: str
    ) -> None:
        response = jwt_client.get(
            "/api/v1/accounts?page_size=100",
            headers=auth_headers(attorney_token),
        )
        assert response.status_code == 403

    def test_attorney_cannot_list_attorneys_by_role_filter(
        self, jwt_client: TestClient, attorney_token: str
    ) -> None:
        response = jwt_client.get(
            "/api/v1/accounts?role=attorney&page_size=100",
            headers=auth_headers(attorney_token),
        )
        assert response.status_code == 403

    def test_attorney_cannot_list_for_assignment(
        self, jwt_client: TestClient, attorney_token: str
    ) -> None:
        response = jwt_client.get(
            "/api/v1/accounts?for_assignment=true",
            headers=auth_headers(attorney_token),
        )
        assert response.status_code == 403

    def test_attorney_cannot_create_account(
        self, jwt_client: TestClient, attorney_token: str
    ) -> None:
        response = jwt_client.post(
            "/api/v1/accounts",
            headers=auth_headers(attorney_token),
            json={
                "email": "hacker@firm.com",
                "password": "hacker-pass",
                "role": Role.ADMIN.value,
                "first_name": "Hack",
                "last_name": "Er",
            },
        )
        assert response.status_code == 403


class TestAdminCreatesAttorneyThenAttorneyLogin:
    def test_admin_created_attorney_gets_limited_permissions(
        self, jwt_client: TestClient, db_session: Session
    ) -> None:
        admin = _create_admin(db_session, email="creator@firm.com")
        admin_token = issue_token(jwt_client, admin.email, "admin-pass1")

        create = jwt_client.post(
            "/api/v1/accounts",
            headers=auth_headers(admin_token),
            json={
                "email": "created-attorney@firm.com",
                "password": "created-pass1",
                "role": Role.ATTORNEY.value,
                "first_name": "Created",
                "last_name": "Attorney",
            },
        )
        assert create.status_code == 201
        assert create.json()["role"] == Role.ATTORNEY.value

        attorney_token = issue_token(
            jwt_client, "created-attorney@firm.com", "created-pass1"
        )
        me = jwt_client.get("/api/v1/auth/me", headers=auth_headers(attorney_token))

        assert me.status_code == 200
        assert me.json()["permissions"] == ATTORNEY_PERMS


class TestJwtPermissionEnforcement:
    def test_stale_jwt_with_admin_permissions_rejected_for_attorney(
        self, jwt_client: TestClient, db_session: Session
    ) -> None:
        attorney = _create_attorney(db_session, password="stale-pass1")
        stale = jwt.encode(
            {
                "sub": str(attorney.id),
                "role": Role.ATTORNEY.value,
                "permissions": ADMIN_PERMS,
                "exp": 9999999999,
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        response = jwt_client.get("/api/v1/auth/me", headers=auth_headers(stale))

        assert response.status_code == 401

    def test_login_jwt_permissions_match_role_matrix(
        self, jwt_client: TestClient, db_session: Session
    ) -> None:
        attorney = _create_attorney(db_session, password="jwt-pass1")
        token = issue_token(jwt_client, attorney.email, "jwt-pass1")
        claims = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )

        assert claims["role"] == Role.ATTORNEY.value
        assert sorted(claims["permissions"]) == ATTORNEY_PERMS
