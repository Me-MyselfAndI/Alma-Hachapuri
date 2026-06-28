"""Precondition tests for email domain — data/state rules only (F2.6).

Permission enforcement is bypassed in conftest; these tests do not cover RBAC.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domains.email.preconditions import (
    EmailStatus,
    can_retry_failed_send,
    lead_emails_accessible,
    pick_conversation_id,
)


class TestRetryFailedSend:
    """E3 — RetryFailedEmail only when status=failed."""

    def test_allows_retry_when_failed(self) -> None:
        assert can_retry_failed_send(status=EmailStatus.FAILED) is True
        assert can_retry_failed_send(status="failed") is True

    @pytest.mark.parametrize(
        "status",
        [EmailStatus.PENDING, EmailStatus.SENT, "pending", "sent"],
    )
    def test_rejects_retry_when_not_failed(self, status: str | EmailStatus) -> None:
        assert can_retry_failed_send(status=status) is False


class TestConversationThreading:
    """Conversation ID resolution — one thread per (lead_id, recipient)."""

    def test_explicit_conversation_id_wins(self) -> None:
        provided = uuid4()
        existing = uuid4()
        new_id = uuid4()
        assert (
            pick_conversation_id(
                provided=provided,
                existing_for_lead_recipient=existing,
                new_id=new_id,
            )
            is provided
        )

    def test_reuses_existing_thread_when_no_explicit_id(self) -> None:
        existing = uuid4()
        new_id = uuid4()
        assert (
            pick_conversation_id(
                provided=None,
                existing_for_lead_recipient=existing,
                new_id=new_id,
            )
            is existing
        )

    def test_creates_new_thread_when_none_exists(self) -> None:
        new_id = uuid4()
        assert (
            pick_conversation_id(
                provided=None,
                existing_for_lead_recipient=None,
                new_id=new_id,
            )
            is new_id
        )

    def test_s7_prospect_and_staff_get_separate_threads(self) -> None:
        """S7 — different recipients on same lead resolve independent conversation ids."""
        prospect_thread = uuid4()
        staff_thread = uuid4()
        first_prospect_send = pick_conversation_id(
            provided=None,
            existing_for_lead_recipient=None,
            new_id=prospect_thread,
        )
        first_staff_send = pick_conversation_id(
            provided=None,
            existing_for_lead_recipient=None,
            new_id=staff_thread,
        )
        assert first_prospect_send != first_staff_send

    def test_follow_up_reuses_prospect_thread(self) -> None:
        prospect_thread = uuid4()
        follow_up = pick_conversation_id(
            provided=None,
            existing_for_lead_recipient=prospect_thread,
            new_id=uuid4(),
        )
        assert follow_up == prospect_thread

    def test_e2_explicit_id_overrides_existing_thread(self) -> None:
        existing = uuid4()
        override = uuid4()
        assert (
            pick_conversation_id(
                provided=override,
                existing_for_lead_recipient=existing,
                new_id=uuid4(),
            )
            is override
        )


class TestLeadEmailAccess:
    """D3 — archived leads remain accessible for email sub-routes."""

    def test_list_emails_allowed_when_lead_exists(self) -> None:
        assert lead_emails_accessible(lead_exists=True) is True

    def test_list_emails_denied_only_when_lead_missing(self) -> None:
        assert lead_emails_accessible(lead_exists=False) is False
