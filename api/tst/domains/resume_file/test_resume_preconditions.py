"""Precondition tests for resume_file domain (F2.6 — no permission checks)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.domains.resume_file.service import (
    ALLOWED_MIME_TYPES,
    MAX_BYTES,
    ResumeDownloadError,
    ResumeValidationError,
    assert_download_allowed,
    is_past_retention,
    validate_resume_file,
)


class TestSaveResumeValidation:
    @pytest.mark.parametrize("mime_type", sorted(ALLOWED_MIME_TYPES))
    def test_accepts_allowed_mime_types(self, mime_type: str) -> None:
        validate_resume_file(mime_type=mime_type, size_bytes=1024)

    @pytest.mark.parametrize(
        "mime_type",
        [
            "text/plain",
            "application/zip",
            "image/png",
            "application/vnd.ms-excel",
        ],
    )
    def test_rejects_disallowed_mime_types(self, mime_type: str) -> None:
        with pytest.raises(ResumeValidationError, match="Unsupported mime type"):
            validate_resume_file(mime_type=mime_type, size_bytes=1024)

    def test_rejects_empty_file(self) -> None:
        with pytest.raises(ResumeValidationError, match="empty"):
            validate_resume_file(mime_type="application/pdf", size_bytes=0)

    def test_rejects_oversized_file(self) -> None:
        with pytest.raises(ResumeValidationError, match="max size"):
            validate_resume_file(mime_type="application/pdf", size_bytes=MAX_BYTES + 1)

    def test_accepts_file_at_max_size(self) -> None:
        validate_resume_file(mime_type="application/pdf", size_bytes=MAX_BYTES)


class TestDownloadResumePreconditions:
    def test_allows_download_for_active_lead(self) -> None:
        assert_download_allowed(
            lead_exists=True,
            resume_exists=True,
            archived_at=None,
        )

    def test_allows_download_for_archived_lead(self) -> None:
        """D3 — archived leads remain readable; archive must not block download."""
        archived_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert_download_allowed(
            lead_exists=True,
            resume_exists=True,
            archived_at=archived_at,
        )

    def test_rejects_missing_lead(self) -> None:
        with pytest.raises(ResumeDownloadError, match="Lead not found"):
            assert_download_allowed(
                lead_exists=False,
                resume_exists=True,
                archived_at=None,
            )

    def test_rejects_missing_resume_even_when_archived(self) -> None:
        archived_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ResumeDownloadError, match="Resume not found"):
            assert_download_allowed(
                lead_exists=True,
                resume_exists=False,
                archived_at=archived_at,
            )


class TestRetentionPolicy:
    def test_active_lead_never_past_retention(self, utc_now: datetime) -> None:
        assert (
            is_past_retention(
                archived_at=None,
                now=utc_now,
                retention_days=90,
            )
            is False
        )

    def test_disabled_when_retention_days_zero(self, utc_now: datetime) -> None:
        archived_at = utc_now - timedelta(days=365)
        assert (
            is_past_retention(
                archived_at=archived_at,
                now=utc_now,
                retention_days=0,
            )
            is False
        )

    def test_not_past_retention_before_period_elapses(self, utc_now: datetime) -> None:
        archived_at = utc_now - timedelta(days=89)
        assert (
            is_past_retention(
                archived_at=archived_at,
                now=utc_now,
                retention_days=90,
            )
            is False
        )

    def test_past_retention_on_day_boundary(self, utc_now: datetime) -> None:
        archived_at = utc_now - timedelta(days=90)
        assert (
            is_past_retention(
                archived_at=archived_at,
                now=utc_now,
                retention_days=90,
            )
            is True
        )

    @pytest.mark.parametrize("retention_days", [30, 90, 365])
    def test_past_retention_respects_configured_days(
        self,
        utc_now: datetime,
        retention_days: int,
    ) -> None:
        archived_at = utc_now - timedelta(days=retention_days)
        assert (
            is_past_retention(
                archived_at=archived_at,
                now=utc_now,
                retention_days=retention_days,
            )
            is True
        )


class TestDownloadResumeRouteFailures:
    """L5 HTTP — docs/entities/resume-file.md Preconditions."""

    def test_download_404_missing_lead(self, client) -> None:
        import uuid

        response = client.get(f"/api/v1/leads/{uuid.uuid4()}/resume")
        assert response.status_code == 404

    def test_download_404_when_resume_row_missing(self, client, db_session) -> None:
        from src.domains.resume_file.models import ResumeFile
        from tst.shared.doc_fixtures import seed_lead

        lead = seed_lead(db_session)
        row = db_session.get(ResumeFile, lead.resume_file_id)
        assert row is not None
        db_session.delete(row)
        db_session.commit()

        response = client.get(f"/api/v1/leads/{lead.id}/resume")
        assert response.status_code == 404

    def test_download_not_403_for_archived_lead(self, client, db_session) -> None:
        from tst.shared.doc_fixtures import seed_lead

        lead = seed_lead(db_session, archived=True)
        response = client.get(f"/api/v1/leads/{lead.id}/resume")
        assert response.status_code != 403
