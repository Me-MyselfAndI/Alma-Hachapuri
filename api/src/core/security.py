"""Password hashing and JWT encode/decode helpers.

Spec: docs/entities/account.md (AuthService)

Hashing uses passlib's bcrypt scheme; tokens are HS256-signed JWTs whose
payload is the minimum needed by the frontend and `get_current_account`:
`sub` (account id as string), `role`, `permissions` (sorted for determinism),
and `exp`.

Note: `permissions` in the token are informational for clients. Route guards
call `account_has_permission(account, key)` against the live DB row's role.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext

from src.core.config import settings


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of `plain`."""

    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True iff `plain` matches `hashed`. Never raises on bad hash."""

    try:
        return _pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        return False


def create_access_token(
    account_id: UUID,
    role: str,
    permissions: list[str],
    expires_minutes: int | None = None,
) -> str:
    """Build an HS256 JWT carrying `sub`, `role`, `permissions`, `exp`.

    `permissions` is sorted so identical inputs produce identical tokens,
    which keeps tests deterministic and avoids surprise diffs in audit logs.
    """

    minutes = expires_minutes if expires_minutes is not None else settings.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(account_id),
        "role": role,
        "permissions": sorted(permissions),
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Verify signature + expiry; return claims dict. Raises `JWTError` on failure."""

    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
