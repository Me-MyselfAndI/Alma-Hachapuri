"""SQLAlchemy model — EmailNotification.

Spec: docs/entities/email-notification.md. Audit log for outbound email tied
to a lead (or pending intake for S7a verification). ``conversation_id`` groups
one thread = ``(lead_id, recipient)``; we index ``(conversation_id, created_at)``
to support timeline queries (L6/E4).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class EmailNotification(Base):
    __tablename__ = "email_notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Null for S7a verification emails sent before lead exists.",
    )
    pending_intake_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("lead_intake_pending.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Set for S7a email_verification rows (pre-lead).",
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=False,
        comment="Groups emails in one (lead_id, recipient) thread.",
    )
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    template: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Template key, e.g. prospect_confirmation, attorney_new_lead, email_verification.",
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="Enum: pending | sent | failed.",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_email_notifications_conversation_id_created_at",
            "conversation_id",
            "created_at",
        ),
    )
