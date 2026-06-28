"""Pure precondition rules for the lead domain (F2.3 / F2.6).

No permission checks — those live in route deps. These functions encode
data/state rules documented in docs/entities/lead.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum


class LeadState(str, Enum):
    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"
    QUALIFIED = "QUALIFIED"
    DISQUALIFIED = "DISQUALIFIED"
    CLOSED = "CLOSED"


VALID_TRANSITIONS: dict[LeadState, frozenset[LeadState]] = {
    LeadState.PENDING: frozenset(
        {LeadState.REACHED_OUT, LeadState.QUALIFIED, LeadState.DISQUALIFIED}
    ),
    LeadState.REACHED_OUT: frozenset(
        {LeadState.PENDING, LeadState.QUALIFIED, LeadState.DISQUALIFIED}
    ),
    LeadState.QUALIFIED: frozenset({LeadState.CLOSED}),
    LeadState.DISQUALIFIED: frozenset({LeadState.CLOSED}),
    LeadState.CLOSED: frozenset(),
}


class VerificationTokenError(str, Enum):
    EXPIRED = "expired"
    ALREADY_USED = "already_used"


def normalize_email(email: str) -> str:
    """D7 — lowercase normalized on write."""
    return email.strip().lower()


def is_valid_state_transition(
    from_state: str | LeadState,
    to_state: str | LeadState,
) -> bool:
    """Return True when the transition is allowed by the v1 matrix."""
    src = LeadState(from_state) if isinstance(from_state, str) else from_state
    dst = LeadState(to_state) if isinstance(to_state, str) else to_state
    return dst in VALID_TRANSITIONS.get(src, frozenset())


def check_verification_token(
    *,
    expires_at: datetime,
    used_at: datetime | None,
    now: datetime,
) -> VerificationTokenError | None:
    """Return an error when the token cannot be consumed; None if OK."""
    if used_at is not None:
        return VerificationTokenError.ALREADY_USED
    if now >= expires_at:
        return VerificationTokenError.EXPIRED
    return None


def lead_readable_by_id(*, exists: bool) -> bool:
    """D3 — archived leads remain readable by id; only missing leads are denied."""
    return exists


def lead_visible_in_list(*, archived_at: datetime | None, include_archived: bool) -> bool:
    """ListLeads excludes archived rows unless include_archived=true."""
    if archived_at is None:
        return True
    return include_archived
