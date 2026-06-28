"""Service-layer tests for ``ProspectService`` — S1 (find-or-create) + reads.

Spec: docs/entities/prospect.md.

These tests use the SQLite ``db_session`` fixture (see ``api/tst/conftest.py``).
SQLite is sufficient here because the prospect schema is plain VARCHAR/TIMESTAMP
plus a UUID (which the conftest renders as CHAR(36) under SQLite). Lead rows
created in ``list_leads_for_prospect`` only need ``prospect_id``, ``created_at``
and the snapshot fields populated — we synthesize the FK targets directly so
the test stays focused on ordering / inclusion rules.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.domains.lead.models import Lead
from src.domains.prospect.models import Prospect
from src.domains.prospect.service import ProspectService
from src.domains.resume_file.models import ResumeFile


UTC = timezone.utc


def _make_resume(db: Session) -> ResumeFile:
    """Insert a stub resume row so ``Lead.resume_file_id`` FK can resolve."""

    resume = ResumeFile(
        storage_key=f"resumes/{uuid.uuid4()}.pdf",
        original_filename="resume.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
    )
    db.add(resume)
    db.flush()
    return resume


def _make_lead(
    db: Session,
    *,
    prospect: Prospect,
    resume: ResumeFile,
    created_at: datetime,
    archived_at: datetime | None = None,
) -> Lead:
    """Insert a minimal Lead row at a specific ``created_at``.

    We bypass ``server_default`` for ``created_at`` so tests can assert order
    deterministically (SQLite resolves ``CURRENT_TIMESTAMP`` at one-second
    granularity, which would tie our rows).
    """

    lead = Lead(
        prospect_id=prospect.id,
        first_name=prospect.first_name,
        last_name=prospect.last_name,
        email=prospect.email,
        resume_file_id=resume.id,
        state="PENDING",
        state_changed_at=created_at,
        created_at=created_at,
        updated_at=created_at,
        archived_at=archived_at,
    )
    db.add(lead)
    db.flush()
    return lead


class TestFindOrCreateByEmail:
    def test_creates_new_on_first_call(self, db_session: Session) -> None:
        prospect, created = ProspectService.find_or_create_by_email(
            db_session,
            email="jane.doe@example.com",
            first_name="Jane",
            last_name="Doe",
        )

        assert created is True
        assert prospect.id is not None
        assert prospect.email == "jane.doe@example.com"
        assert prospect.first_name == "Jane"
        assert prospect.last_name == "Doe"

    def test_returns_existing_on_second_call(self, db_session: Session) -> None:
        first, created_first = ProspectService.find_or_create_by_email(
            db_session,
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )
        assert created_first is True

        second, created_second = ProspectService.find_or_create_by_email(
            db_session,
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )

        assert created_second is False
        assert second.id == first.id

    def test_email_lookup_normalizes_case_and_whitespace(
        self, db_session: Session
    ) -> None:
        """D7 — match key is normalized lowercase/trim on both write and lookup."""

        first, _ = ProspectService.find_or_create_by_email(
            db_session,
            email="  Jane.Doe@Example.COM ",
            first_name="Jane",
            last_name="Doe",
        )

        same, created = ProspectService.find_or_create_by_email(
            db_session,
            email="jane.doe@example.com",
            first_name="Jane",
            last_name="Doe",
        )

        assert created is False
        assert same.id == first.id
        assert first.email == "jane.doe@example.com"

    def test_updates_names_last_write_wins(self, db_session: Session) -> None:
        existing, _ = ProspectService.find_or_create_by_email(
            db_session,
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )

        updated, created = ProspectService.find_or_create_by_email(
            db_session,
            email="jane@example.com",
            first_name="Jane",
            last_name="Smith",
        )

        assert created is False
        assert updated.id == existing.id
        assert updated.first_name == "Jane"
        assert updated.last_name == "Smith"


class TestGetProspect:
    def test_returns_row_when_found(self, db_session: Session) -> None:
        prospect, _ = ProspectService.find_or_create_by_email(
            db_session,
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )

        result = ProspectService.get_prospect(db_session, prospect.id)

        assert result is not None
        assert result.id == prospect.id

    def test_returns_none_for_unknown_uuid(self, db_session: Session) -> None:
        result = ProspectService.get_prospect(db_session, uuid.uuid4())
        assert result is None


class TestListLeadsForProspect:
    def test_returns_leads_ordered_by_created_at_desc(self, db_session: Session) -> None:
        prospect, _ = ProspectService.find_or_create_by_email(
            db_session,
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )
        resume = _make_resume(db_session)

        base = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        oldest = _make_lead(db_session, prospect=prospect, resume=resume, created_at=base)
        middle = _make_lead(
            db_session,
            prospect=prospect,
            resume=resume,
            created_at=base + timedelta(days=1),
        )
        newest = _make_lead(
            db_session,
            prospect=prospect,
            resume=resume,
            created_at=base + timedelta(days=2),
        )

        leads = ProspectService.list_leads_for_prospect(db_session, prospect.id)

        assert [lead.id for lead in leads] == [newest.id, middle.id, oldest.id]

    def test_empty_list_for_prospect_without_leads(self, db_session: Session) -> None:
        prospect, _ = ProspectService.find_or_create_by_email(
            db_session,
            email="loner@example.com",
            first_name="Lone",
            last_name="Wolf",
        )

        leads = ProspectService.list_leads_for_prospect(db_session, prospect.id)
        assert leads == []

    def test_includes_archived_leads(self, db_session: Session) -> None:
        """D3 — archived leads stay in the prospect's lead list."""

        prospect, _ = ProspectService.find_or_create_by_email(
            db_session,
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )
        resume = _make_resume(db_session)

        active = _make_lead(
            db_session,
            prospect=prospect,
            resume=resume,
            created_at=datetime(2026, 6, 1, tzinfo=UTC),
        )
        archived = _make_lead(
            db_session,
            prospect=prospect,
            resume=resume,
            created_at=datetime(2026, 5, 1, tzinfo=UTC),
            archived_at=datetime(2026, 5, 15, tzinfo=UTC),
        )

        leads = ProspectService.list_leads_for_prospect(db_session, prospect.id)
        ids = {lead.id for lead in leads}

        assert active.id in ids
        assert archived.id in ids


def test_get_prospect_unknown_returns_none(db_session: Session) -> None:
    """Module-level smoke test mirroring the spec's wording verbatim."""

    assert ProspectService.get_prospect(db_session, uuid.uuid4()) is None
