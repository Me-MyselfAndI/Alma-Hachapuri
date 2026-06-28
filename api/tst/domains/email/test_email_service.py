"""Service-layer tests for ``EmailService``.

Spec: docs/entities/email-notification.md (S7a, S7, E2/E3 helpers).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.domains.account.models import Account
from src.domains.email.models import EmailNotification
from src.domains.email.preconditions import EmailStatus
from src.domains.email.service import EmailDeliveryError, EmailService
from src.domains.lead.models import Lead, LeadIntakePending
from src.domains.prospect.models import Prospect
from src.domains.resume_file.models import ResumeFile


UTC = timezone.utc


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


def _make_prospect(db: Session, *, email: str = "jane@example.com") -> Prospect:
    prospect = Prospect(
        email=email,
        first_name="Jane",
        last_name="Doe",
    )
    db.add(prospect)
    db.flush()
    return prospect


def _make_attorney(
    db: Session,
    *,
    email: str = "attorney@firm.com",
    work_email: str | None = "attorney.work@firm.com",
) -> Account:
    account = Account(
        email=email,
        password_hash="hash",
        role="attorney",
        first_name="Att",
        last_name="Orney",
        work_email=work_email,
        is_default_assignee=True,
        is_active=True,
    )
    db.add(account)
    db.flush()
    return account


def _make_lead(
    db: Session,
    *,
    prospect: Prospect | None = None,
    resume: ResumeFile | None = None,
    assigned: Account | None = None,
    email: str = "jane@example.com",
) -> Lead:
    if prospect is None:
        prospect = _make_prospect(db, email=email)
    if resume is None:
        resume = _make_resume(db)
    now = datetime.now(UTC)
    lead = Lead(
        prospect_id=prospect.id,
        first_name=prospect.first_name,
        last_name=prospect.last_name,
        email=email,
        resume_file_id=resume.id,
        state="PENDING",
        state_changed_at=now,
        assigned_account_id=assigned.id if assigned else None,
        created_at=now,
        updated_at=now,
    )
    db.add(lead)
    db.flush()
    return lead


def _make_pending(db: Session, *, email: str = "pending@example.com") -> LeadIntakePending:
    pending = LeadIntakePending(
        email=email,
        first_name="Pat",
        last_name="Pending",
        temp_resume_storage_key=f"temp/{uuid.uuid4()}.pdf",
        token_hash=f"hash-{uuid.uuid4()}",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(pending)
    db.flush()
    return pending


class TestRenderTemplate:
    @pytest.mark.parametrize(
        "template",
        [
            "email_verification",
            "prospect_confirmation",
            "attorney_new_lead",
            "prospect_follow_up",
        ],
    )
    def test_render_template_returns_subject_and_html(self, template: str) -> None:
        context = {
            "first_name": "Jane",
            "verify_url": "http://localhost:3000/verify?token=abc",
            "expires_at": "2026-06-28T00:00:00Z",
            "prospect_name": "Jane Doe",
            "lead_id": str(uuid.uuid4()),
            "lead_url": "http://localhost:3000/leads/x",
        }
        subject, html = EmailService.render_template(template, context)
        assert isinstance(subject, str) and len(subject) > 0
        assert isinstance(html, str) and len(html) > 0
        assert "<p>" in html

    def test_unknown_template_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown email template"):
            EmailService.render_template("not_a_template", {})


class TestResolveConversationId:
    def test_reuses_existing_thread_via_service(self, db_session: Session) -> None:
        lead = _make_lead(db_session)
        existing_conv = uuid.uuid4()
        row = EmailNotification(
            lead_id=lead.id,
            conversation_id=existing_conv,
            recipient=lead.email,
            template="prospect_confirmation",
            subject="Hi",
            status=EmailStatus.SENT.value,
        )
        db_session.add(row)
        db_session.flush()

        resolved = EmailService.resolve_conversation_id(
            db_session, lead_id=lead.id, recipient=lead.email
        )
        assert resolved == existing_conv

    def test_creates_new_thread_when_none_exists(self, db_session: Session) -> None:
        lead = _make_lead(db_session)
        resolved = EmailService.resolve_conversation_id(
            db_session, lead_id=lead.id, recipient=lead.email
        )
        assert isinstance(resolved, uuid.UUID)

    def test_explicit_conversation_id_overrides_existing(
        self, db_session: Session
    ) -> None:
        lead = _make_lead(db_session)
        existing_conv = uuid.uuid4()
        override = uuid.uuid4()
        db_session.add(
            EmailNotification(
                lead_id=lead.id,
                conversation_id=existing_conv,
                recipient=lead.email,
                template="prospect_confirmation",
                subject="Hi",
                status=EmailStatus.SENT.value,
            )
        )
        db_session.flush()

        resolved = EmailService.resolve_conversation_id(
            db_session,
            lead_id=lead.id,
            recipient=lead.email,
            conversation_id=override,
        )
        assert resolved == override


class TestSendVerificationEmail:
    @patch("src.domains.email.service.EmailService._send_smtp")
    def test_send_verification_email_success(
        self, mock_smtp: MagicMock, db_session: Session
    ) -> None:
        pending = _make_pending(db_session)
        result = EmailService.send_verification_email(
            db_session,
            pending_intake_id=pending.id,
            email="Pending@Example.com",
            token="raw-token",
        )

        assert result.lead_id is None
        assert result.pending_intake_id == pending.id
        assert result.recipient == "pending@example.com"
        assert result.template == "email_verification"
        assert result.status == EmailStatus.SENT.value
        mock_smtp.assert_called_once()

    @patch("src.domains.email.service.EmailService._send_smtp")
    def test_send_verification_email_raises_on_smtp_failure(
        self, mock_smtp: MagicMock, db_session: Session
    ) -> None:
        mock_smtp.side_effect = EmailDeliveryError("connection refused")
        pending = _make_pending(db_session)

        with pytest.raises(EmailDeliveryError):
            EmailService.send_verification_email(
                db_session,
                pending_intake_id=pending.id,
                email=pending.email,
                token="raw-token",
            )


class TestSendLeadCreatedNotifications:
    @patch("src.domains.email.service.EmailService._send_smtp")
    def test_sends_prospect_and_attorney_emails(
        self, mock_smtp: MagicMock, db_session: Session
    ) -> None:
        attorney = _make_attorney(db_session)
        lead = _make_lead(db_session, assigned=attorney)

        results = EmailService.send_lead_created_notifications(db_session, lead=lead)

        assert len(results) == 2
        templates = {r.template for r in results}
        assert templates == {"prospect_confirmation", "attorney_new_lead"}
        assert all(r.status == EmailStatus.SENT.value for r in results)
        assert results[0].conversation_id != results[1].conversation_id
        assert mock_smtp.call_count == 2

    @patch("src.domains.email.service.EmailService._send_smtp")
    def test_never_raises_when_smtp_fails(
        self, mock_smtp: MagicMock, db_session: Session
    ) -> None:
        mock_smtp.side_effect = EmailDeliveryError("timeout")
        attorney = _make_attorney(db_session)
        lead = _make_lead(db_session, assigned=attorney)

        results = EmailService.send_lead_created_notifications(db_session, lead=lead)

        assert len(results) == 2
        assert all(r.status == EmailStatus.FAILED.value for r in results)


class TestRetryFailed:
    @patch("src.domains.email.service.EmailService._send_smtp")
    def test_retry_failed_updates_sent_status(
        self, mock_smtp: MagicMock, db_session: Session
    ) -> None:
        lead = _make_lead(db_session)
        row = EmailNotification(
            lead_id=lead.id,
            conversation_id=uuid.uuid4(),
            recipient=lead.email,
            template="prospect_follow_up",
            subject="Old subject",
            status=EmailStatus.FAILED.value,
            error_message="timeout",
        )
        db_session.add(row)
        db_session.flush()

        updated = EmailService.retry_failed(db_session, row.id)

        assert updated.status == EmailStatus.SENT.value
        assert updated.error_message is None
        mock_smtp.assert_called_once()

    def test_retry_rejects_non_failed_status(self, db_session: Session) -> None:
        lead = _make_lead(db_session)
        row = EmailNotification(
            lead_id=lead.id,
            conversation_id=uuid.uuid4(),
            recipient=lead.email,
            template="prospect_follow_up",
            subject="Hi",
            status=EmailStatus.SENT.value,
        )
        db_session.add(row)
        db_session.flush()

        with pytest.raises(HTTPException) as exc:
            EmailService.retry_failed(db_session, row.id)
        assert exc.value.status_code == 409

    @patch("src.domains.email.service.EmailService._send_smtp")
    def test_retry_rejects_verification_email(
        self, mock_smtp: MagicMock, db_session: Session
    ) -> None:
        pending = LeadIntakePending(
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
            temp_resume_storage_key="temp/x.pdf",
            token_hash="old-hash",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db_session.add(pending)
        db_session.flush()
        row = EmailNotification(
            pending_intake_id=pending.id,
            conversation_id=uuid.uuid4(),
            recipient=pending.email,
            template="email_verification",
            subject="Verify",
            status=EmailStatus.FAILED.value,
            error_message="smtp down",
        )
        db_session.add(row)
        db_session.flush()

        with pytest.raises(HTTPException) as exc:
            EmailService.retry_failed(db_session, row.id)

        assert exc.value.status_code == 409
        assert "submit the form again" in exc.value.detail.lower()
        mock_smtp.assert_not_called()


class TestSendTemplate:
    @patch("src.domains.email.service.EmailService._send_smtp")
    def test_staff_send_uses_conversation_resolution(
        self, mock_smtp: MagicMock, db_session: Session
    ) -> None:
        lead = _make_lead(db_session)
        first = EmailService.send_template(
            db_session,
            lead_id=lead.id,
            template="prospect_follow_up",
        )
        second = EmailService.send_template(
            db_session,
            lead_id=lead.id,
            template="prospect_follow_up",
        )

        assert first.conversation_id == second.conversation_id
        assert first.status == EmailStatus.SENT.value

    def test_staff_send_rejects_unknown_template(self, db_session: Session) -> None:
        lead = _make_lead(db_session)
        with pytest.raises(HTTPException) as exc:
            EmailService.send_template(
                db_session,
                lead_id=lead.id,
                template="email_verification",
            )
        assert exc.value.status_code == 422

    @patch("src.domains.email.service.EmailService._send_smtp")
    def test_staff_send_accepts_subject_and_body_overrides(
        self, mock_smtp: MagicMock, db_session: Session
    ) -> None:
        lead = _make_lead(db_session, first_name="Jane")
        notification = EmailService.send_template(
            db_session,
            lead_id=lead.id,
            template="prospect_follow_up",
            subject_override="Checking in",
            body_override="Hi Jane,\n\nJust following up on your application.",
        )

        assert notification.subject == "Checking in"
        assert notification.status == EmailStatus.SENT.value
        mock_smtp.assert_called_once()
        assert "Just following up" in mock_smtp.call_args.kwargs["html_body"]
        assert "Jane" in mock_smtp.call_args.kwargs["html_body"]

    def test_staff_send_rejects_empty_subject_override(self, db_session: Session) -> None:
        lead = _make_lead(db_session)
        with pytest.raises(HTTPException) as exc:
            EmailService.send_template(
                db_session,
                lead_id=lead.id,
                template="prospect_follow_up",
                subject_override="   ",
            )
        assert exc.value.status_code == 422


class TestPreviewStaffEmail:
    def test_preview_follow_up_includes_lead_first_name(
        self, db_session: Session
    ) -> None:
        lead = _make_lead(db_session, first_name="Jane")
        subject, body = EmailService.preview_staff_email(
            db_session, lead_id=lead.id, template="prospect_follow_up"
        )
        assert subject == "Follow-up on your submission"
        assert "Jane" in body

    def test_preview_rejects_unknown_template(self, db_session: Session) -> None:
        lead = _make_lead(db_session)
        with pytest.raises(HTTPException) as exc:
            EmailService.preview_staff_email(
                db_session, lead_id=lead.id, template="email_verification"
            )
        assert exc.value.status_code == 422
