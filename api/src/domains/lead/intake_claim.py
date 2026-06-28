"""Atomic L1b pending-intake claim — row lock + idempotent verify.

Uses ``SELECT … FOR UPDATE`` so concurrent verify requests for the same token
serialize on the pending row. A completed verify stores ``lead_id`` on the
pending row so retries return the same lead without creating duplicates.

Stale reclaim: if ``used_at`` is set but ``lead_id`` is still null and the
claim is older than ``verification_processing_stale_minutes``, allow one new
attempt (crashed worker / legacy partial state).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import settings
from src.domains.lead.models import Lead, LeadIntakePending
from src.domains.lead.tokens import ensure_utc


class VerifyClaimOutcome(str, Enum):
    """Result of attempting to claim a pending intake row for L1b."""

    CLAIMED = "claimed"
    STALE_RECLAIMED = "stale_reclaimed"
    ALREADY_COMPLETED = "already_completed"
    IN_PROGRESS = "in_progress"
    EXPIRED = "expired"


@dataclass(frozen=True)
class VerifyClaimResult:
    outcome: VerifyClaimOutcome
    pending: LeadIntakePending


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_pending_for_verify(db: Session, *, token_hash: str) -> LeadIntakePending:
    """Load pending row by token hash with a row-level lock."""

    pending = db.scalar(
        select(LeadIntakePending)
        .where(LeadIntakePending.token_hash == token_hash)
        .with_for_update()
    )
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown verification token",
        )
    return pending


def claim_pending_for_verify(
    db: Session,
    *,
    pending: LeadIntakePending,
    now: datetime | None = None,
) -> VerifyClaimResult:
    """Decide whether this L1b request may proceed; set ``used_at`` when claiming."""

    ts = now or _now_utc()
    if ts >= ensure_utc(pending.expires_at):
        return VerifyClaimResult(VerifyClaimOutcome.EXPIRED, pending)

    if pending.lead_id is not None:
        return VerifyClaimResult(VerifyClaimOutcome.ALREADY_COMPLETED, pending)

    stale_before = ts - timedelta(minutes=settings.verification_processing_stale_minutes)

    if pending.used_at is None:
        pending.used_at = ts
        db.flush()
        return VerifyClaimResult(VerifyClaimOutcome.CLAIMED, pending)

    used_at = ensure_utc(pending.used_at)
    if used_at >= stale_before:
        return VerifyClaimResult(VerifyClaimOutcome.IN_PROGRESS, pending)

    pending.used_at = ts
    db.flush()
    return VerifyClaimResult(VerifyClaimOutcome.STALE_RECLAIMED, pending)


def resolve_completed_lead(db: Session, *, pending: LeadIntakePending) -> Lead:
    """Return the lead created from a completed pending intake."""

    if pending.lead_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification token already used",
        )
    lead = db.get(Lead, pending.lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pending intake data invalid: linked lead missing",
        )
    return lead


def raise_for_claim_outcome(result: VerifyClaimResult) -> None:
    """Map non-proceed outcomes to HTTP errors."""

    if result.outcome is VerifyClaimOutcome.EXPIRED:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Verification token expired",
        )
    if result.outcome is VerifyClaimOutcome.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification already in progress",
        )
