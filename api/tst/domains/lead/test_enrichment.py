"""Tests for F7.1 dummy enrichment (S8)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.core.config import settings
from src.domains.lead.enrichment import (
    extract_custom_fields_dummy,
    run_lead_enrichment,
    schedule_lead_enrichment,
)
from src.domains.lead.models import Lead


def test_extract_custom_fields_dummy_shape() -> None:
    lead_id = uuid.uuid4()
    fields = extract_custom_fields_dummy(lead_id=lead_id)

    assert fields["_source"] == "dummy_llm_v1"
    assert fields["lead_id"] == str(lead_id)
    assert "primary_skills" in fields


def test_run_lead_enrichment_writes_custom_fields(db_session: Session) -> None:
    from src.core.permissions import Role
    from src.domains.account.schemas import AccountCreate
    from src.domains.account.service import AccountService
    from src.domains.prospect.models import Prospect
    from src.domains.resume_file.models import ResumeFile

    attorney = AccountService.create_account(
        db_session,
        AccountCreate(
            email="enrich.attorney@firm.com",
            password="pass12345",
            role=Role.ATTORNEY,
            first_name="En",
            last_name="Rich",
            is_default_assignee=True,
        ),
    )
    prospect = Prospect(
        email="prospect@example.com",
        first_name="Pat",
        last_name="Lee",
    )
    db_session.add(prospect)
    db_session.flush()
    resume = ResumeFile(
        storage_key="test.pdf",
        original_filename="cv.pdf",
        mime_type="application/pdf",
        size_bytes=100,
    )
    db_session.add(resume)
    db_session.flush()
    lead = Lead(
        prospect_id=prospect.id,
        first_name="Pat",
        last_name="Lee",
        email="prospect@example.com",
        resume_file_id=resume.id,
        assigned_account_id=attorney.id,
    )
    db_session.add(lead)
    db_session.commit()

    with patch("src.domains.lead.enrichment.SessionLocal") as mock_factory:
        mock_db = MagicMock()
        mock_db.get.return_value = lead
        mock_factory.return_value = mock_db
        run_lead_enrichment(lead.id)

    assert lead.custom_fields is not None
    assert lead.custom_fields["_source"] == "dummy_llm_v1"
    mock_db.commit.assert_called_once()


def test_schedule_noop_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_llm_enrichment", False)
    with patch("src.domains.lead.enrichment.run_lead_enrichment") as mock_run:
        schedule_lead_enrichment(uuid.uuid4())
        mock_run.assert_not_called()


def test_schedule_runs_when_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_llm_enrichment", True)
    lead_id = uuid.uuid4()
    with patch("src.domains.lead.enrichment.run_lead_enrichment") as mock_run:
        schedule_lead_enrichment(lead_id)
        mock_run.assert_called_once_with(lead_id)
