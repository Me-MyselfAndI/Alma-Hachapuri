"""StorageService — S2.

Pure precondition helpers (``validate_resume_file`` kwargs form,
``assert_download_allowed``, ``is_past_retention``) live alongside the
filesystem-backed storage operations consumed by L1 (save) and L5 (download).

Storage layout (local v1):

* ``<settings.uploads_dir>/<uuid>.<ext>``           — permanent resume binaries
* ``<settings.uploads_dir>/temp/<uuid>.<ext>``      — pending intake binaries
  written by Flow A1 (L1a) before the email-verification step promotes them.

``storage_key`` values stored in :class:`ResumeFile` are **relative** to
``settings.uploads_dir`` so the uploads directory can be relocated (or swapped
for S3 in the future) without rewriting the database.

Mime sniffing: v1 trusts the multipart ``Content-Type`` header on the
:class:`fastapi.UploadFile`. python-magic would give a stronger guarantee, but
it is an optional dependency and not in ``api/requirements.txt``; the header
check is sufficient for the assessment and matches the spec note in
``docs/entities/resume-file.md``.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid as uuid_pkg
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.core.config import settings
from src.domains.resume_file.models import ResumeFile

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)
MAX_BYTES = 10 * 1024 * 1024

EXTENSION_BY_MIME: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

TEMP_SUBDIR = "temp"
_STREAM_CHUNK_BYTES = 64 * 1024


class ResumeValidationError(ValueError):
    """Invalid mime type or size for resume upload."""


class ResumeDownloadError(ValueError):
    """Lead or resume missing for download."""


# ---------------------------------------------------------------------------
# Pure precondition helpers (F2.6 — no I/O, no exceptions other than ValueError)
# ---------------------------------------------------------------------------


def _validate_metadata(mime_type: str, size_bytes: int) -> None:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ResumeValidationError(f"Unsupported mime type: {mime_type}")
    if size_bytes <= 0:
        raise ResumeValidationError("File is empty")
    if size_bytes > MAX_BYTES:
        raise ResumeValidationError(f"File exceeds max size of {MAX_BYTES} bytes")


def validate_resume_file(
    file: UploadFile | None = None,
    *,
    mime_type: str | None = None,
    size_bytes: int | None = None,
) -> None:
    """Validate a resume upload against SaveResume preconditions.

    Two call styles:

    * ``validate_resume_file(upload)`` — raises :class:`fastapi.HTTPException`
      with status 400 when the ``UploadFile`` carries a disallowed mime type
      or exceeds ``MAX_BYTES``. Used by HTTP routes / services.
    * ``validate_resume_file(mime_type=..., size_bytes=...)`` — raises
      :class:`ResumeValidationError`. Used by pure precondition tests and
      callers that already have the metadata in hand.
    """

    if file is not None:
        size = file.size if file.size is not None else _size_of_upload(file)
        try:
            _validate_metadata(file.content_type or "", size)
        except ResumeValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        return

    if mime_type is None or size_bytes is None:
        raise TypeError(
            "validate_resume_file requires either `file` or both "
            "`mime_type` and `size_bytes`",
        )
    _validate_metadata(mime_type, size_bytes)


def assert_download_allowed(
    *,
    lead_exists: bool,
    resume_exists: bool,
    archived_at: datetime | None = None,
) -> None:
    """Precondition check for DownloadResume.

    Archived leads are allowed (D3). ``archived_at`` is accepted for call-site
    clarity but does not block download.
    """
    if not lead_exists:
        raise ResumeDownloadError("Lead not found")
    if not resume_exists:
        raise ResumeDownloadError("Resume not found")


def is_past_retention(
    *,
    archived_at: datetime | None,
    now: datetime,
    retention_days: int,
) -> bool:
    """Return True when the resume file should be purged per F2.5 retention policy."""
    if archived_at is None or retention_days <= 0:
        return False
    return (now - archived_at) >= timedelta(days=retention_days)


# ---------------------------------------------------------------------------
# Storage operations (filesystem-backed v1)
# ---------------------------------------------------------------------------


def _uploads_root() -> Path:
    """Resolve the uploads directory at call time so tests can monkeypatch settings."""
    return Path(settings.uploads_dir)


def _size_of_upload(file: UploadFile) -> int:
    """Best-effort size lookup for an ``UploadFile`` whose ``.size`` is None."""
    pos = file.file.tell()
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(pos)
    return size


def _extension_for(mime_type: str) -> str:
    """Map an allowed mime type to a canonical lowercase extension."""
    return EXTENSION_BY_MIME.get(mime_type, "")


def _generate_storage_key(mime_type: str, *, subdir: str | None = None) -> str:
    """Generate a UUID-based storage key (path relative to ``uploads_dir``)."""
    name = f"{uuid_pkg.uuid4().hex}{_extension_for(mime_type)}"
    return f"{subdir}/{name}" if subdir else name


def _resolve_path(storage_key: str) -> Path:
    """Resolve a storage key to an absolute path under the uploads root.

    Rejects keys that try to escape the uploads root (defence in depth — keys
    are server-generated, but a missing check would be the kind of bug we'd
    regret).
    """
    root = _uploads_root().resolve()
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"storage_key escapes uploads root: {storage_key!r}") from exc
    return candidate


def _write_upload_to(path: Path, file: UploadFile) -> int:
    """Stream ``file`` to ``path`` and return the bytes written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file.file.seek(0)
    written = 0
    with path.open("wb") as out:
        while True:
            chunk = file.file.read(_STREAM_CHUNK_BYTES)
            if not chunk:
                break
            out.write(chunk)
            written += len(chunk)
    file.file.seek(0)
    return written


