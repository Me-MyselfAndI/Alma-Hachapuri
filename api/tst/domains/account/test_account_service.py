"""Service-layer tests for AuthService, AccountService, SeedService.

Spec: docs/entities/account.md.

Each test owns its own SQLite ``db_session`` (per the conftest fixture). Tests
that need an admin actor use ``AccountService.create_account`` directly rather
than going through HTTP — the HTTP edge is covered by the precondition tests
in ``test_account_preconditions.py``.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.permissions import Role
from src.domains.account.models import Account
from src.domains.account.schemas import AccountCreate, AccountUpdate
from src.domains.account.service import AccountService, AuthService, SeedService


def _make_attorney(
    db: Session,
    *,
    email: str = "attorney@example.com",
    password: str = "attorney-pass",
    is_default_assignee: bool = True,
) -> Account:
    return AccountService.create_account(
        db,
        AccountCreate(
            email=email,
            password=password,
            role=Role.ATTORNEY,
            first_name="Att",
            last_name="Orney",
            is_default_assignee=is_default_assignee,
        ),
    )


def _make_admin(
    db: Session,
    *,
    email: str = "admin@example.com",
    password: str = "admin-pass",
) -> Account:
    return AccountService.create_account(
        db,
        AccountCreate(
            email=email,
            password=password,
            role=Role.ADMIN,
            first_name="Ad",
            last_name="Min",
        ),
    )


class TestAuthLogin:
    def test_login_happy_path_returns_jwt_with_claims(self, db_session: Session) -> None:
        admin = _make_admin(db_session, email="login@firm.com", password="goodpass1")

        account, token = AuthService.login(
            db_session, "login@firm.com", "goodpass1"
        )

        assert account.id == admin.id
        claims = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert claims["sub"] == str(admin.id)
        assert claims["role"] == Role.ADMIN.value
        assert "manage_users" in claims["permissions"]
        assert "exp" in claims

    def test_authenticate_wrong_password_returns_none(
        self, db_session: Session
    ) -> None:
        _make_admin(db_session, email="x@firm.com", password="rightpass")
        assert (
            AuthService.authenticate(db_session, "x@firm.com", "wrongpass") is None
        )

    def test_authenticate_unknown_email_returns_none(
        self, db_session: Session
    ) -> None:
        assert AuthService.authenticate(db_session, "nobody@firm.com", "x") is None

    def test_login_inactive_account_returns_403(self, db_session: Session) -> None:
        admin = _make_admin(db_session, email="inactive@firm.com", password="goodpass1")
        AccountService.update_account(
            db_session, admin.id, AccountUpdate(is_active=False)
        )

        with pytest.raises(HTTPException) as exc:
            AuthService.login(db_session, "inactive@firm.com", "goodpass1")
        assert exc.value.status_code == 403

        # ``authenticate`` itself still returns the account so callers can
        # decide what to do with an inactive match.
        account = AuthService.authenticate(
            db_session, "inactive@firm.com", "goodpass1"
        )
        assert account is not None and account.is_active is False

    def test_login_email_lookup_case_insensitive(self, db_session: Session) -> None:
        _make_admin(db_session, email="Mixed@FIRM.com", password="goodpass1")
        account, _ = AuthService.login(db_session, "mixed@firm.com", "goodpass1")
        assert account.email == "mixed@firm.com"


class TestCreateAccount:
    def test_duplicate_email_raises_409(self, db_session: Session) -> None:
        _make_admin(db_session, email="dup@firm.com")
        with pytest.raises(HTTPException) as exc:
            AccountService.create_account(
                db_session,
                AccountCreate(
                    email="dup@firm.com",
                    password="anotherpass",
                    role=Role.READONLY,
                    first_name="X",
                    last_name="Y",
                ),
            )
        assert exc.value.status_code == 409

    def test_default_assignee_on_non_attorney_raises_422(
        self, db_session: Session
    ) -> None:
        with pytest.raises(HTTPException) as exc:
            AccountService.create_account(
                db_session,
                AccountCreate(
                    email="bad@firm.com",
                    password="anotherpass",
                    role=Role.INTAKE_COORDINATOR,
                    first_name="X",
                    last_name="Y",
                    is_default_assignee=True,
                ),
            )
        assert exc.value.status_code == 422

    def test_default_assignee_on_attorney_clears_others(
        self, db_session: Session
    ) -> None:
        first = _make_attorney(db_session, email="first@firm.com")
        second = _make_attorney(db_session, email="second@firm.com")

        db_session.refresh(first)
        assert first.is_default_assignee is False
        assert second.is_default_assignee is True

    def test_email_is_stored_lowercase(self, db_session: Session) -> None:
        account = AccountService.create_account(
            db_session,
            AccountCreate(
                email="MixedCase@Firm.COM",
                password="anotherpass",
                role=Role.ADMIN,
                first_name="X",
                last_name="Y",
            ),
        )
        assert account.email == "mixedcase@firm.com"


class TestUpdateAccount:
    def test_clear_sole_default_attorney_raises_422(
        self, db_session: Session
    ) -> None:
        attorney = _make_attorney(db_session, email="only@firm.com")

        with pytest.raises(HTTPException) as exc:
            AccountService.update_account(
                db_session,
                attorney.id,
                AccountUpdate(is_default_assignee=False),
            )
        assert exc.value.status_code == 422

    def test_deactivate_sole_default_attorney_raises_422(
        self, db_session: Session
    ) -> None:
        attorney = _make_attorney(db_session, email="only@firm.com")

        with pytest.raises(HTTPException) as exc:
            AccountService.update_account(
                db_session,
                attorney.id,
                AccountUpdate(is_active=False),
            )
        assert exc.value.status_code == 422

    def test_setting_default_on_attorney_clears_others(
        self, db_session: Session
    ) -> None:
        first = _make_attorney(db_session, email="first@firm.com")
        second = _make_attorney(
            db_session,
            email="second@firm.com",
            is_default_assignee=False,
        )

        AccountService.update_account(
            db_session,
            second.id,
            AccountUpdate(is_default_assignee=True),
        )

        db_session.refresh(first)
        db_session.refresh(second)
        assert first.is_default_assignee is False
        assert second.is_default_assignee is True

    def test_rejects_default_assignee_on_non_attorney(
        self, db_session: Session
    ) -> None:
        _make_attorney(db_session, email="anchor@firm.com")  # keep D4 happy
        readonly = AccountService.create_account(
            db_session,
            AccountCreate(
                email="ro@firm.com",
                password="anotherpass",
                role=Role.READONLY,
                first_name="R",
                last_name="O",
            ),
        )

        with pytest.raises(HTTPException) as exc:
            AccountService.update_account(
                db_session,
                readonly.id,
                AccountUpdate(is_default_assignee=True),
            )
        assert exc.value.status_code == 422

    def test_role_field_in_update_rejected_by_schema(self) -> None:
        with pytest.raises(Exception):  # pydantic ValidationError
            AccountUpdate.model_validate({"role": "admin"})

    def test_update_not_found_raises_404(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc:
            AccountService.update_account(
                db_session,
                uuid.uuid4(),
                AccountUpdate(first_name="Nope"),
            )
        assert exc.value.status_code == 404


class TestSelfMutations:
    def test_self_password_change_wrong_current_raises_401(
        self, db_session: Session
    ) -> None:
        admin = _make_admin(db_session, email="self@firm.com", password="current1")
        with pytest.raises(HTTPException) as exc:
            AccountService.update_self_password(
                db_session, admin, "wrong-current", "newpassword1"
            )
        assert exc.value.status_code == 401

    def test_self_password_change_success(self, db_session: Session) -> None:
        admin = _make_admin(db_session, email="self@firm.com", password="current1")
        AccountService.update_self_password(
            db_session, admin, "current1", "newpassword1"
        )

        # New password works; old does not.
        assert (
            AuthService.authenticate(db_session, "self@firm.com", "newpassword1")
            is not None
        )
        assert (
            AuthService.authenticate(db_session, "self@firm.com", "current1")
            is None
        )

    def test_self_email_change_wrong_current_raises_401(
        self, db_session: Session
    ) -> None:
        admin = _make_admin(db_session, email="self@firm.com", password="current1")
        with pytest.raises(HTTPException) as exc:
            AccountService.update_self_email(
                db_session, admin, "new@firm.com", "wrong-current"
            )
        assert exc.value.status_code == 401

    def test_self_email_change_duplicate_raises_409(
        self, db_session: Session
    ) -> None:
        _make_admin(db_session, email="taken@firm.com", password="otherpass")
        admin = _make_admin(db_session, email="self@firm.com", password="current1")

        with pytest.raises(HTTPException) as exc:
            AccountService.update_self_email(
                db_session, admin, "taken@firm.com", "current1"
            )
        assert exc.value.status_code == 409

    def test_self_email_change_success(self, db_session: Session) -> None:
        admin = _make_admin(db_session, email="self@firm.com", password="current1")
        updated = AccountService.update_self_email(
            db_session, admin, "New@Firm.com", "current1"
        )
        assert updated.email == "new@firm.com"


class TestSeedService:
    def test_seed_inserts_four_accounts(self, db_session: Session) -> None:
        results = SeedService.seed_demo_accounts(db_session)

        assert len(results) == 4
        assert all(created for _, _, created in results)

        # Default attorney exists and is the unique default.
        attorney = next(
            r for r in db_session.query(Account).filter_by(role=Role.ATTORNEY.value)
        )
        assert attorney.is_default_assignee is True

    def test_seed_is_idempotent(self, db_session: Session) -> None:
        SeedService.seed_demo_accounts(db_session)
        second_run = SeedService.seed_demo_accounts(db_session)

        assert all(created is False for _, _, created in second_run)
        # No duplicates.
        total = db_session.query(Account).count()
        assert total == 4
