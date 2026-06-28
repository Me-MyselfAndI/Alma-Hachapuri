"""Pydantic schemas — account & auth.

Spec: docs/entities/account.md (A1–A9 request/response shapes).

Naming convention:
* ``*Create`` / ``*Update`` — inbound request bodies, mirror admin-facing API.
* ``*Read`` — outbound shapes (no ``password_hash`` ever).
* ``AccountMe`` — ``AccountRead`` + ``permissions[]`` for the signed-in user.
* ``Paginated[T]`` — generic envelope reused across list endpoints.

D7 (email lowercasing) is applied at the service layer rather than in
validators so a single source of truth normalizes the lookup key the same way
``ProspectService`` does.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from src.core.permissions import Role


T = TypeVar("T")


class TokenResponse(BaseModel):
    """A1 — OAuth2 bearer token envelope."""

    access_token: str
    token_type: str = "bearer"


class AccountCreate(BaseModel):
    """A3 — admin create. ``role`` is required and immutable post-create."""

    email: EmailStr
    password: Annotated[str, Field(min_length=8)]
    role: Role
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]
    work_email: EmailStr | None = None
    is_default_assignee: bool = False


class AccountUpdate(BaseModel):
    """A6 — admin update. ``role`` is intentionally absent (immutable per spec).

    The model rejects ``role`` even if a client sends it — a ``model_validator``
    pre-pass inspects the raw payload before Pydantic strips unknown fields.
    Without this, ``extra="ignore"`` would silently swallow ``role`` and a
    client could think the change went through.
    """

    model_config = ConfigDict(extra="forbid")

    is_active: bool | None = None
    password: Annotated[str, Field(min_length=8)] | None = None
    first_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    last_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    work_email: EmailStr | None = None
    is_default_assignee: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_role(cls, data: object) -> object:
        if isinstance(data, dict) and "role" in data:
            raise ValueError("role is immutable; create a new account to change role")
        return data


class AccountRead(BaseModel):
    """Outbound shape. ``password_hash`` is never exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: Role
    first_name: str
    last_name: str
    work_email: EmailStr | None
    is_default_assignee: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccountMe(AccountRead):
    """A2 — ``AccountRead`` + the caller's permission keys."""

    permissions: list[str]


class AccountEmailUpdate(BaseModel):
    """A7 — change own email; requires fresh password proof."""

    email: EmailStr
    current_password: str


class AccountPasswordUpdate(BaseModel):
    """A8 — change own password."""

    current_password: str
    new_password: Annotated[str, Field(min_length=8)]


class Paginated(BaseModel, Generic[T]):
    """Generic pagination envelope for ``GET /accounts`` and friends."""

    items: list[T]
    total: int
    page: int
    page_size: int
