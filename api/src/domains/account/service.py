"""AuthService, AccountService, SeedService.

Spec: docs/entities/account.md (Preconditions + Actions A1–A9).

Three flat namespaces:

* ``AuthService`` — credential check + token mint. Does **not** raise HTTP errors
  directly; the route maps `None` → 401 and inactive → 403 so the same
  ``authenticate()`` is reusable from CLI / scripts.
* ``AccountService`` — admin CRUD plus self-service email / password updates.
  Service-level guards raise ``HTTPException`` with the documented status
  codes (409 on duplicate, 422 on D6 violation, etc.) so the routes stay
  thin glue.
* ``SeedService`` — idempotent first-run seed for demo accounts. Reads
  credentials from settings so dev / staging can pin different passwords.

D6 (``is_default_assignee`` only on attorneys), D7 (lowercased email), and the
D4 guard ("at least one active default attorney always exists") are enforced
here rather than in Pydantic so they share one implementation between create
and update paths.
"""

from __future__ import annotations

import logging
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.permissions import Role, permissions_for_role
from src.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from src.domains.account.models import Account
from src.domains.account.schemas import (
    AccountCreate,
    AccountUpdate,
)
from src.domains.lead.models import Lead
from src.domains.lead.preconditions import LeadState


logger = logging.getLogger(__name__)

# Active pipeline states — used when load-balancing new lead assignment.
_IN_PROCESS_LEAD_STATES = (
    LeadState.PENDING.value,
    LeadState.REACHED_OUT.value,
    LeadState.QUALIFIED.value,
)


def _normalize_email(email: str) -> str:
    """Lowercase + strip per D7. Pure function — no DB access."""

    return email.strip().lower()


class AuthService:
    """Stateless login helpers."""

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Account | None:
        """Return the matching account on credential match, else ``None``.

        Active/inactive status is NOT enforced here — callers decide whether
        an inactive match is a 403 (HTTP) or simply rejected (CLI).
        """

        normalized = _normalize_email(email)
        account = db.scalar(select(Account).where(Account.email == normalized))
        if account is None:
            return None
        if not verify_password(password, account.password_hash):
            return None
        return account

    @staticmethod
    def login(db: Session, email: str, password: str) -> tuple[Account, str]:
        """HTTP-facing login: raises 401/403 directly, returns ``(account, jwt)``.

        Wrong-credentials and unknown-email both 401 with the same message to
        avoid user enumeration; deactivation is the only case we 403 because
        the username/password were correct.
        """

        account = AuthService.authenticate(db, email, password)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not account.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive account",
            )

        token = create_access_token(
            account_id=account.id,
            role=account.role,
            permissions=list(permissions_for_role(account.role)),
        )
        return account, token


def _coerce_role(role: Role | str) -> str:
    return role.value if isinstance(role, Role) else role


def _count_other_active_default_attorneys(
    db: Session, *, exclude_id: UUID | None
) -> int:
    """Active attorneys with ``is_default_assignee=true`` excluding ``exclude_id``.

    Used for the D4 guard: clearing/deactivating the *only* default attorney
    leaves lead create unable to resolve an assignee. We refuse those updates
    unless another qualifying row exists.
    """

    stmt = select(func.count()).select_from(Account).where(
        Account.role == Role.ATTORNEY.value,
        Account.is_default_assignee.is_(True),
        Account.is_active.is_(True),
    )
    if exclude_id is not None:
        stmt = stmt.where(Account.id != exclude_id)
    return int(db.scalar(stmt) or 0)


def _clear_other_default_attorneys(db: Session, *, keep_id: UUID | None) -> None:
    """Flip ``is_default_assignee`` off on every attorney except ``keep_id``.

    Side effect required by spec: at most one ``is_default_assignee=true`` row
    among ``role=attorney`` rows. We do the update in-Python rather than via
    ``UPDATE`` so the changes flow through the ORM (and ``updated_at`` auto-
    bumps via ``onupdate``).
    """

    stmt = select(Account).where(
        Account.role == Role.ATTORNEY.value,
        Account.is_default_assignee.is_(True),
    )
    for other in db.scalars(stmt):
        if keep_id is not None and other.id == keep_id:
            continue
        other.is_default_assignee = False


