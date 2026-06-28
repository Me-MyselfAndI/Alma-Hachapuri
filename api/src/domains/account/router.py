"""FastAPI routers — A1–A9 (auth + accounts).

Spec: docs/entities/account.md.

Split into two routers exported from this module:

* ``auth_router`` — public (A1) and Bearer-self (A2, A7, A8, A9) routes.
* ``accounts_router`` — admin CRUD (A3–A6) gated on ``manage_users``.

Both are mounted from ``src/main.py``. Permissions / token decoding live in
``src/core/deps.py`` — these handlers stay thin, pushing all rules into
``AuthService`` / ``AccountService``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.deps import get_current_account, get_db, oauth2_scheme, require_permission
from src.core.permissions import Role, account_has_permission, permissions_for_role
from src.core.security import decode_access_token
from src.domains.account.models import Account
from src.domains.account.schemas import (
    AccountCreate,
    AccountEmailUpdate,
    AccountMe,
    AccountPasswordUpdate,
    AccountRead,
    AccountUpdate,
    Paginated,
    SessionDiagnostics,
    TokenResponse,
)
from src.domains.account.service import AccountService, AuthService


auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
accounts_router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


def _to_me(account: Account) -> AccountMe:
    return AccountMe(
        id=account.id,
        email=account.email,
        role=account.role,
        first_name=account.first_name,
        last_name=account.last_name,
        work_email=account.work_email,
        is_default_assignee=account.is_default_assignee,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
        permissions=sorted(permissions_for_role(account.role)),
    )


# ---------------------------------------------------------------------------
# Auth (A1, A2, A7, A8, A9)
# ---------------------------------------------------------------------------


@auth_router.post(
    "/token",
    response_model=TokenResponse,
    summary="Login (A1)",
)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    _, token = AuthService.login(db, form.username, form.password)
    return TokenResponse(access_token=token)


@auth_router.get(
    "/me",
    response_model=AccountMe,
    summary="GetCurrentAccount (A2)",
)
def get_me(account: Account = Depends(get_current_account)) -> AccountMe:
    return _to_me(account)


@auth_router.get(
    "/diagnostics",
    response_model=SessionDiagnostics,
    summary="SessionDiagnostics (troubleshoot auth)",
)
def session_diagnostics(
    account: Account = Depends(get_current_account),
    token: str = Depends(oauth2_scheme),
) -> SessionDiagnostics:
    """Side-by-side view of DB role, code matrix, JWT claims, and ``/me`` permissions."""

    payload = decode_access_token(token)
    me = _to_me(account)
    matrix = sorted(permissions_for_role(account.role))
    jwt_role = payload.get("role")
    jwt_permissions = sorted(payload.get("permissions") or [])

    return SessionDiagnostics(
        account_id=account.id,
        email=account.email,
        db_role=account.role,
        permissions_from_db_role=matrix,
        jwt_role=str(jwt_role) if jwt_role is not None else None,
        jwt_permissions=jwt_permissions,
        jwt_matches_db=(jwt_role == account.role and jwt_permissions == matrix),
        me_permissions=me.permissions,
        me_permissions_match_matrix=(me.permissions == matrix),
    )


@auth_router.patch(
    "/me",
    response_model=AccountMe,
    summary="ChangeOwnEmail (A7)",
)
def change_own_email(
    body: AccountEmailUpdate,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> AccountMe:
    updated = AccountService.update_self_email(
        db, account, body.email, body.current_password
    )
    return _to_me(updated)


@auth_router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="ChangeOwnPassword (A8)",
)
def change_own_password(
    body: AccountPasswordUpdate,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> Response:
    AccountService.update_self_password(
        db, account, body.current_password, body.new_password
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@auth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Logout (A9)",
)
def logout() -> Response:
    # Stateless JWT — nothing to revoke server-side in v1. Endpoint exists for
    # API symmetry and so the client gets a 204 it can branch on.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Account admin (A3–A6)
# ---------------------------------------------------------------------------


@accounts_router.post(
    "",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="CreateAccount (A3)",
)
def create_account(
    body: AccountCreate,
    db: Session = Depends(get_db),
    _admin: Any = Depends(require_permission("manage_users")),
) -> AccountRead:
    account = AccountService.create_account(db, body)
    return AccountRead.model_validate(account)


@accounts_router.get(
    "",
    response_model=Paginated[AccountRead],
    summary="ListAccounts (A4)",
)
def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Role | None = Query(None),
    for_assignment: bool = Query(
        False,
        description="When true, list active attorneys for assignment (requires assign_lead).",
    ),
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> Paginated[AccountRead]:
    if for_assignment:
        if not account_has_permission(account, "assign_lead"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        stmt = (
            select(Account)
            .where(
                Account.is_active.is_(True),
                Account.role == Role.ATTORNEY.value,
            )
            .order_by(Account.last_name.asc(), Account.first_name.asc())
        )
        assignable = list(db.scalars(stmt))
        return Paginated[AccountRead](
            items=[AccountRead.model_validate(a) for a in assignable],
            total=len(assignable),
            page=1,
            page_size=max(len(assignable), 1),
        )

    if not account_has_permission(account, "manage_users"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    items, total = AccountService.list_accounts(
        db, page=page, page_size=page_size, role=role
    )
    return Paginated[AccountRead](
        items=[AccountRead.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@accounts_router.get(
    "/{account_id}",
    response_model=AccountRead,
    summary="GetAccount (A5)",
)
def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    _admin: Any = Depends(require_permission("manage_users")),
) -> AccountRead:
    account = AccountService.get_account(db, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    return AccountRead.model_validate(account)


@accounts_router.patch(
    "/{account_id}",
    response_model=AccountRead,
    summary="UpdateAccount (A6)",
)
def update_account(
    account_id: UUID,
    body: AccountUpdate,
    db: Session = Depends(get_db),
    _admin: Any = Depends(require_permission("manage_users")),
) -> AccountRead:
    account = AccountService.update_account(db, account_id, body)
    return AccountRead.model_validate(account)
