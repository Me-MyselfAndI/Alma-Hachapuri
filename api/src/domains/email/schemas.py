"""Pydantic schemas — email notification domain.

Spec: docs/entities/email-notification.md (L6, E1–E4, E6).
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    """Generic pagination envelope for E4."""

    items: list[T]
    total: int
    page: int
    page_size: int


class EmailNotificationRead(BaseModel):
    """Outbound shape for notification rows."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    pending_intake_id: UUID | None = None
    conversation_id: UUID
    recipient: EmailStr
    template: str
    subject: str
    status: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime


class EmailSendRequest(BaseModel):
    """E2 — staff-initiated send."""

    template: str = Field(..., min_length=1, max_length=100)
    recipient: EmailStr | None = None
    conversation_id: UUID | None = None
    subject: str | None = Field(None, min_length=1, max_length=200)
    body: str | None = Field(None, min_length=1, max_length=10000)


class EmailPreviewRequest(BaseModel):
    """Default subject + body for a staff send template."""

    template: str = Field(..., min_length=1, max_length=100)


class EmailPreviewResponse(BaseModel):
    subject: str
    body: str


class EmailTemplateInfo(BaseModel):
    """E6 — template catalog entry."""

    key: str
    description: str
    default_recipient: str
