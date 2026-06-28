"""Unit tests for L1b pending-intake claim logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.core.config import settings
from src.domains.lead.intake_claim import (
    VerifyClaimOutcome,
    VerifyClaimResult,
    claim_pending_for_verify,
    raise_for_claim_outcome,
)
from src.domains.lead.models import LeadIntakePending

UTC = timezone.utc


def _pending(**overrides) -> LeadIntakePending:
    now = datetime.now(UTC)
    defaults = {
        "email": "jane@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "temp_resume_storage_key": "temp/x.pdf",
        "token_hash": "abc",
        "expires_at": now + timedelta(hours=24),
        "used_at": None,
        "lead_id": None,
    }
    defaults.update(overrides)
    return LeadIntakePending(**defaults)


class TestClaimPendingForVerify:
    def test_claims_fresh_pending(self, db_session) -> None:
        pending = _pending()
        db_session.add(pending)
        db_session.flush()

        now = datetime.now(UTC)
        result = claim_pending_for_verify(db_session, pending=pending, now=now)

        assert result.outcome is VerifyClaimOutcome.CLAIMED
        assert pending.used_at == now

    def test_completed_pending(self, db_session) -> None:
        lead_id = uuid4()
        pending = _pending(lead_id=lead_id, used_at=datetime.now(UTC))
        db_session.add(pending)
        db_session.flush()

        result = claim_pending_for_verify(db_session, pending=pending)

        assert result.outcome is VerifyClaimOutcome.ALREADY_COMPLETED

    def test_in_progress_within_stale_window(self, db_session) -> None:
        pending = _pending(used_at=datetime.now(UTC) - timedelta(minutes=1))
        db_session.add(pending)
        db_session.flush()

        result = claim_pending_for_verify(db_session, pending=pending)

        assert result.outcome is VerifyClaimOutcome.IN_PROGRESS

    def test_stale_reclaim(self, db_session, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "verification_processing_stale_minutes", 5)
        stale = datetime.now(UTC) - timedelta(minutes=10)
        pending = _pending(used_at=stale)
        db_session.add(pending)
        db_session.flush()

        now = datetime.now(UTC)
        result = claim_pending_for_verify(db_session, pending=pending, now=now)

        assert result.outcome is VerifyClaimOutcome.STALE_RECLAIMED
        assert pending.used_at == now

    def test_expired_link(self, db_session) -> None:
        pending = _pending(expires_at=datetime.now(UTC) - timedelta(hours=1))
        db_session.add(pending)
        db_session.flush()

        result = claim_pending_for_verify(db_session, pending=pending)

        assert result.outcome is VerifyClaimOutcome.EXPIRED


class TestRaiseForClaimOutcome:
    def test_in_progress_raises_409(self) -> None:
        pending = _pending(used_at=datetime.now(UTC))
        with pytest.raises(HTTPException) as exc:
            raise_for_claim_outcome(
                VerifyClaimResult(VerifyClaimOutcome.IN_PROGRESS, pending)
            )
        assert exc.value.status_code == 409
