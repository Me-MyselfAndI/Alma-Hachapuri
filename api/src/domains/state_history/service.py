"""LeadStateHistoryService — S6.

Spec: docs/entities/lead-state-history.md.

Append-only audit rows for lead lifecycle changes. ``record_initial`` and
``record_transition`` are called from lead orchestration (L1b, L4, L10); L7
exposes ``list_for_lead`` over HTTP.

D8: when ``from_state == to_state``, ``record_transition`` returns ``None``
(no row inserted) so callers can skip the call or rely on the no-op.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domains.account.models import Account
from src.domains.lead.models import Lead
from src.domains.state_history.models import LeadStateHistory
from src.domains.state_history.preconditions import (
    check_record_initial,
    check_record_state_change,
)


class LeadStateHistoryService:
    """Stateless namespace for lead state history (S6)."""

    @staticmethod
    def record_initial(
        db: Session,
        *,
        lead_id: UUID,
        to_state: str = "PENDING",
    ) -> LeadStateHistory:
        """Insert the system row on lead create: ``from_state`` and actor both null."""

        lead_exists = db.get(Lead, lead_id) is not None
        err = check_record_initial(
            lead_exists=lead_exists,
            from_state=None,
            to_state=to_state,
            changed_by_account_id=None,
        )
        if err is not None:
            raise ValueError(err.value)

        row = LeadStateHistory(
            lead_id=lead_id,
            from_state=None,
            to_state=to_state,
            changed_by_account_id=None,
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def record_transition(
        db: Session,
        *,
        lead_id: UUID,
        from_state: str,
        to_state: str,
        changed_by: Account,
        note: str | None = None,
    ) -> LeadStateHistory | None:
        """Append an immutable transition row.

        Returns ``None`` without inserting when ``from_state == to_state`` (D8).
        Raises ``ValueError`` when preconditions fail (invalid transition, missing
        lead, etc.) — HTTP callers map that to 400 at the lead route boundary.
        """

        if from_state == to_state:
            return None

        lead_exists = db.get(Lead, lead_id) is not None
        err = check_record_state_change(
            lead_exists=lead_exists,
            from_state=from_state,
            to_state=to_state,
            changed_by_account_id=changed_by.id,
        )
        if err is not None:
            raise ValueError(err.value)

        row = LeadStateHistory(
            lead_id=lead_id,
            from_state=from_state,
            to_state=to_state,
            changed_by_account_id=changed_by.id,
            note=note,
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def list_for_lead(db: Session, lead_id: UUID) -> list[LeadStateHistory]:
        """All history rows for the lead, oldest first."""

        stmt = (
            select(LeadStateHistory)
            .where(LeadStateHistory.lead_id == lead_id)
            .order_by(LeadStateHistory.created_at.asc())
        )
        return list(db.scalars(stmt))