def save_resume(db: Session, file: UploadFile) -> ResumeFile:
    """Validate, persist binary, insert ``resume_files`` row, return ORM instance.

    The caller's transaction owns the DB row; on rollback callers should call
    :func:`delete_orphan` with the returned ``storage_key`` to reclaim disk.
    """
    validate_resume_file(file)
    mime_type = file.content_type or "application/octet-stream"
    storage_key = _generate_storage_key(mime_type)
    target = _resolve_path(storage_key)

    size_bytes = _write_upload_to(target, file)

    record = ResumeFile(
        storage_key=storage_key,
        original_filename=file.filename or "resume",
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(record)
    db.flush()
    return record


def save_temp_resume(file: UploadFile) -> str:
    """Persist a resume in the temp subdirectory for the email-verification flow.

    Returns the storage key (relative path). No DB row is created — the
    intake-pending row tracks the key until
    :func:`promote_temp_to_permanent` runs in L1b.
    """
    validate_resume_file(file)
    mime_type = file.content_type or "application/octet-stream"
    storage_key = _generate_storage_key(mime_type, subdir=TEMP_SUBDIR)
    target = _resolve_path(storage_key)
    _write_upload_to(target, file)
    return storage_key


def promote_temp_to_permanent(
    db: Session,
    *,
    temp_storage_key: str,
    original_filename: str,
    mime_type: str,
    size_bytes: int,
) -> ResumeFile:
    """Move a verified-intake temp file to its permanent location and insert the row.

    Called from ``VerifyEmailAndCreateLead`` (L1b). The new storage key keeps
    the same extension; we mint a fresh UUID rather than reusing the temp one
    to avoid leaking the pending identifier into the permanent layout.
    """

    if not temp_storage_key.startswith(f"{TEMP_SUBDIR}/"):
        raise ValueError(
            f"temp_storage_key must live under {TEMP_SUBDIR!r}: {temp_storage_key!r}"
        )

    source = _resolve_path(temp_storage_key)
    if not source.exists():
        raise FileNotFoundError(f"Temp resume missing: {temp_storage_key}")

    new_key = _generate_storage_key(mime_type)
    destination = _resolve_path(new_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))

    record = ResumeFile(
        storage_key=new_key,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(record)
    db.flush()
    return record


def open_stream(resume_file: ResumeFile) -> tuple[Iterator[bytes], str]:
    """Open a binary read iterator for ``resume_file`` (for ``StreamingResponse``).

    Returns ``(iterator, content_type)``. The iterator opens the underlying
    file lazily and closes it when exhausted (FastAPI iterates eagerly during
    response streaming, so the file lifecycle is bounded by the request).
    """
    path = _resolve_path(resume_file.storage_key)
    if not path.exists():
        raise ResumeDownloadError("Resume not found")

    def _iter() -> Iterator[bytes]:
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(_STREAM_CHUNK_BYTES)
                if not chunk:
                    break
                yield chunk

    return _iter(), resume_file.mime_type


def delete_orphan(storage_key: str) -> None:
    """Best-effort delete of a storage object; never raises.

    Used when a write succeeded on disk but the surrounding DB transaction
    rolled back. Logs warnings instead of propagating so callers don't mask
    the original failure.
    """
    try:
        path = _resolve_path(storage_key)
    except ValueError:
        logger.warning("delete_orphan: refusing suspicious storage_key %r", storage_key)
        return

    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("delete_orphan: failed to remove %s: %s", path, exc)
