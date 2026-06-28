"""HTTP route tests for staff email — docs/entities/email-notification.md + F6.2 scope."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from src.core.permissions import Role
from src.domains.lead.models import Lead
from src.domains.lead.preconditions import LeadState
from src.domains.prospect.models import Prospect
from src.domains.resume_file.models import ResumeFile
from tst.shared.doc_fixtures import seed_failed_email, seed_lead, seed_sent_email

UTC = timezone.utc
PDF_MIME = "application/pdf"


def _seed_lead(db_session, *, assignee_id: uuid.UUID) -> Lead:
    prospect = Prospect(
        id=uuid.uuid4(),
        email="lead@example.com",
        first_name="Jane",
        last_name="Doe",
    )
    db_session.add(prospect)
    resume = ResumeFile(
        storage_key="test/cv.pdf",
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
        email="lead@example.com",
        resume_file_id=resume.id,
        state=LeadState.PENDING.value,
        state_changed_at=now,
        assigned_account_id=assignee_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


class TestStaffEmailRouteScope:
    def test_attorney_cannot_send_on_unassigned_lead(self, role_client, db_session) -> None:
        _, owner = role_client(Role.ATTORNEY, email="owner@firm.com")
        client, _other = role_client(
            Role.ATTORNEY,
            email="other@firm.com",
            is_default_assignee=False,
        )
        lead = _seed_lead(db_session, assignee_id=owner.id)

        with patch("src.domains.email.service.EmailService._send_smtp"):
            response = client.post(
                f"/api/v1/leads/{lead.id}/emails",
                json={
                    "template": "prospect_follow_up",
                    "recipient": lead.email,
                    "subject": "Follow up",
                    "body": "Hello",
                },
            )

        assert response.status_code == 403

    def test_attorney_can_send_on_own_lead(self, role_client, db_session) -> None:
        client, attorney = role_client(Role.ATTORNEY, email="owner@firm.com")
        lead = _seed_lead(db_session, assignee_id=attorney.id)

        with patch("src.domains.email.service.EmailService._send_smtp"):
            response = client.post(
                f"/api/v1/leads/{lead.id}/emails",
                json={
                    "template": "prospect_follow_up",
                    "recipient": lead.email,
                    "subject": "Follow up",
                    "body": "Hello",
                },
            )

        assert response.status_code == 201

    def test_attorney_cannot_preview_unassigned_lead(self, role_client, db_session) -> None:
        _, owner = role_client(Role.ATTORNEY, email="owner@firm.com")
        client, _other = role_client(
            Role.ATTORNEY,
            email="other@firm.com",
            is_default_assignee=False,
        )
        lead = _seed_lead(db_session, assignee_id=owner.id)

        response = client.post(
            f"/api/v1/leads/{lead.id}/emails/preview",
            json={"template": "prospect_follow_up"},
        )

        assert response.status_code == 403

    def test_intake_can_send_on_any_lead(self, role_client, db_session) -> None:
        _, owner = role_client(Role.ATTORNEY, email="owner@firm.com")
        intake_client, _intake = role_client(
            Role.INTAKE_COORDINATOR,
            email="intake@firm.com",
        )
        lead = _seed_lead(db_session, assignee_id=owner.id)

        with patch("src.domains.email.service.EmailService._send_smtp"):
            response = intake_client.post(
                f"/api/v1/leads/{lead.id}/emails",
                json={
                    "template": "prospect_follow_up",
                    "recipient": lead.email,
                    "subject": "Follow up",
                    "body": "Hello",
                },
            )

        assert response.status_code == 201


class TestListLeadEmailsFailures:
    def test_list_lead_emails_404_missing_lead(self, client) -> None:
        response = client.get(f"/api/v1/leads/{uuid.uuid4()}/emails")
        assert response.status_code == 404

    def test_list_emails_200_for_archived_lead(self, client, db_session) -> None:
        lead = seed_lead(db_session, archived=True)
        response = client.get(f"/api/v1/leads/{lead.id}/emails")
        assert response.status_code == 200


class TestGetEmailNotificationFailures:
    def test_get_email_404_missing_notification(self, client) -> None:
        response = client.get(f"/api/v1/emails/{uuid.uuid4()}")
        assert response.status_code == 404


class TestRetryFailedEmailFailures:
    def test_retry_409_when_status_sent(self, client, db_session) -> None:
        lead = seed_lead(db_session)
        sent = seed_sent_email(db_session, lead=lead)
        response = client.post(f"/api/v1/emails/{sent.id}/retry")
        assert response.status_code == 409

    def test_retry_404_missing_notification(self, client) -> None:
        response = client.post(f"/api/v1/emails/{uuid.uuid4()}/retry")
        assert response.status_code == 404

    def test_retry_failed_email_200(self, client, db_session) -> None:
        lead = seed_lead(db_session)
        failed = seed_failed_email(db_session, lead=lead)
        with patch("src.domains.email.service.EmailService._send_smtp"):
            response = client.post(f"/api/v1/emails/{failed.id}/retry")
        assert response.status_code == 200


class TestSendStaffEmailFailures:
    def test_send_404_missing_lead(self, client) -> None:
        with patch("src.domains.email.service.EmailService._send_smtp"):
            response = client.post(
                f"/api/v1/leads/{uuid.uuid4()}/emails",
                json={
                    "template": "prospect_follow_up",
                    "recipient": "x@example.com",
                    "subject": "Hi",
                    "body": "Hello",
                },
            )
        assert response.status_code == 404

    def test_send_422_unknown_template(self, client, db_session) -> None:
        lead = seed_lead(db_session)
        with patch("src.domains.email.service.EmailService._send_smtp"):
            response = client.post(
                f"/api/v1/leads/{lead.id}/emails",
                json={
                    "template": "not_a_real_template",
                    "recipient": lead.email,
                },
            )
        assert response.status_code == 422

    def test_preview_404_missing_lead(self, client) -> None:
        response = client.post(
            f"/api/v1/leads/{uuid.uuid4()}/emails/preview",
            json={"template": "prospect_follow_up"},
        )
        assert response.status_code == 404
