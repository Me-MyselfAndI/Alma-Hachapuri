"""FastAPI router — L7 GetLeadStateHistory.

Mounted from ``src/main.py`` under ``/api/v1/leads/{lead_id}/state-history`` so
the lead-id path parameter is declared once at the mount point (same pattern as
``resume_file.router``). This module's router has **no prefix** of its own.

Permission: ``read_leads``. D3 — archived leads remain readable; 404 only when
the lead id does not exist.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.deps import get_db, require_permission
from src.domains.account.models import Account
from src.domains.lead.models import Lead
from src.domains.state_history.schemas import LeadStateHistoryRead, history_row_to_read
from src.domains.state_history.service import LeadStateHistoryService

router = APIRouter(tags=["state-history"])


@router.get(
    "",
    response_model=list[LeadStateHistoryRead],
    summary="GetLeadStateHistory (L7)",
)
def get_lead_state_history(
    lead_id: uuid.UUID = Path(..., description="Lead whose state history to list."),
    db: Session = Depends(get_db),
    _account: Any = Depends(require_permission("read_leads")),
) -> list[LeadStateHistoryRead]:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    rows = LeadStateHistoryService.list_for_lead(db, lead_id)

    account_ids = {
        row.changed_by_account_id for row in rows if row.changed_by_account_id is not None
    }
    email_by_id: dict[uuid.UUID, str] = {}
    if account_ids:
        accounts = db.scalars(select(Account).where(Account.id.in_(account_ids)))
        email_by_id = {account.id: account.email for account in accounts}

    return [
        history_row_to_read(
            row,
            changed_by_email=(
                email_by_id.get(row.changed_by_account_id)
                if row.changed_by_account_id is not None
                else None
            ),
        )
        for row in rows
    ]
