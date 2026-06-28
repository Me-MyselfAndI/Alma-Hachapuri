"""SQLAlchemy models — Lead and LeadIntakePending.

Spec: docs/entities/lead.md. Lifecycle states stored as VARCHAR (enum lives
in code at `src/domains/lead/preconditions.py::LeadState`). `state_changed_at`
powers "how long waiting / going cold" — see F2.1 design notes in the doc.

`LeadIntakePending` backs the email-verification pre-lead row (Flow A1, L1a).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    prospect_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("prospects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Snapshot at submit (denormalized from form).",
    )
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Snapshot at submit (denormalized; lowercase per D7).",
    )
    resume_file_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("resume_files.id", ondelete="RESTRICT"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        comment="Enum: PENDING | REACHED_OUT | QUALIFIED | DISQUALIFIED | CLOSED.",
    )
    state_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Set on create and on every state change (replaces IN_CONTACT/ON_HOLD).",
    )
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custom_fields: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="LLM-extracted; null until enriched (F7.1).",
    )
    assigned_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft-delete timestamp (L14). Null = active.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class LeadIntakePending(Base):
    """Pre-lead row for email verification flow (L1a).

    Holds form data + temp resume location until the user clicks the
    verification link (L1b). On success, `used_at` is set and a real
    `Lead` row is created. See docs/entities/lead.md ("Pending intake").
    """

    __tablename__ = "lead_intake_pending"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Lowercase + trim normalized (D7).",
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temp_resume_storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Pending file location until L1b promotes it to resume_files.",
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Hash of single-use verification token; never store the raw token.",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when L1b succeeds; prevents replay.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
