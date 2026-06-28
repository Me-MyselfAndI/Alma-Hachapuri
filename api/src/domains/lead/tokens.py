"""Verification token helpers for public lead intake (L1a / L1b)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ensure_utc(dt: datetime) -> datetime:
    """Normalize DB-returned naive timestamps to UTC-aware."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