class AccountService:
    """Admin CRUD + self-service email/password mutations."""

    @staticmethod
    def create_account(db: Session, data: AccountCreate) -> Account:
        role_value = _coerce_role(data.role)

        if data.is_default_assignee and role_value != Role.ATTORNEY.value:
            raise HTTPException(
                status_code=422,
                detail="is_default_assignee is only valid for attorneys (D6)",
            )

        normalized = _normalize_email(data.email)
        existing = db.scalar(select(Account).where(Account.email == normalized))
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        work_email = data.work_email.strip().lower() if data.work_email else None

        account = Account(
            email=normalized,
            password_hash=hash_password(data.password),
            role=role_value,
            first_name=data.first_name,
            last_name=data.last_name,
            work_email=work_email,
            is_default_assignee=data.is_default_assignee,
            is_active=True,
        )
        db.add(account)
        db.flush()

        if data.is_default_assignee:
            _clear_other_default_attorneys(db, keep_id=account.id)

        db.commit()
        db.refresh(account)
        return account

    @staticmethod
    def resolve_intake_assignee(db: Session) -> Account:
        """Pick the active attorney with the fewest in-process leads (F6.1).

        In-process = ``PENDING``, ``REACHED_OUT``, or ``QUALIFIED``, excluding
        archived rows. Ties break on earliest ``Account.created_at``.

        Raises HTTP 503 when no active attorney exists — expected in normal
        operation after seed/admin setup.
        """

        attorneys = list(
            db.scalars(
                select(Account)
                .where(
                    Account.role == Role.ATTORNEY.value,
                    Account.is_active.is_(True),
                )
                .order_by(Account.created_at.asc())
            )
        )
        if not attorneys:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No active attorney available for lead assignment",
            )

        if len(attorneys) == 1:
            return attorneys[0]

        attorney_ids = [a.id for a in attorneys]
        counts_stmt = (
            select(Lead.assigned_account_id, func.count())
            .where(
                Lead.assigned_account_id.in_(attorney_ids),
                Lead.state.in_(_IN_PROCESS_LEAD_STATES),
                Lead.archived_at.is_(None),
            )
            .group_by(Lead.assigned_account_id)
        )
        counts = {row[0]: int(row[1]) for row in db.execute(counts_stmt)}

        return min(attorneys, key=lambda a: (counts.get(a.id, 0), a.created_at))

    @staticmethod
    def resolve_default_assignee(db: Session) -> Account:
        """Return the active attorney with ``is_default_assignee=true`` (admin D4).

        Used by admin guards and legacy checks — **not** for auto-assign on
        intake (see ``resolve_intake_assignee``).
        """

        stmt = select(Account).where(
            Account.role == Role.ATTORNEY.value,
            Account.is_default_assignee.is_(True),
        ).order_by(Account.created_at.asc())
        account = db.scalar(stmt)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "No default assignee configured: an active attorney with "
                    "is_default_assignee=true is required (D4)"
                ),
            )
        if not account.is_active:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Default assignee is inactive: an active attorney with "
                    "is_default_assignee=true is required (D4)"
                ),
            )
        return account

    @staticmethod
    def get_account(db: Session, account_id: UUID) -> Account | None:
        return db.get(Account, account_id)

    @staticmethod
    def list_accounts(
        db: Session,
        *,
        page: int,
        page_size: int,
        role: Role | str | None = None,
    ) -> tuple[list[Account], int]:
        base = select(Account)
        count_q = select(func.count()).select_from(Account)
        if role is not None:
            role_value = _coerce_role(role)
            base = base.where(Account.role == role_value)
            count_q = count_q.where(Account.role == role_value)

        total = int(db.scalar(count_q) or 0)
        stmt = (
            base.order_by(Account.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(db.scalars(stmt))
        return items, total

    @staticmethod
    def update_account(
        db: Session, account_id: UUID, data: AccountUpdate
    ) -> Account:
        account = db.get(Account, account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            )

        # D6 — is_default_assignee=true only on attorneys.
        if (
            data.is_default_assignee is True
            and account.role != Role.ATTORNEY.value
        ):
            raise HTTPException(
                status_code=422,
                detail="is_default_assignee is only valid for attorneys (D6)",
            )

        # D4 guard — cannot leave zero active default attorneys.
        clearing_default = (
            data.is_default_assignee is False
            and account.is_default_assignee
            and account.role == Role.ATTORNEY.value
        )
        deactivating_default = (
            data.is_active is False
            and account.is_active
            and account.is_default_assignee
            and account.role == Role.ATTORNEY.value
        )
        if clearing_default or deactivating_default:
            others = _count_other_active_default_attorneys(
                db, exclude_id=account.id
            )
            if others == 0:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "At least one active attorney with "
                        "is_default_assignee=true must remain (D4)"
                    ),
                )

        if data.password is not None:
            account.password_hash = hash_password(data.password)
        if data.first_name is not None:
            account.first_name = data.first_name
        if data.last_name is not None:
            account.last_name = data.last_name
        if data.work_email is not None:
            account.work_email = data.work_email.strip().lower()
        if data.is_active is not None:
            account.is_active = data.is_active
        if data.is_default_assignee is not None:
            account.is_default_assignee = data.is_default_assignee

        db.flush()

        if data.is_default_assignee is True:
            _clear_other_default_attorneys(db, keep_id=account.id)

        db.commit()
        db.refresh(account)
        return account

    @staticmethod
    def update_self_email(
        db: Session,
        account: Account,
        new_email: str,
        current_password: str,
    ) -> Account:
        if not verify_password(current_password, account.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        normalized = _normalize_email(new_email)
        if normalized != account.email:
            existing = db.scalar(
                select(Account).where(Account.email == normalized)
            )
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email already exists",
                )
        account.email = normalized
        db.commit()
        db.refresh(account)
        return account

    @staticmethod
    def update_self_password(
        db: Session,
        account: Account,
        current_password: str,
        new_password: str,
    ) -> None:
        if not verify_password(current_password, account.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )
        account.password_hash = hash_password(new_password)
        db.commit()


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------

