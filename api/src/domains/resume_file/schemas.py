"""Pydantic schemas — resume file.

Public responses **never expose** ``storage_key`` (filesystem/S3 location).
Clients only ever see the metadata in :class:`ResumeFileRead`; binary
content is delivered via the streaming download endpoint (L5).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeFileRead(BaseModel):
    """Public metadata projection for a resume file.

    Matches the columns documented in ``docs/entities/resume-file.md`` minus
    ``storage_key``. The storage key is an internal pointer (local path or
    S3 key) and must not leak to API consumers.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime
