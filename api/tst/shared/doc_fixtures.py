"""Shared seed data for HTTP route tests aligned with entity Preconditions docs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.domains.email.models import EmailNotification
from src.domains.email.preconditions import EmailStatus
from src.domains.lead.models import Lead
from src.domains.lead.preconditions import LeadState
from src.domains.prospect.models import Prospect
from src.domains.resume_file.models import ResumeFile

UTC = timezone.utc
PDF_MIME = "application/pdf"


def seed_lead(
    db_session: Session,
    *,
    assignee_id: uuid.UUID | None = None,
    archived: bool = False,
) -> Lead:
    prospect = Prospect(
        id=uuid.uuid4(),
        email="doc-test@example.com",
        first_name="Jane",
        last_name="Doe",
    )
    db_session.add(prospect)
    resume = ResumeFile(
        storage_key="doc/test.pdf",
        original_filename="cv.pdf",
        mime_type=PDF_MIME,
        size_bytes=100,
    )
    db_session.add(resume)
    db_session.flush()

    now = datetime.now(UTC)
    lead = Lead(
        prospect_id=prospect.id,
        first_name="Jane",
        last_name="Doe",
        email="doc-test@example.com",
        resume_file_id=resume.id,
        state=LeadState.PENDING.value,
        state_changed_at=now,
        assigned_account_id=assignee_id,
        archived_at=now if archived else None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


def seed_failed_email(db_session: Session, *, lead: Lead) -> EmailNotification:
    row = EmailNotification(
        lead_id=lead.id,
        conversation_id=uuid.uuid4(),
        recipient=lead.email,
        template="prospect_follow_up",
        subject="Failed",
        status=EmailStatus.FAILED.value,
        error_message="smtp error",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def seed_sent_email(db_session: Session, *, lead: Lead) -> EmailNotification:
    row = EmailNotification(
        lead_id=lead.id,
        conversation_id=uuid.uuid4(),
        recipient=lead.email,
        template="prospect_follow_up",
        subject="Sent",
        status=EmailStatus.SENT.value,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row
