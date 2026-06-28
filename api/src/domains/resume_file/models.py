"""SQLAlchemy model — ResumeFile.

Spec: docs/entities/resume-file.md. Stores metadata only; the binary lives in
`storage/uploads/` (or S3) under `storage_key`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ResumeFile(Base):
    __tablename__ = "resume_files"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Relative path or S3 key, e.g. uploads/{uuid}.pdf. Never expose to client.",
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
