"""Precondition tests for lead domain — data/state rules only (F2.6).

Permission enforcement is bypassed in conftest; these tests do not cover RBAC.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.domains.lead.preconditions import (
    LeadState,
    VerificationTokenError,
    VALID_TRANSITIONS,
    check_verification_token,
    is_valid_state_transition,
    lead_readable_by_id,
    lead_visible_in_list,
    normalize_email,
)

UTC = timezone.utc


class TestNormalizeEmail:
    def test_lowercases_and_strips(self) -> None:
        assert normalize_email("  Jane.Doe@Example.COM  ") == "jane.doe@example.com"


class TestStateTransitionMatrix:
    @pytest.mark.parametrize(
        ("from_state", "to_state"),
        [
            (LeadState.PENDING, LeadState.REACHED_OUT),
            (LeadState.PENDING, LeadState.QUALIFIED),
            (LeadState.PENDING, LeadState.DISQUALIFIED),
            (LeadState.REACHED_OUT, LeadState.PENDING),
            (LeadState.REACHED_OUT, LeadState.QUALIFIED),
            (LeadState.REACHED_OUT, LeadState.DISQUALIFIED),
            (LeadState.QUALIFIED, LeadState.CLOSED),
            (LeadState.DISQUALIFIED, LeadState.CLOSED),
        ],
    )
    def test_allowed_transitions(self, from_state: LeadState, to_state: LeadState) -> None:
        assert is_valid_state_transition(from_state, to_state) is True

    @pytest.mark.parametrize(
        ("from_state", "to_state"),
        [
            (LeadState.PENDING, LeadState.PENDING),
            (LeadState.PENDING, LeadState.CLOSED),
            (LeadState.REACHED_OUT, LeadState.REACHED_OUT),
            (LeadState.REACHED_OUT, LeadState.CLOSED),
            (LeadState.QUALIFIED, LeadState.PENDING),
            (LeadState.QUALIFIED, LeadState.REACHED_OUT),
            (LeadState.DISQUALIFIED, LeadState.QUALIFIED),
            (LeadState.CLOSED, LeadState.PENDING),
            (LeadState.CLOSED, LeadState.REACHED_OUT),
        ],
    )
    def test_disallowed_transitions(self, from_state: LeadState, to_state: LeadState) -> None:
        assert is_valid_state_transition(from_state, to_state) is False

    def test_closed_has_no_outgoing_edges(self) -> None:
        assert VALID_TRANSITIONS[LeadState.CLOSED] == frozenset()

    def test_accepts_string_state_values(self) -> None:
        assert is_valid_state_transition("PENDING", "REACHED_OUT") is True
        assert is_valid_state_transition("CLOSED", "PENDING") is False


class TestVerificationToken:
    def _now(self) -> datetime:
        return datetime(2026, 6, 27, 12, 0, 0, tzinfo=UTC)

    def test_valid_token(self) -> None:
        now = self._now()
        assert (
            check_verification_token(
                expires_at=now + timedelta(hours=24),
                used_at=None,
                now=now,
            )
            is None
        )

    def test_expired_token_rejected(self) -> None:
        now = self._now()
        assert (
            check_verification_token(
                expires_at=now - timedelta(seconds=1),
                used_at=None,
                now=now,
            )
            is VerificationTokenError.EXPIRED
        )

    def test_used_token_rejected(self) -> None:
        now = self._now()
        assert (
            check_verification_token(
                expires_at=now + timedelta(hours=24),
                used_at=now - timedelta(minutes=5),
                now=now,
            )
            is VerificationTokenError.ALREADY_USED
        )

    def test_used_takes_precedence_over_expired(self) -> None:
        now = self._now()
        assert (
            check_verification_token(
                expires_at=now - timedelta(hours=1),
                used_at=now - timedelta(minutes=10),
                now=now,
            )
            is VerificationTokenError.ALREADY_USED
        )


class TestArchivedLeadAccess:
    """D3 — archived leads remain fully accessible by direct id."""

    def test_get_lead_allowed_when_archived(self) -> None:
        archived_at = datetime(2026, 6, 1, tzinfo=UTC)
        assert lead_readable_by_id(exists=True) is True
        assert archived_at is not None  # archive timestamp does not affect read-by-id

    def test_get_lead_denied_only_when_missing(self) -> None:
        assert lead_readable_by_id(exists=False) is False

    def test_list_hides_archived_by_default(self) -> None:
        archived_at = datetime(2026, 6, 1, tzinfo=UTC)
        assert lead_visible_in_list(archived_at=archived_at, include_archived=False) is False

    def test_list_shows_archived_when_flag_set(self) -> None:
        archived_at = datetime(2026, 6, 1, tzinfo=UTC)
        assert lead_visible_in_list(archived_at=archived_at, include_archived=True) is True

    def test_active_lead_always_listed(self) -> None:
        assert lead_visible_in_list(archived_at=None, include_archived=False) is True
