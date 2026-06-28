"""FastAPI dependencies: get_db, get_current_account, require_permission.

Spec: docs/entities/permission.md, docs/entities/account.md (Preconditions:
GetCurrentAccount).

Authentication path:
  1. `oauth2_scheme` extracts the Bearer token (FastAPI 401s if missing).
  2. `get_current_account` decodes the JWT, loads the `Account` row, and
     enforces `is_active`.
  3. `require_permission` / `require_any_permission` layer on a 403 check.

All failures map to HTTP errors at this layer — domain services should never
raise auth errors of their own.
"""

from __future__ import annotations

from typing import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.permissions import account_has_permission, permissions_for_role
from src.core.security import decode_access_token
from src.domains.account.models import Account


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_account(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Account:
    """Resolve the requesting account from a Bearer token.

    Returns 401 for any token problem (missing/invalid/expired or unknown
    subject — same message in both cases to avoid user enumeration). Returns
    403 only when we positively identify a deactivated account.
    """

    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    sub = payload.get("sub")
    if not sub:
        raise _CREDENTIALS_EXCEPTION

    try:
        account_id = UUID(str(sub))
    except (ValueError, TypeError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    account = db.execute(select(Account).where(Account.id == account_id)).scalar_one_or_none()
    if account is None:
        raise _CREDENTIALS_EXCEPTION

    if not account.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive account")

    # Reject tokens whose embedded claims drift from the live DB role / matrix.
    # Clients must re-login after role or permission changes (JWT is not revocable in v1).
    jwt_role = payload.get("role")
    if jwt_role != account.role:
        raise _CREDENTIALS_EXCEPTION

    expected_permissions = sorted(permissions_for_role(account.role))
    jwt_permissions = sorted(payload.get("permissions") or [])
    if jwt_permissions != expected_permissions:
        raise _CREDENTIALS_EXCEPTION

    return account


def require_permission(key: str) -> Callable[[Account], Account]:
    """Factory: dependency that 403s unless the current account has `key`."""

    def _dep(account: Account = Depends(get_current_account)) -> Account:
        if not account_has_permission(account, key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return account

    return _dep


def require_any_permission(*keys: str) -> Callable[[Account], Account]:
    """Factory: dependency that 403s unless the account has at least one of `keys`."""

    def _dep(account: Account = Depends(get_current_account)) -> Account:
        if not any(account_has_permission(account, k) for k in keys):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return account

    return _dep
