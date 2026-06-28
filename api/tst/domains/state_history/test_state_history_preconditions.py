"""Precondition tests for state_history domain (F2.6 — no permission checks)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domains.lead.preconditions import LeadState
from src.domains.state_history.preconditions import (
    RecordInitialError,
    RecordStateChangeError,
    check_record_initial,
    check_record_state_change,
    history_readable_for_lead,
)

UTC = timezone.utc
STAFF_ID = uuid4()


class TestGetLeadStateHistoryPreconditions:
    """D3 — archived leads remain readable by id."""

    def test_allowed_when_lead_exists(self) -> None:
        assert history_readable_for_lead(lead_exists=True) is True

    def test_allowed_when_archived(self) -> None:
        archived_at = datetime(2026, 6, 1, tzinfo=UTC)
        assert history_readable_for_lead(lead_exists=True) is True
        assert archived_at is not None  # archive timestamp does not affect read

    def test_denied_only_when_missing(self) -> None:
        assert history_readable_for_lead(lead_exists=False) is False


class TestRecordInitialState:
    def test_accepts_valid_initial_row(self) -> None:
        assert (
            check_record_initial(
                lead_exists=True,
                from_state=None,
                to_state=LeadState.PENDING.value,
                changed_by_account_id=None,
            )
            is None
        )

    def test_rejects_missing_lead(self) -> None:
        assert (
            check_record_initial(
                lead_exists=False,
                from_state=None,
                to_state=LeadState.PENDING.value,
                changed_by_account_id=None,
            )
            is RecordInitialError.LEAD_NOT_FOUND
        )

    def test_rejects_non_null_from_state(self) -> None:
        assert (
            check_record_initial(
                lead_exists=True,
                from_state=LeadState.PENDING.value,
                to_state=LeadState.PENDING.value,
                changed_by_account_id=None,
            )
            is RecordInitialError.FROM_STATE_NOT_NULL
        )

    def test_rejects_invalid_to_state(self) -> None:
        assert (
            check_record_initial(
                lead_exists=True,
                from_state=None,
                to_state="NOT_A_STATE",
                changed_by_account_id=None,
            )
            is RecordInitialError.INVALID_TO_STATE
        )

    def test_rejects_changed_by_on_system_create(self) -> None:
        assert (
            check_record_initial(
                lead_exists=True,
                from_state=None,
                to_state=LeadState.PENDING.value,
                changed_by_account_id=STAFF_ID,
            )
            is RecordInitialError.CHANGED_BY_NOT_NULL
        )


class TestRecordStateChange:
    @pytest.mark.parametrize(
        ("from_state", "to_state"),
        [
            (LeadState.PENDING, LeadState.REACHED_OUT),
            (LeadState.REACHED_OUT, LeadState.QUALIFIED),
            (LeadState.QUALIFIED, LeadState.CLOSED),
        ],
    )
    def test_accepts_valid_transition(
        self,
        from_state: LeadState,
        to_state: LeadState,
    ) -> None:
        assert (
            check_record_state_change(
                lead_exists=True,
                from_state=from_state.value,
                to_state=to_state.value,
                changed_by_account_id=STAFF_ID,
            )
            is None
        )

    def test_rejects_missing_lead(self) -> None:
        assert (
            check_record_state_change(
                lead_exists=False,
                from_state=LeadState.PENDING.value,
                to_state=LeadState.REACHED_OUT.value,
                changed_by_account_id=STAFF_ID,
            )
            is RecordStateChangeError.LEAD_NOT_FOUND
        )

    def test_rejects_invalid_from_state(self) -> None:
        assert (
            check_record_state_change(
                lead_exists=True,
                from_state="BOGUS",
                to_state=LeadState.REACHED_OUT.value,
                changed_by_account_id=STAFF_ID,
            )
            is RecordStateChangeError.INVALID_FROM_STATE
        )

    def test_rejects_invalid_to_state(self) -> None:
        assert (
            check_record_state_change(
                lead_exists=True,
                from_state=LeadState.PENDING.value,
                to_state="BOGUS",
                changed_by_account_id=STAFF_ID,
            )
            is RecordStateChangeError.INVALID_TO_STATE
        )

    def test_rejects_same_state(self) -> None:
        assert (
            check_record_state_change(
                lead_exists=True,
                from_state=LeadState.PENDING.value,
                to_state=LeadState.PENDING.value,
                changed_by_account_id=STAFF_ID,
            )
            is RecordStateChangeError.SAME_STATE
        )

    def test_rejects_missing_changed_by(self) -> None:
        assert (
            check_record_state_change(
                lead_exists=True,
                from_state=LeadState.PENDING.value,
                to_state=LeadState.REACHED_OUT.value,
                changed_by_account_id=None,
            )
            is RecordStateChangeError.CHANGED_BY_REQUIRED
        )

    def test_rejects_disallowed_transition(self) -> None:
        assert (
            check_record_state_change(
                lead_exists=True,
                from_state=LeadState.CLOSED.value,
                to_state=LeadState.PENDING.value,
                changed_by_account_id=STAFF_ID,
            )
            is RecordStateChangeError.INVALID_TRANSITION
        )

    def test_allowed_for_archived_lead(self) -> None:
        """D3 — archive does not block recording transitions."""
        archived_at = datetime(2026, 6, 1, tzinfo=UTC)
        assert (
            check_record_state_change(
                lead_exists=True,
                from_state=LeadState.PENDING.value,
                to_state=LeadState.REACHED_OUT.value,
                changed_by_account_id=STAFF_ID,
            )
            is None
        )
        assert archived_at is not None  # precondition layer ignores archive flag
