"""Pydantic schemas — lead.

Spec: docs/entities/lead.md (L1a–L4, L10, L13, L14).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from pydantic.types import StringConstraints

from src.domains.account.schemas import Paginated
from src.domains.lead.preconditions import LeadState
from src.domains.prospect.schemas import ProspectSummary


class LeadVerificationRequestResponse(BaseModel):
    """L1a — check-your-email payload."""

    message: str = "Check your email to confirm your submission."
    email: EmailStr


class LeadVerificationRequestInput(BaseModel):
    """Validated L1a form fields (multipart body)."""

    first_name: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    last_name: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    email: EmailStr
    source: Annotated[str | None, StringConstraints(max_length=200)] = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _strip_required_names(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("source", mode="before")
    @classmethod
    def _strip_optional_source(cls, value: object) -> object | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class LeadVerifyRequest(BaseModel):
    """L1b POST body — SPA verification."""

    token: Annotated[str, Field(min_length=1)]


class LeadCreateResponse(BaseModel):
    """L1b success — minimal public response."""

    id: UUID
    state: LeadState
    message: str = "Thank you for your submission."


class AssignedAccountSummary(BaseModel):
    """Embedded assignee on LeadRead."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    work_email: EmailStr | None = None
    email: EmailStr


class LeadResumeSummary(BaseModel):
    """Resume metadata embedded in LeadRead; download via L5."""

    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    download_url: str


class LeadRead(BaseModel):
    """L3 detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prospect_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    state: LeadState
    state_changed_at: datetime
    source: str | None
    custom_fields: dict | None
    assigned_account_id: UUID | None
    assigned_account: AssignedAccountSummary | None = None
    resume: LeadResumeSummary | None = None
    prospect: ProspectSummary | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LeadListItem(BaseModel):
    """L2 dashboard row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    state: LeadState
    state_changed_at: datetime
    source: str | None
    assigned_account_id: UUID | None
    assigned_account_name: str | None = None
    archived_at: datetime | None = None
    created_at: datetime


class LeadListParams(BaseModel):
    """Query params for ListLeads / ExportLeads."""

    state: LeadState | None = None
    assigned_account_id: UUID | None = None
    mine: bool = False
    include_archived: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class LeadUpdate(BaseModel):
    """L4 PATCH body — at least one field required."""

    state: LeadState | None = None
    assigned_account_id: UUID | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> LeadUpdate:
        if self.state is None and self.assigned_account_id is None:
            raise ValueError("At least one field must be provided")
        return self


class LeadTransitionRequest(BaseModel):
    """L10 state transition."""

    to_state: LeadState
    note: str | None = None


# Re-export pagination envelope for router convenience.
__all__ = [
    "LeadCreateResponse",
    "LeadListItem",
    "LeadListParams",
    "LeadRead",
    "LeadTransitionRequest",
    "LeadUpdate",
    "LeadVerificationRequestInput",
    "LeadVerificationRequestResponse",
    "LeadVerifyRequest",
    "Paginated",
]
