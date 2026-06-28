"""FastAPI router — P1 GetProspect, P2 ListProspectLeads.

Spec: docs/entities/prospect.md. Both routes require ``read_prospect`` and
404 only when the prospect_id has no matching row. ``ProspectLeadItem``
exposes ``archived_at`` so the UI can render archived rows distinctly
without dropping them (D3).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.deps import get_db, require_permission
from src.domains.prospect.schemas import ProspectLeadItem, ProspectRead
from src.domains.prospect.service import ProspectService

router = APIRouter(prefix="/api/v1/prospects", tags=["prospects"])


@router.get(
    "/{prospect_id}",
    response_model=ProspectRead,
    summary="GetProspect (P1)",
)
def get_prospect(
    prospect_id: UUID,
    db: Session = Depends(get_db),
    _account: Any = Depends(require_permission("read_prospect")),
) -> ProspectRead:
    prospect = ProspectService.get_prospect(db, prospect_id)
    if prospect is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prospect not found")

    leads = ProspectService.list_leads_for_prospect(db, prospect_id)
    return ProspectRead(
        id=prospect.id,
        email=prospect.email,
        first_name=prospect.first_name,
        last_name=prospect.last_name,
        lead_count=len(leads),
        created_at=prospect.created_at,
        updated_at=prospect.updated_at,
    )


@router.get(
    "/{prospect_id}/leads",
    response_model=list[ProspectLeadItem],
    summary="ListProspectLeads (P2)",
)
def list_prospect_leads(
    prospect_id: UUID,
    db: Session = Depends(get_db),
    _account: Any = Depends(require_permission("read_prospect")),
) -> list[ProspectLeadItem]:
    if ProspectService.get_prospect(db, prospect_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="prospect not found")

    leads = ProspectService.list_leads_for_prospect(db, prospect_id)
    return [ProspectLeadItem.model_validate(lead) for lead in leads]
