"""Service-layer tests for ``LeadService`` — L1a, L1b, transitions, token errors.

Spec: docs/entities/lead.md. Uses SQLite ``db_session`` and mocks SMTP/email
where delivery would hit the network.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from starlette.datastructures import Headers

from src.core.config import settings
from src.core.permissions import Role
from src.domains.account.models import Account
from src.domains.account.schemas import AccountCreate
from src.domains.account.service import AccountService
from src.domains.lead.models import Lead, LeadIntakePending
from src.domains.lead.preconditions import LeadState
from src.domains.lead.service import LeadService
from src.domains.resume_file.models import ResumeFile
from src.domains.state_history.models import LeadStateHistory

UTC = timezone.utc
PDF_MIME = "application/pdf"


@pytest.fixture
def uploads_dir(tmp_path, monkeypatch):
    target = tmp_path / "uploads"
    target.mkdir()
    monkeypatch.setattr(settings, "uploads_dir", str(target))
    return target


def _make_upload(
    *,
    content: bytes = b"%PDF-1.4 test resume",
    filename: str = "cv.pdf",
) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        size=len(content),
        filename=filename,
        headers=Headers({"content-type": PDF_MIME}),
    )


def _seed_default_attorney(db_session) -> Account:
    return AccountService.create_account(
        db_session,
        AccountCreate(
            email="default.attorney@firm.com",
            password="attorney-pass",
            role=Role.ATTORNEY,
            first_name="Default",
            last_name="Attorney",
            is_default_assignee=True,
        ),
    )


def _seed_staff(db_session, *, role: Role = Role.ADMIN) -> Account:
    return AccountService.create_account(
        db_session,
        AccountCreate(
            email=f"{role.value}@firm.com",
            password="staff-pass1",
            role=role,
            first_name="Staff",
            last_name="User",
        ),
    )


class TestRequestVerification:
    @patch("src.domains.lead.service.EmailService.send_verification_email")
    def test_creates_pending_row(
        self,
        mock_send,
        db_session,
        uploads_dir,
    ) -> None:
        mock_send.return_value = None

        response = LeadService.request_verification(
            db_session,
            first_name="Jane",
            last_name="Doe",
            email="Jane.Doe@Example.com",
            resume=_make_upload(),
        )

        assert response.email == "jane.doe@example.com"
        pending_rows = list(db_session.scalars(select(LeadIntakePending)))
        assert len(pending_rows) == 1
        assert pending_rows[0].email == "jane.doe@example.com"
        assert pending_rows[0].used_at is None
        mock_send.assert_called_once()

    @patch("src.domains.lead.service.EmailService.send_verification_email")
    def test_email_failure_rolls_back_pending(
        self,
        mock_send,
        db_session,
        uploads_dir,
    ) -> None:
        from src.domains.email.service import EmailDeliveryError

        mock_send.side_effect = EmailDeliveryError("smtp down")

        with pytest.raises(HTTPException) as exc_info:
            LeadService.request_verification(
                db_session,
                first_name="Jane",
                last_name="Doe",
                email="jane@example.com",
                resume=_make_upload(),
            )

        assert exc_info.value.status_code == 503
        assert db_session.scalars(select(LeadIntakePending)).all() == []


class TestVerifyAndCreateLead:
    @patch("src.domains.lead.service.EmailService.send_lead_created_notifications")
    @patch("src.domains.lead.service.EmailService.send_verification_email")
    def test_happy_path(
        self,
        mock_verify_send,
        mock_created_send,
        db_session,
        uploads_dir,
    ) -> None:
        mock_verify_send.return_value = None
        mock_created_send.return_value = None
        _seed_default_attorney(db_session)

        LeadService.request_verification(
            db_session,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            resume=_make_upload(),
        )
        pending = db_session.scalar(select(LeadIntakePending))
        assert pending is not None

        raw_token = mock_verify_send.call_args.kwargs["token"]
        lead = LeadService.verify_and_create_lead(db_session, token=raw_token)

        assert lead.state == LeadState.PENDING.value
        assert lead.email == "jane@example.com"
        assert lead.assigned_account_id is not None

        db_session.refresh(pending)
        assert pending.used_at is not None

        history = list(
            db_session.scalars(
                select(LeadStateHistory).where(LeadStateHistory.lead_id == lead.id)
            )
        )
        assert len(history) == 1
        assert history[0].from_state is None
        assert history[0].to_state == LeadState.PENDING.value

        mock_created_send.assert_called_once()


class TestStateTransitions:
    def _make_lead(self, db_session) -> tuple[Lead, Account]:
        attorney = _seed_default_attorney(db_session)
        actor = _seed_staff(db_session)
        prospect_id = uuid.uuid4()
        from src.domains.prospect.models import Prospect

        prospect = Prospect(
            id=prospect_id,
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )
        db_session.add(prospect)
        resume = ResumeFile(
            storage_key="test.pdf",
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
            email="jane@example.com",
            resume_file_id=resume.id,
            state=LeadState.PENDING.value,
            state_changed_at=now,
            assigned_account_id=attorney.id,
            created_at=now,
            updated_at=now,
        )
        db_session.add(lead)
        db_session.commit()
        db_session.refresh(lead)
        return lead, actor

    @pytest.mark.parametrize(
        ("from_state", "to_state"),
        [
            (LeadState.PENDING, LeadState.REACHED_OUT),
            (LeadState.PENDING, LeadState.QUALIFIED),
            (LeadState.REACHED_OUT, LeadState.PENDING),
            (LeadState.QUALIFIED, LeadState.CLOSED),
        ],
    )
    def test_allowed_transitions(
        self,
        db_session,
        from_state: LeadState,
        to_state: LeadState,
    ) -> None:
        lead, actor = self._make_lead(db_session)
        lead.state = from_state.value
        db_session.commit()

        updated = LeadService.transition_lead(
            db_session,
            lead_id=lead.id,
            to_state=to_state,
            actor=actor,
        )

        assert updated.state == to_state.value
        rows = list(
            db_session.scalars(
                select(LeadStateHistory).where(LeadStateHistory.lead_id == lead.id)
            )
        )
        assert any(r.to_state == to_state.value for r in rows)

    def test_same_state_is_no_op(self, db_session) -> None:
        lead, actor = self._make_lead(db_session)

        updated = LeadService.transition_lead(
            db_session,
            lead_id=lead.id,
            to_state=LeadState.PENDING,
            actor=actor,
        )

        assert updated.state == LeadState.PENDING.value
        history_rows = list(
            db_session.scalars(
                select(LeadStateHistory).where(LeadStateHistory.lead_id == lead.id)
            )
        )
        assert history_rows == []

    def test_invalid_transition_raises_400(self, db_session) -> None:
        lead, actor = self._make_lead(db_session)

        with pytest.raises(HTTPException) as exc_info:
            LeadService.transition_lead(
                db_session,
                lead_id=lead.id,
                to_state=LeadState.CLOSED,
                actor=actor,
            )

        assert exc_info.value.status_code == 400


class TestTokenErrors:
    @patch("src.domains.lead.service.EmailService.send_verification_email")
    def test_expired_token(self, mock_send, db_session, uploads_dir) -> None:
        mock_send.return_value = None
        _seed_default_attorney(db_session)

        LeadService.request_verification(
            db_session,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            resume=_make_upload(),
        )
        pending = db_session.scalar(select(LeadIntakePending))
        assert pending is not None
        pending.expires_at = datetime.now(UTC) - timedelta(hours=1)
        db_session.commit()

        raw_token = mock_send.call_args.kwargs["token"]
        with pytest.raises(HTTPException) as exc_info:
            LeadService.verify_and_create_lead(db_session, token=raw_token)

        assert exc_info.value.status_code == 410

    @patch("src.domains.lead.service.EmailService.send_verification_email")
    @patch("src.domains.lead.service.EmailService.send_lead_created_notifications")
    def test_used_token(
        self,
        mock_created,
        mock_send,
        db_session,
        uploads_dir,
    ) -> None:
        mock_send.return_value = None
        mock_created.return_value = None
        _seed_default_attorney(db_session)

        LeadService.request_verification(
            db_session,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            resume=_make_upload(),
        )
        raw_token = mock_send.call_args.kwargs["token"]
        LeadService.verify_and_create_lead(db_session, token=raw_token)

        with pytest.raises(HTTPException) as exc_info:
            LeadService.verify_and_create_lead(db_session, token=raw_token)

        assert exc_info.value.status_code == 409

    def test_unknown_token(self, db_session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            LeadService.verify_and_create_lead(db_session, token="unknown-token")

        assert exc_info.value.status_code == 404
