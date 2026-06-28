"""Service-layer tests for ``LeadStateHistoryService`` — S6.

Spec: docs/entities/lead-state-history.md.

Uses the SQLite ``db_session`` fixture (see ``api/tst/conftest.py``). History
rows set ``created_at`` explicitly so ordering assertions stay deterministic
under SQLite's one-second timestamp granularity.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.domains.account.models import Account
from src.domains.lead.models import Lead
from src.domains.lead.preconditions import LeadState
from src.domains.prospect.models import Prospect
from src.domains.resume_file.models import ResumeFile
from src.domains.state_history.service import LeadStateHistoryService

UTC = timezone.utc


def _make_prospect(db: Session) -> Prospect:
    prospect = Prospect(
        email="jane@example.com",
        first_name="Jane",
        last_name="Doe",
    )
    db.add(prospect)
    db.flush()
    return prospect


def _make_resume(db: Session) -> ResumeFile:
    resume = ResumeFile(
        storage_key=f"resumes/{uuid.uuid4()}.pdf",
        original_filename="resume.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
    )
    db.add(resume)
    db.flush()
    return resume


def _make_lead(db: Session, *, prospect: Prospect, resume: ResumeFile) -> Lead:
    lead = Lead(
        prospect_id=prospect.id,
        first_name=prospect.first_name,
        last_name=prospect.last_name,
        email=prospect.email,
        resume_file_id=resume.id,
        state=LeadState.PENDING.value,
        state_changed_at=datetime(2026, 6, 1, tzinfo=UTC),
        created_at=datetime(2026, 6, 1, tzinfo=UTC),
        updated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    db.add(lead)
    db.flush()
    return lead


def _make_account(db: Session, *, email: str = "attorney@firm.com") -> Account:
    account = Account(
        email=email,
        password_hash="not-used-in-tests",
        role="attorney",
        first_name="Att",
        last_name="Orney",
    )
    db.add(account)
    db.flush()
    return account


def _make_lead_fixture(db: Session) -> Lead:
    prospect = _make_prospect(db)
    resume = _make_resume(db)
    return _make_lead(db, prospect=prospect, resume=resume)


class TestRecordInitial:
    def test_creates_row_with_null_from_state_and_changed_by(
        self, db_session: Session
    ) -> None:
        lead = _make_lead_fixture(db_session)

        row = LeadStateHistoryService.record_initial(db_session, lead_id=lead.id)

        assert row.id is not None
        assert row.lead_id == lead.id
        assert row.from_state is None
        assert row.to_state == LeadState.PENDING.value
        assert row.changed_by_account_id is None
        assert row.note is None


class TestRecordTransition:
    def test_stores_note_and_changed_by(self, db_session: Session) -> None:
        lead = _make_lead_fixture(db_session)
        actor = _make_account(db_session, email="attorney@firm.com")

        row = LeadStateHistoryService.record_transition(
            db_session,
            lead_id=lead.id,
            from_state=LeadState.PENDING.value,
            to_state=LeadState.REACHED_OUT.value,
            changed_by=actor,
            note="Left voicemail",
        )

        assert row is not None
        assert row.from_state == LeadState.PENDING.value
        assert row.to_state == LeadState.REACHED_OUT.value
        assert row.changed_by_account_id == actor.id
        assert row.note == "Left voicemail"

    def test_no_op_when_same_state(self, db_session: Session) -> None:
        lead = _make_lead_fixture(db_session)
        actor = _make_account(db_session)

        result = LeadStateHistoryService.record_transition(
            db_session,
            lead_id=lead.id,
            from_state=LeadState.PENDING.value,
            to_state=LeadState.PENDING.value,
            changed_by=actor,
        )

        assert result is None
        assert LeadStateHistoryService.list_for_lead(db_session, lead.id) == []


class TestListForLead:
    def test_ordered_by_created_at_asc(self, db_session: Session) -> None:
        lead = _make_lead_fixture(db_session)
        actor = _make_account(db_session)

        base = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
        initial = LeadStateHistoryService.record_initial(db_session, lead_id=lead.id)
        initial.created_at = base

        first = LeadStateHistoryService.record_transition(
            db_session,
            lead_id=lead.id,
            from_state=LeadState.PENDING.value,
            to_state=LeadState.REACHED_OUT.value,
            changed_by=actor,
        )
        assert first is not None
        first.created_at = base + timedelta(hours=1)

        second = LeadStateHistoryService.record_transition(
            db_session,
            lead_id=lead.id,
            from_state=LeadState.REACHED_OUT.value,
            to_state=LeadState.QUALIFIED.value,
            changed_by=actor,
        )
        assert second is not None
        second.created_at = base + timedelta(hours=2)

        db_session.flush()

        rows = LeadStateHistoryService.list_for_lead(db_session, lead.id)

        assert [row.id for row in rows] == [initial.id, first.id, second.id]
