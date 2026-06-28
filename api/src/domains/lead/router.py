"""FastAPI router — L1a, L1b, L2–L4, L10, L13, L14.

Spec: docs/entities/lead.md. Sub-routes L5/L6/L7 are mounted from other packages.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.deps import get_db, require_permission
from src.core.rate_limit import limiter
from src.domains.account.models import Account
from src.domains.account.schemas import Paginated
from src.domains.lead.enrichment import schedule_lead_enrichment
from src.domains.lead.models import Lead
from src.domains.lead.preconditions import LeadState
from src.domains.lead.schemas import (
    AssignedAccountSummary,
    LeadCreateResponse,
    LeadListItem,
    LeadListParams,
    LeadRead,
    LeadResumeSummary,
    LeadTransitionRequest,
    LeadUpdate,
    LeadVerificationRequestResponse,
    LeadVerifyRequest,
)
from src.domains.lead.service import LeadService
from src.domains.prospect.models import Prospect
from src.domains.prospect.schemas import ProspectSummary
from src.domains.resume_file.models import ResumeFile

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


def _verification_request_rate_limit() -> str:
    return settings.verification_request_rate_limit


def _build_lead_read(db: Session, lead: Lead) -> LeadRead:
    prospect = db.get(Prospect, lead.prospect_id)
    resume = db.get(ResumeFile, lead.resume_file_id)
    assignee = (
        db.get(Account, lead.assigned_account_id) if lead.assigned_account_id else None
    )

    resume_summary = None
    if resume is not None:
        resume_summary = LeadResumeSummary(
            id=resume.id,
            original_filename=resume.original_filename,
            mime_type=resume.mime_type,
            size_bytes=resume.size_bytes,
            download_url=f"/api/v1/leads/{lead.id}/resume",
        )

    assignee_summary = None
    if assignee is not None:
        assignee_summary = AssignedAccountSummary(
            id=assignee.id,
            first_name=assignee.first_name,
            last_name=assignee.last_name,
            work_email=assignee.work_email,
            email=assignee.email,
        )

    prospect_summary = None
    if prospect is not None:
        prospect_summary = ProspectSummary.model_validate(prospect)

    return LeadRead(
        id=lead.id,
        prospect_id=lead.prospect_id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        state=LeadState(lead.state),
        state_changed_at=lead.state_changed_at,
        source=lead.source,
        custom_fields=lead.custom_fields,
        assigned_account_id=lead.assigned_account_id,
        assigned_account=assignee_summary,
        resume=resume_summary,
        prospect=prospect_summary,
        archived_at=lead.archived_at,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


def _assignee_name_map(db: Session, leads: list[Lead]) -> dict[UUID, str]:
    """Batch-load assignee display names for list/export rows."""

    assignee_ids = {lead.assigned_account_id for lead in leads if lead.assigned_account_id}
    if not assignee_ids:
        return {}

    accounts = db.scalars(select(Account).where(Account.id.in_(assignee_ids)))
    return {
        account.id: f"{account.first_name} {account.last_name}"
        for account in accounts
    }


def _build_list_item(lead: Lead, assignee_names: dict[UUID, str]) -> LeadListItem:
    assignee_name = None
    if lead.assigned_account_id:
        assignee_name = assignee_names.get(lead.assigned_account_id)

    return LeadListItem(
        id=lead.id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        state=LeadState(lead.state),
        state_changed_at=lead.state_changed_at,
        source=lead.source,
        assigned_account_id=lead.assigned_account_id,
        assigned_account_name=assignee_name,
        archived_at=lead.archived_at,
        created_at=lead.created_at,
    )


# ---------------------------------------------------------------------------
# Public intake (L1a, L1b)
# ---------------------------------------------------------------------------


@router.post(
    "/verification-requests",
    response_model=LeadVerificationRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="RequestLeadVerification (L1a)",
)
@limiter.limit(_verification_request_rate_limit)
def request_lead_verification(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
    source: str | None = Form(None),
    db: Session = Depends(get_db),
) -> LeadVerificationRequestResponse:
    return LeadService.request_verification(
        db,
        first_name=first_name,
        last_name=last_name,
        email=email,
        resume=resume,
        source=source,
    )


@router.get(
    "/verify",
    response_model=LeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="VerifyEmailAndCreateLead (L1b — email link)",
)
def verify_lead_get(
    background_tasks: BackgroundTasks,
    token: str | None = Query(None),
    db: Session = Depends(get_db),
) -> LeadCreateResponse:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token is required",
        )
    lead = LeadService.verify_and_create_lead(db, token=token)
    if settings.enable_llm_enrichment:
        background_tasks.add_task(schedule_lead_enrichment, lead.id)
    return LeadCreateResponse(id=lead.id, state=LeadState(lead.state))


@router.post(
    "/verify",
    response_model=LeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="VerifyEmailAndCreateLead (L1b — SPA)",
)
def verify_lead_post(
    body: LeadVerifyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> LeadCreateResponse:
    lead = LeadService.verify_and_create_lead(db, token=body.token)
    if settings.enable_llm_enrichment:
        background_tasks.add_task(schedule_lead_enrichment, lead.id)
    return LeadCreateResponse(id=lead.id, state=LeadState(lead.state))


# ---------------------------------------------------------------------------
# Internal routes — register /export before /{lead_id}
# ---------------------------------------------------------------------------


@router.get(
    "/export",
    summary="ExportLeads (L13)",
    responses={200: {"content": {"text/csv": {}}}},
)
def export_leads(
    state: LeadState | None = Query(None),
    assigned_account_id: UUID | None = Query(None),
    mine: bool = Query(False),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    account: Account = Depends(require_permission("export_leads")),
) -> Response:
    params = LeadListParams(
        state=state,
        assigned_account_id=assigned_account_id,
        mine=mine,
        include_archived=include_archived,
    )
    csv_data, total, truncated = LeadService.export_leads_csv(
        db,
        params=params,
        current_account_id=account.id,
    )
    headers: dict[str, str] = {
        "Content-Disposition": 'attachment; filename="leads.csv"',
        "X-Export-Total-Count": str(total),
    }
    if truncated:
        headers["X-Export-Truncated"] = "true"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers=headers,
    )


@router.get(
    "",
    response_model=Paginated[LeadListItem],
    summary="ListLeads (L2)",
)
def list_leads(
    state: LeadState | None = Query(None),
    assigned_account_id: UUID | None = Query(None),
    mine: bool = Query(False),
    include_archived: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    account: Account = Depends(require_permission("read_leads")),
) -> Paginated[LeadListItem]:
    params = LeadListParams(
        state=state,
        assigned_account_id=assigned_account_id,
        mine=mine,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    items, total = LeadService.list_leads(
        db,
        params=params,
        current_account_id=account.id,
    )
    assignee_names = _assignee_name_map(db, items)
    return Paginated[LeadListItem](
        items=[_build_list_item(lead, assignee_names) for lead in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{lead_id}",
    response_model=LeadRead,
    summary="GetLead (L3)",
)
def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    _account: Any = Depends(require_permission("read_leads")),
) -> LeadRead:
    lead = LeadService.get_lead(db, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return _build_lead_read(db, lead)


@router.patch(
    "/{lead_id}",
    response_model=LeadRead,
    summary="UpdateLead (L4)",
)
def update_lead(
    lead_id: UUID,
    body: LeadUpdate,
    db: Session = Depends(get_db),
    account: Account = Depends(require_permission("write_lead")),
) -> LeadRead:
    if body.assigned_account_id is not None:
        from src.core.permissions import account_has_permission

        if not account_has_permission(account, "assign_lead"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    lead = LeadService.update_lead(db, lead_id=lead_id, update=body, actor=account)
    return _build_lead_read(db, lead)


@router.post(
    "/{lead_id}/transitions",
    response_model=LeadRead,
    summary="TransitionLead (L10)",
)
def transition_lead(
    lead_id: UUID,
    body: LeadTransitionRequest,
    db: Session = Depends(get_db),
    account: Account = Depends(require_permission("write_lead")),
) -> LeadRead:
    lead = LeadService.transition_lead(
        db,
        lead_id=lead_id,
        to_state=body.to_state,
        actor=account,
        note=body.note,
    )
    return _build_lead_read(db, lead)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="ArchiveLead (L14)",
)
def archive_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    account: Account = Depends(require_permission("write_lead")),
) -> Response:
    LeadService.archive_lead(db, lead_id=lead_id, actor=account)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