_SEED_BLUEPRINT: tuple[dict, ...] = (
    {
        "email": "admin@example.com",
        "password_setting": "demo_admin_password",
        "default_password": "admin123",
        "role": Role.ADMIN.value,
        "first_name": "Admin",
        "last_name": "User",
        "is_default_assignee": False,
    },
    {
        "email": "attorney@example.com",
        "password_setting": "demo_attorney_password",
        "default_password": "attorney123",
        "role": Role.ATTORNEY.value,
        "first_name": "Default",
        "last_name": "Attorney",
        "is_default_assignee": True,
    },
    {
        "email": "intake@example.com",
        "password_setting": "demo_intake_password",
        "default_password": "intake123",
        "role": Role.INTAKE_COORDINATOR.value,
        "first_name": "Intake",
        "last_name": "Coordinator",
        "is_default_assignee": False,
    },
    {
        "email": "readonly@example.com",
        "password_setting": "demo_readonly_password",
        "default_password": "readonly123",
        "role": Role.READONLY.value,
        "first_name": "Read",
        "last_name": "Only",
        "is_default_assignee": False,
    },
)


def _resolved_password(blueprint: dict) -> str:
    """Pull demo password from settings, falling back to the in-code default."""

    return getattr(
        settings, blueprint["password_setting"], blueprint["default_password"]
    )


class SeedService:
    """Idempotent demo-account seeder. Safe to call on every startup."""

    @staticmethod
    def seed_demo_accounts(
        db: Session, *, log_to: Iterable | None = None
    ) -> list[tuple[str, str, bool]]:
        """Upsert the four demo accounts; return ``(email, password, created)`` tuples.

        ``created=True`` means we inserted the row this call. Passwords are
        only printed/logged for rows we just inserted — re-running the seed
        on a populated DB leaks nothing.
        """

        results: list[tuple[str, str, bool]] = []
        any_created = False

        for blueprint in _SEED_BLUEPRINT:
            email = _normalize_email(blueprint["email"])
            password = _resolved_password(blueprint)
            existing = db.scalar(select(Account).where(Account.email == email))
            if existing is not None:
                results.append((email, password, False))
                continue

            account = Account(
                email=email,
                password_hash=hash_password(password),
                role=blueprint["role"],
                first_name=blueprint["first_name"],
                last_name=blueprint["last_name"],
                is_default_assignee=blueprint["is_default_assignee"],
                is_active=True,
            )
            db.add(account)
            results.append((email, password, True))
            any_created = True

        if any_created:
            db.commit()
            # Print + log so both `docker-compose up` and structured logs surface it.
            banner = ["", "=" * 60, "Seeded demo accounts (first run):", "-" * 60]
            for email, password, created in results:
                if created:
                    banner.append(f"  {email:<28} {password}")
            banner.append("=" * 60)
            message = "\n".join(banner)
            print(message)
            logger.info(message)
        else:
            db.rollback()

        return results
