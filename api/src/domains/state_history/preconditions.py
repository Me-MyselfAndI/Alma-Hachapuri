"""Pure precondition rules for lead state history (F2.3 / F2.6).

No permission checks — those live in route deps. Documented in
docs/entities/lead-state-history.md.
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from src.domains.lead.preconditions import LeadState, is_valid_state_transition


class RecordInitialError(str, Enum):
    LEAD_NOT_FOUND = "lead_not_found"
    FROM_STATE_NOT_NULL = "from_state_not_null"
    INVALID_TO_STATE = "invalid_to_state"
    CHANGED_BY_NOT_NULL = "changed_by_not_null"


class RecordStateChangeError(str, Enum):
    LEAD_NOT_FOUND = "lead_not_found"
    INVALID_FROM_STATE = "invalid_from_state"
    INVALID_TO_STATE = "invalid_to_state"
    SAME_STATE = "same_state"
    INVALID_TRANSITION = "invalid_transition"
    CHANGED_BY_REQUIRED = "changed_by_required"


def history_readable_for_lead(*, lead_exists: bool) -> bool:
    """D3 — archived leads remain readable; only missing leads are denied."""
    return lead_exists


def _parse_lead_state(value: str) -> LeadState | None:
    try:
        return LeadState(value)
    except ValueError:
        return None


def check_record_initial(
    *,
    lead_exists: bool,
    from_state: str | None,
    to_state: str,
    changed_by_account_id: UUID | None,
) -> RecordInitialError | None:
    """Preconditions for RecordInitialState (S6 on lead create)."""
    if not lead_exists:
        return RecordInitialError.LEAD_NOT_FOUND
    if from_state is not None:
        return RecordInitialError.FROM_STATE_NOT_NULL
    if _parse_lead_state(to_state) is None:
        return RecordInitialError.INVALID_TO_STATE
    if changed_by_account_id is not None:
        return RecordInitialError.CHANGED_BY_NOT_NULL
    return None


def check_record_state_change(
    *,
    lead_exists: bool,
    from_state: str,
    to_state: str,
    changed_by_account_id: UUID | None,
) -> RecordStateChangeError | None:
    """Preconditions for RecordStateChange (S6 on L4/L10 transition)."""
    if not lead_exists:
        return RecordStateChangeError.LEAD_NOT_FOUND
    parsed_from = _parse_lead_state(from_state)
    if parsed_from is None:
        return RecordStateChangeError.INVALID_FROM_STATE
    parsed_to = _parse_lead_state(to_state)
    if parsed_to is None:
        return RecordStateChangeError.INVALID_TO_STATE
    if from_state == to_state:
        return RecordStateChangeError.SAME_STATE
    if changed_by_account_id is None:
        return RecordStateChangeError.CHANGED_BY_REQUIRED
    if not is_valid_state_transition(parsed_from, parsed_to):
        return RecordStateChangeError.INVALID_TRANSITION
    return None
