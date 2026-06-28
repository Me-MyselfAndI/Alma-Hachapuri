"""Pydantic schemas — state history.

Spec: docs/entities/lead-state-history.md (L7 ``LeadStateHistoryRead``).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from src.domains.state_history.models import LeadStateHistory


class LeadStateHistoryRead(BaseModel):
    """Public audit row returned by L7 and embeddable on ``LeadRead``."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    from_state: str | None
    to_state: str
    changed_by_account_id: UUID | None
    changed_by_email: EmailStr | None
    note: str | None = None
    created_at: datetime


def history_row_to_read(
    row: LeadStateHistory,
    *,
    changed_by_email: str | None = None,
) -> LeadStateHistoryRead:
    """Build a read model from an ORM row plus optional joined account email."""

    return LeadStateHistoryRead(
        id=row.id,
        lead_id=row.lead_id,
        from_state=row.from_state,
        to_state=row.to_state,
        changed_by_account_id=row.changed_by_account_id,
        changed_by_email=changed_by_email,
        note=row.note,
        created_at=row.created_at,
    )
