"""Pydantic schemas — prospect.

Spec: docs/entities/prospect.md (P1 ProspectRead, P2 ProspectLeadItem).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class ProspectRead(BaseModel):
    """P1 response shape. ``lead_count`` is computed at the service layer."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    lead_count: int
    created_at: datetime
    updated_at: datetime


class ProspectSummary(BaseModel):
    """Lightweight prospect identity for embedding (e.g. inside ``LeadRead``)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str


class ProspectLeadItem(BaseModel):
    """Per-lead row returned by P2 ``GET /prospects/{id}/leads``.

    Lighter than the full ``LeadRead`` — the prospect detail view only needs
    enough to render a list of "this person's submissions". D3: archived leads
    stay in the list, so ``archived_at`` is exposed for the UI to decorate.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    state: str
    created_at: datetime
    archived_at: datetime | None
