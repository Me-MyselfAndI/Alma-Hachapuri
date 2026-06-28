"""HTTP route tests for lead endpoints with real RBAC."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.core.permissions import Role
from src.domains.account.schemas import AccountCreate
from src.domains.account.service import AccountService
from src.domains.lead.models import Lead
from src.domains.lead.preconditions import LeadState
from src.domains.prospect.models import Prospect
from src.domains.resume_file.models import ResumeFile
from tst.shared.doc_fixtures import seed_lead as _seed_lead_any

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


class TestLeadRouteRbac:
    def test_attorney_cannot_transition_unassigned_lead(self, role_client, db_session) -> None:
        _, owner = role_client(Role.ATTORNEY, email="owner@firm.com")
        client, _other = role_client(
            Role.ATTORNEY,
            email="other@firm.com",
            is_default_assignee=False,
        )
        lead = _seed_lead(db_session, assignee_id=owner.id)

        response = client.post(
            f"/api/v1/leads/{lead.id}/transitions",
            json={"to_state": LeadState.REACHED_OUT.value},
        )

        assert response.status_code == 403

    def test_attorney_can_transition_own_lead(self, role_client, db_session) -> None:
        client, attorney = role_client(Role.ATTORNEY, email="owner@firm.com")
        lead = _seed_lead(db_session, assignee_id=attorney.id)

        response = client.post(
            f"/api/v1/leads/{lead.id}/transitions",
            json={"to_state": LeadState.REACHED_OUT.value},
        )

        assert response.status_code == 200
        assert response.json()["state"] == LeadState.REACHED_OUT.value

    def test_admin_can_transition_any_lead(self, role_client, db_session) -> None:
        _, attorney = role_client(
            Role.ATTORNEY,
            email="owner@firm.com",
        )
        admin_client, _admin = role_client(Role.ADMIN, email="admin@firm.com")
        lead = _seed_lead(db_session, assignee_id=attorney.id)

        response = admin_client.post(
            f"/api/v1/leads/{lead.id}/transitions",
            json={"to_state": LeadState.REACHED_OUT.value},
        )

        assert response.status_code == 200

    def test_readonly_cannot_transition(self, role_client, db_session) -> None:
        _, attorney = role_client(Role.ATTORNEY, email="owner@firm.com")
        client, _readonly = role_client(Role.READONLY, email="readonly@firm.com")
        lead = _seed_lead(db_session, assignee_id=attorney.id)

        response = client.post(
            f"/api/v1/leads/{lead.id}/transitions",
            json={"to_state": LeadState.REACHED_OUT.value},
        )

        assert response.status_code == 403


class TestLeadAssigneesAndReassignment:
    def test_list_assignable_requires_assign_lead(self, role_client) -> None:
        attorney_client, _ = role_client(Role.ATTORNEY, email="attorney@firm.com")

        response = attorney_client.get("/api/v1/accounts?for_assignment=true")

        assert response.status_code == 403

    def test_admin_lists_assignable_accounts(self, role_client) -> None:
        _, first = role_client(
            Role.ATTORNEY,
            email="first@firm.com",
            is_default_assignee=True,
        )
        role_client(
            Role.ATTORNEY,
            email="second@firm.com",
            is_default_assignee=False,
        )
        admin_client, _ = role_client(Role.ADMIN, email="admin@firm.com")

        response = admin_client.get("/api/v1/accounts?for_assignment=true")

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) >= 2
        ids = {item["id"] for item in body["items"]}
        assert str(first.id) in ids

    def test_admin_can_reassign_lead(self, role_client, db_session) -> None:
        _, first = role_client(
            Role.ATTORNEY,
            email="first@firm.com",
            is_default_assignee=True,
        )
        _, second = role_client(
            Role.ATTORNEY,
            email="second@firm.com",
            is_default_assignee=False,
        )
        admin_client, _ = role_client(Role.ADMIN, email="admin@firm.com")
        lead = _seed_lead(db_session, assignee_id=first.id)

        response = admin_client.patch(
            f"/api/v1/leads/{lead.id}",
            json={"assigned_account_id": str(second.id)},
        )

        assert response.status_code == 200
        assert response.json()["assigned_account_id"] == str(second.id)

        refreshed = db_session.get(Lead, lead.id)
        assert refreshed is not None
        assert refreshed.assigned_account_id == second.id

    def test_attorney_cannot_list_all_accounts(self, role_client) -> None:
        attorney_client, _ = role_client(
            Role.ATTORNEY,
            email="attorney@firm.com",
        )

        response = attorney_client.get("/api/v1/accounts?page_size=100")

        assert response.status_code == 403

    def test_intake_cannot_reassign_lead(self, role_client, db_session) -> None:
        _, first = role_client(
            Role.ATTORNEY,
            email="first@firm.com",
            is_default_assignee=True,
        )
        _, second = role_client(
            Role.ATTORNEY,
            email="second@firm.com",
            is_default_assignee=False,
        )
        intake_client, _ = role_client(
            Role.INTAKE_COORDINATOR,
            email="intake@firm.com",
        )
        lead = _seed_lead(db_session, assignee_id=first.id)

        response = intake_client.patch(
            f"/api/v1/leads/{lead.id}",
            json={"assigned_account_id": str(second.id)},
        )

        assert response.status_code == 403


class TestVerificationRequestRateLimit:
    @patch("src.domains.lead.service.EmailService.send_verification_email")
    def test_exceeding_limit_returns_429(self, mock_send, client, monkeypatch) -> None:
        mock_send.return_value = None
        from src.core.rate_limit import limiter

        monkeypatch.setattr("src.core.config.settings.rate_limit_enabled", True)
        monkeypatch.setattr("src.core.config.settings.verification_request_rate_limit", "2/minute")
        limiter.enabled = True

        payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
        }
        files = {"resume": ("cv.pdf", b"%PDF-1.4", "application/pdf")}

        assert client.post("/api/v1/leads/verification-requests", data=payload, files=files).status_code == 202
        assert client.post("/api/v1/leads/verification-requests", data=payload, files=files).status_code == 202
        response = client.post("/api/v1/leads/verification-requests", data=payload, files=files)

        assert response.status_code == 429
        limiter.enabled = False


class TestVerificationRequestRoute:
    def test_invalid_email_returns_422(self, client) -> None:
        response = client.post(
            "/api/v1/leads/verification-requests",
            data={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "not-an-email",
            },
            files={"resume": ("cv.pdf", b"%PDF-1.4", "application/pdf")},
        )

        assert response.status_code == 422

    def test_empty_first_name_returns_422(self, client) -> None:
        response = client.post(
            "/api/v1/leads/verification-requests",
            data={
                "first_name": "   ",
                "last_name": "Doe",
                "email": "jane@example.com",
            },
            files={"resume": ("cv.pdf", b"%PDF-1.4", "application/pdf")},
        )

        assert response.status_code == 422


class TestExportRoute:
    def test_export_includes_archived_and_state_changed_columns(
        self, role_client, db_session
    ) -> None:
        _, attorney = role_client(Role.ATTORNEY, email="owner@firm.com")
        admin_client, _admin = role_client(Role.ADMIN, email="admin@firm.com")
        _seed_lead(db_session, assignee_id=attorney.id)

        response = admin_client.get("/api/v1/leads/export")

        assert response.status_code == 200
        lines = response.text.strip().splitlines()
        header = lines[0]
        assert "state_changed_at" in header
        assert "archived_at" in header
        assert response.headers.get("X-Export-Total-Count") == "1"


class TestGetLeadFailures:
    def test_get_lead_404_when_missing(self, client) -> None:
        response = client.get(f"/api/v1/leads/{uuid.uuid4()}")
        assert response.status_code == 404


class TestVerifyLeadFailures:
    def test_verify_get_400_missing_token(self, client) -> None:
        response = client.get("/api/v1/leads/verify")
        assert response.status_code == 400

    def test_verify_get_404_unknown_token(self, client) -> None:
        response = client.get("/api/v1/leads/verify?token=totally-unknown-token")
        assert response.status_code == 404


class TestUpdateLeadFailures:
    def test_update_lead_404_when_missing(self, client) -> None:
        response = client.patch(
            f"/api/v1/leads/{uuid.uuid4()}",
            json={"state": LeadState.REACHED_OUT.value},
        )
        assert response.status_code == 404

    def test_update_lead_400_invalid_transition(self, client, db_session) -> None:
        lead = _seed_lead_any(db_session)
        response = client.patch(
            f"/api/v1/leads/{lead.id}",
            json={"state": LeadState.CLOSED.value},
        )
        assert response.status_code == 400

    def test_attorney_patch_unassigned_lead_403(self, role_client, db_session) -> None:
        _, owner = role_client(Role.ATTORNEY, email="patch-owner@firm.com")
        client, _ = role_client(
            Role.ATTORNEY,
            email="patch-other@firm.com",
            is_default_assignee=False,
        )
        lead = _seed_lead(db_session, assignee_id=owner.id)

        response = client.patch(
            f"/api/v1/leads/{lead.id}",
            json={"state": LeadState.REACHED_OUT.value},
        )
        assert response.status_code == 403


class TestArchiveLeadFailures:
    def test_archive_lead_404_when_missing(self, client) -> None:
        response = client.delete(f"/api/v1/leads/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_attorney_archive_unassigned_lead_403(self, role_client, db_session) -> None:
        _, owner = role_client(Role.ATTORNEY, email="arch-owner@firm.com")
        client, _ = role_client(
            Role.ATTORNEY,
            email="arch-other@firm.com",
            is_default_assignee=False,
        )
        lead = _seed_lead(db_session, assignee_id=owner.id)

        response = client.delete(f"/api/v1/leads/{lead.id}")
        assert response.status_code == 403
