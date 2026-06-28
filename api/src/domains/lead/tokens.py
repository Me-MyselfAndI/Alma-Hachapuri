"""Verification token helpers shared by lead intake and email retry."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.core.config import settings
from src.domains.lead.models import LeadIntakePending


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ensure_utc(dt: datetime) -> datetime:
    """Normalize DB-returned naive timestamps to UTC-aware."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def reissue_verification_token(db: Session, pending: LeadIntakePending) -> str:
    """Issue a fresh single-use token for an unused pending intake row.

    Updates ``token_hash`` and extends ``expires_at`` so E3 retry sends a
    working verification link without storing the raw token at send time.
    """

    raw_token = secrets.token_urlsafe(32)
    pending.token_hash = hash_verification_token(raw_token)
    pending.expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.verification_token_ttl_hours
    )
    db.flush()
    return raw_token
