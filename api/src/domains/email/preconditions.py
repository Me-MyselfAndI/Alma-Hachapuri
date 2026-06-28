"""Pure precondition rules for the email domain (F2.3 / F2.6).

No permission checks — those live in route deps. These functions encode
data/state rules documented in docs/entities/email-notification.md.
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID


class EmailStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


def can_retry_failed_send(*, status: str | EmailStatus) -> bool:
    """E3 — retry only when the original notification row status is failed."""
    return EmailStatus(status) == EmailStatus.FAILED


def pick_conversation_id(
    *,
    provided: UUID | None,
    existing_for_lead_recipient: UUID | None,
    new_id: UUID,
) -> UUID:
    """Resolve conversation_id for a send or reply.

    Priority: explicit ``conversation_id`` (E2 body) > existing thread for
    ``(lead_id, recipient)`` > ``new_id`` for first message in a thread.
    """
    if provided is not None:
        return provided
    if existing_for_lead_recipient is not None:
        return existing_for_lead_recipient
    return new_id


def lead_emails_accessible(*, lead_exists: bool) -> bool:
    """D3 — archived leads remain readable; only a missing lead denies access."""
    return lead_exists
