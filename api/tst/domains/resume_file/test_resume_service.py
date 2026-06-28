"""Service tests for ``src.domains.resume_file.service`` (S2 — StorageService).

These tests exercise the filesystem-backed storage operations only; the HTTP
download route (L5) is covered separately as part of the lead slice's
integration tests. ``settings.uploads_dir`` is monkeypatched per-test via
``tmp_path`` so we never touch the real ``storage/uploads/`` directory.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from src.core.config import settings
from src.domains.resume_file import service as storage_service
from src.domains.resume_file.models import ResumeFile
from src.domains.resume_file.service import (
    ALLOWED_MIME_TYPES,
    MAX_BYTES,
    TEMP_SUBDIR,
    delete_orphan,
    open_stream,
    promote_temp_to_permanent,
    save_resume,
    save_temp_resume,
    validate_resume_file,
)

PDF_MIME = "application/pdf"
DOC_MIME = "application/msword"
DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def uploads_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``settings.uploads_dir`` to a per-test temp directory.

    The service reads ``settings.uploads_dir`` at call time, so a simple
    ``monkeypatch.setattr`` on the live settings instance is enough — no need
    to reimport modules.
    """
    target = tmp_path / "uploads"
    target.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", str(target))
    return target


@pytest.fixture
def fake_db() -> MagicMock:
    """A SQLAlchemy ``Session`` stand-in that records add/flush calls.

    The service flushes after add so the ORM receives DB-assigned defaults; we
    don't need real Postgres for service-level assertions, just to verify the
    row is staged and the storage_key flows through.
    """
    db = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    return db


