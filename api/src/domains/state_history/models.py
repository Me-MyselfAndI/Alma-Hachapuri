"""SQLAlchemy model — LeadStateHistory.

Spec: docs/entities/lead-state-history.md. Append-only audit of lead state
changes. Initial row on create has `from_state` and `changed_by_account_id`
both null (system insert during L1b orchestration).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LeadStateHistory(Base):
    __tablename__ = "lead_state_history"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_state: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Null on initial create.",
    )
    to_state: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="Null when system inserted the initial row.",
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional reason captured on L10 transitions.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