def _make_upload(
    *,
    content: bytes = b"%PDF-1.4 fake content",
    content_type: str = PDF_MIME,
    filename: str = "resume.pdf",
    size: int | None = None,
) -> UploadFile:
    """Build a Starlette ``UploadFile`` suitable for direct service calls."""
    file_size = len(content) if size is None else size
    return UploadFile(
        file=BytesIO(content),
        size=file_size,
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


# ---------------------------------------------------------------------------
# validate_resume_file (UploadFile path)
# ---------------------------------------------------------------------------


class TestValidateResumeFileUpload:
    @pytest.mark.parametrize("mime_type", sorted(ALLOWED_MIME_TYPES))
    def test_accepts_pdf_doc_docx(self, mime_type: str) -> None:
        validate_resume_file(_make_upload(content_type=mime_type))

    @pytest.mark.parametrize(
        "mime_type",
        ["text/plain", "image/png", "application/zip", "application/vnd.ms-excel"],
    )
    def test_rejects_bad_mime(self, mime_type: str) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_resume_file(_make_upload(content_type=mime_type))
        assert exc_info.value.status_code == 400
        assert "mime type" in str(exc_info.value.detail).lower()

    def test_rejects_oversize(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_resume_file(
                _make_upload(content=b"x" * 32, size=MAX_BYTES + 1),
            )
        assert exc_info.value.status_code == 400
        assert "max size" in str(exc_info.value.detail).lower()

    def test_rejects_empty_upload(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            validate_resume_file(_make_upload(content=b"", size=0))
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# save_resume
# ---------------------------------------------------------------------------


class TestSaveResume:
    def test_writes_file_and_stages_row(
        self,
        uploads_dir: Path,
        fake_db: MagicMock,
    ) -> None:
        payload = b"%PDF-1.4 hello world"
        upload = _make_upload(content=payload, filename="cv.pdf")

        record = save_resume(fake_db, upload)

        assert isinstance(record, ResumeFile)
        assert record.original_filename == "cv.pdf"
        assert record.mime_type == PDF_MIME
        assert record.size_bytes == len(payload)
        assert record.storage_key.endswith(".pdf")

        on_disk = uploads_dir / record.storage_key
        assert on_disk.exists(), "save_resume must write the binary to uploads_dir"
        assert on_disk.read_bytes() == payload

        fake_db.add.assert_called_once_with(record)
        fake_db.flush.assert_called_once()

    def test_storage_key_is_uuid_with_extension(
        self,
        uploads_dir: Path,
        fake_db: MagicMock,
    ) -> None:
        record = save_resume(fake_db, _make_upload(content_type=DOCX_MIME, filename="x.docx"))
        assert record.storage_key.endswith(".docx")
        assert "/" not in record.storage_key, "permanent keys live at uploads_dir root"


# ---------------------------------------------------------------------------
# save_temp_resume
# ---------------------------------------------------------------------------


class TestSaveTempResume:
    def test_writes_to_temp_subdirectory(self, uploads_dir: Path) -> None:
        payload = b"%PDF-1.4 pending intake"
        upload = _make_upload(content=payload, filename="pending.pdf")

        storage_key = save_temp_resume(upload)

        assert storage_key.startswith(f"{TEMP_SUBDIR}/")
        assert storage_key.endswith(".pdf")

        on_disk = uploads_dir / storage_key
        assert on_disk.exists()
        assert on_disk.read_bytes() == payload

    def test_no_db_row_required(self, uploads_dir: Path) -> None:
        """save_temp_resume must not require or touch a Session."""
        storage_key = save_temp_resume(_make_upload())
        assert (uploads_dir / storage_key).exists()


# ---------------------------------------------------------------------------
# promote_temp_to_permanent
# ---------------------------------------------------------------------------


class TestPromoteTempToPermanent:
    def test_moves_file_and_creates_row(
        self,
        uploads_dir: Path,
        fake_db: MagicMock,
    ) -> None:
        payload = b"%PDF-1.4 verified intake"
        temp_key = save_temp_resume(_make_upload(content=payload, filename="cv.pdf"))
        temp_path = uploads_dir / temp_key
        assert temp_path.exists()

        record = promote_temp_to_permanent(
            fake_db,
            temp_storage_key=temp_key,
            original_filename="cv.pdf",
            mime_type=PDF_MIME,
            size_bytes=len(payload),
        )

        assert isinstance(record, ResumeFile)
        assert record.storage_key.endswith(".pdf")
        assert not record.storage_key.startswith(f"{TEMP_SUBDIR}/")

        permanent_path = uploads_dir / record.storage_key
        assert permanent_path.exists(), "binary must be moved to permanent path"
        assert permanent_path.read_bytes() == payload
        assert not temp_path.exists(), "temp file must be gone after promotion"

        fake_db.add.assert_called_once_with(record)
        fake_db.flush.assert_called_once()

    def test_rejects_non_temp_storage_key(
        self,
        uploads_dir: Path,
        fake_db: MagicMock,
    ) -> None:
        with pytest.raises(ValueError, match="temp_storage_key"):
            promote_temp_to_permanent(
                fake_db,
                temp_storage_key="not-in-temp.pdf",
                original_filename="cv.pdf",
                mime_type=PDF_MIME,
                size_bytes=10,
            )

    def test_raises_when_temp_file_missing(
        self,
        uploads_dir: Path,
        fake_db: MagicMock,
    ) -> None:
        with pytest.raises(FileNotFoundError):
            promote_temp_to_permanent(
                fake_db,
                temp_storage_key=f"{TEMP_SUBDIR}/missing.pdf",
                original_filename="cv.pdf",
                mime_type=PDF_MIME,
                size_bytes=10,
            )


# ---------------------------------------------------------------------------
# open_stream
# ---------------------------------------------------------------------------


class TestOpenStream:
    def test_yields_written_bytes(
        self,
        uploads_dir: Path,
        fake_db: MagicMock,
    ) -> None:
        payload = b"%PDF-1.4 streamed content"
        record = save_resume(fake_db, _make_upload(content=payload, filename="cv.pdf"))

        iterator, content_type = open_stream(record)
        streamed = b"".join(iterator)

        assert streamed == payload
        assert content_type == PDF_MIME

    def test_raises_when_file_missing(self, uploads_dir: Path) -> None:
        ghost = ResumeFile(
            storage_key="missing.pdf",
            original_filename="cv.pdf",
            mime_type=PDF_MIME,
            size_bytes=0,
        )
        with pytest.raises(storage_service.ResumeDownloadError):
            open_stream(ghost)


# ---------------------------------------------------------------------------
# delete_orphan
# ---------------------------------------------------------------------------


class TestDeleteOrphan:
    def test_removes_existing_file(
        self,
        uploads_dir: Path,
        fake_db: MagicMock,
    ) -> None:
        record = save_resume(fake_db, _make_upload(content=b"%PDF-1.4 ", filename="cv.pdf"))
        on_disk = uploads_dir / record.storage_key
        assert on_disk.exists()

        delete_orphan(record.storage_key)

        assert not on_disk.exists()

    def test_silent_when_file_missing(
        self,
        uploads_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        delete_orphan("never-existed.pdf")

        assert not any(
            rec.levelname == "ERROR" for rec in caplog.records
        ), "delete_orphan must not log at ERROR for missing files"

    def test_refuses_path_traversal_key(
        self,
        uploads_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Defence-in-depth: a malformed key must not delete outside the root."""
        sibling = uploads_dir.parent / "outside.txt"
        sibling.write_bytes(b"protected")

        delete_orphan("../outside.txt")

        assert sibling.exists(), "delete_orphan must not escape uploads_dir"
