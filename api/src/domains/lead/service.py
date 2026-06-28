"""LeadService (S4, S5).

Enrichment (S8) lives in ``enrichment.py`` and is queued from the L1b router.

Spec: docs/entities/lead.md, docs/entities/API_CATALOG.md.
"""

from __future__ import annotations

import csv
import io
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.permissions import Role, account_has_permission
from src.domains.account.models import Account
from src.domains.account.service import AccountService
from src.domains.email.service import EmailDeliveryError, EmailService
from src.domains.lead.intake_claim import (
    VerifyClaimOutcome,
    claim_pending_for_verify,
    load_pending_for_verify,
    raise_for_claim_outcome,
    resolve_completed_lead,
)
from src.domains.lead.models import Lead, LeadIntakePending
from src.domains.lead.preconditions import (
    LeadState,
    is_valid_state_transition,
    normalize_email,
)
from src.domains.lead.schemas import (
    LeadListParams,
    LeadUpdate,
    LeadVerificationRequestResponse,
)
from src.domains.lead.tokens import hash_verification_token, ensure_utc
from src.domains.prospect.service import ProspectService
from src.domains.resume_file.service import (
    EXTENSION_BY_MIME,
    delete_orphan,
    promote_temp_to_permanent,
    save_temp_resume,
)
from src.domains.state_history.service import LeadStateHistoryService

logger = logging.getLogger(__name__)

_MIME_BY_EXTENSION = {ext: mime for mime, ext in EXTENSION_BY_MIME.items()}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    """Normalize SQLite-returned naive timestamps to UTC-aware."""

    return ensure_utc(dt)


def _temp_resume_metadata(storage_key: str) -> tuple[str, str, int]:
    """Derive filename, mime, and size from a temp storage key on disk."""

    from src.domains.resume_file.service import _resolve_path  # noqa: PLC0415

    path = _resolve_path(storage_key)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pending intake data invalid: temp resume file missing",
        )

    ext = path.suffix.lower()
    mime_type = _MIME_BY_EXTENSION.get(ext, "application/octet-stream")
    return path.name, mime_type, path.stat().st_size


def _invalidate_prior_pending(db: Session, *, email: str) -> None:
    """Mark unused pending rows for the same email as used and remove temp files."""

    stmt = select(LeadIntakePending).where(
        LeadIntakePending.email == email,
        LeadIntakePending.used_at.is_(None),
    )
    for row in db.scalars(stmt):
        delete_orphan(row.temp_resume_storage_key)
        row.used_at = _now_utc()
    db.flush()


class LeadService:
    """Lead lifecycle — intake, CRUD, transitions, export, archive."""

    @staticmethod
    def request_verification(
        db: Session,
        *,
        first_name: str,
        last_name: str,
        email: str,
        resume: UploadFile,
        source: str | None = None,
    ) -> LeadVerificationRequestResponse:
        """L1a — pending row + temp file + verification email; no lead."""

        normalized = normalize_email(email)
        temp_key: str | None = None

        try:
            temp_key = save_temp_resume(resume)
            _invalidate_prior_pending(db, email=normalized)

            raw_token = secrets.token_urlsafe(32)
            token_hash = hash_verification_token(raw_token)
            expires_at = _now_utc() + timedelta(hours=settings.verification_token_ttl_hours)

            pending = LeadIntakePending(
                email=normalized,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                source=source,
                temp_resume_storage_key=temp_key,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            db.add(pending)
            db.flush()

            EmailService.send_verification_email(
                db,
                pending_intake_id=pending.id,
                email=normalized,
                token=raw_token,
            )
            db.commit()
        except EmailDeliveryError as exc:
            db.rollback()
            if temp_key:
                delete_orphan(temp_key)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to send verification email",
            ) from exc
        except HTTPException:
            db.rollback()
            if temp_key:
                delete_orphan(temp_key)
            raise
        except Exception:
            db.rollback()
            if temp_key:
                delete_orphan(temp_key)
            raise

        return LeadVerificationRequestResponse(email=normalized)

    @staticmethod
    def verify_and_create_lead(db: Session, *, token: str) -> Lead:
        """L1b — validate token; orchestrate S1–S7; return Lead ORM."""

        if not token or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="token is required",
            )

        token_hash = hash_verification_token(token.strip())
        pending = load_pending_for_verify(db, token_hash=token_hash)
        claim = claim_pending_for_verify(db, pending=pending)

        if claim.outcome is VerifyClaimOutcome.ALREADY_COMPLETED:
            return resolve_completed_lead(db, pending=pending)

        raise_for_claim_outcome(claim)

        promoted_key: str | None = None
        try:
            original_filename, mime_type, size_bytes = _temp_resume_metadata(
                pending.temp_resume_storage_key
            )
            resume_file = promote_temp_to_permanent(
                db,
                temp_storage_key=pending.temp_resume_storage_key,
                original_filename=original_filename,
                mime_type=mime_type,
                size_bytes=size_bytes,
            )
            promoted_key = resume_file.storage_key

            lead = LeadService.create_lead(
                db,
                first_name=pending.first_name,
                last_name=pending.last_name,
                email=pending.email,
                resume_file_id=resume_file.id,
                source=pending.source,
            )

            pending.lead_id = lead.id
            db.commit()
            db.refresh(lead)
        except HTTPException:
            db.rollback()
            if promoted_key:
                delete_orphan(promoted_key)
            raise
        except Exception:
            db.rollback()
            if promoted_key:
                delete_orphan(promoted_key)
            raise

        try:
            EmailService.send_lead_created_notifications(db, lead=lead)
            db.commit()
        except Exception:
            logger.exception("S7 notifications failed for lead %s", lead.id)
            db.rollback()

        return lead

    @staticmethod
    def create_lead(
        db: Session,
        *,
        first_name: str,
        last_name: str,
        email: str,
        resume_file_id: UUID,
        source: str | None = None,
    ) -> Lead:
        """Internal orchestrator after resume promoted (L1b steps 3–7)."""

        normalized = normalize_email(email)
        prospect, _ = ProspectService.find_or_create_by_email(
            db,
            email=normalized,
            first_name=first_name,
            last_name=last_name,
        )
        assignee = AccountService.resolve_default_assignee(db)
        now = _now_utc()

        lead = Lead(
            prospect_id=prospect.id,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=normalized,
            resume_file_id=resume_file_id,
            state=LeadState.PENDING.value,
            state_changed_at=now,
            source=source,
            assigned_account_id=assignee.id,
        )
        db.add(lead)
        db.flush()

        LeadStateHistoryService.record_initial(db, lead_id=lead.id, to_state=LeadState.PENDING.value)
        return lead

    @staticmethod
    def get_lead(db: Session, lead_id: UUID) -> Lead | None:
        return db.get(Lead, lead_id)

    @staticmethod
    def list_leads(
        db: Session,
        *,
        params: LeadListParams,
        current_account_id: UUID | None = None,
    ) -> tuple[list[Lead], int]:
        base = select(Lead)
        count_q = select(func.count()).select_from(Lead)

        if not params.include_archived:
            base = base.where(Lead.archived_at.is_(None))
            count_q = count_q.where(Lead.archived_at.is_(None))

        if params.state is not None:
            state_val = (
                params.state.value
                if isinstance(params.state, LeadState)
                else params.state
            )
            base = base.where(Lead.state == state_val)
            count_q = count_q.where(Lead.state == state_val)

        assignee_filter = params.assigned_account_id
        if params.mine and current_account_id is not None:
            assignee_filter = current_account_id
        if assignee_filter is not None:
            base = base.where(Lead.assigned_account_id == assignee_filter)
            count_q = count_q.where(Lead.assigned_account_id == assignee_filter)

        total = int(db.scalar(count_q) or 0)
        stmt = (
            base.order_by(Lead.created_at.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
        items = list(db.scalars(stmt))
        return items, total

    @staticmethod
    def _assert_write_scope(lead: Lead, actor: Account) -> None:
        """Attorneys may only mutate leads assigned to them (F6.2)."""

        if actor.role == Role.ATTORNEY.value:
            if lead.assigned_account_id != actor.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

    @staticmethod
    def _assert_assign_permission(actor: Account) -> None:
        if not account_has_permission(actor, "assign_lead"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    @staticmethod
    def _apply_state_change(
        db: Session,
        *,
        lead: Lead,
        to_state: LeadState | str,
        actor: Account,
        note: str | None = None,
    ) -> None:
        to_val = to_state.value if isinstance(to_state, LeadState) else to_state
        from_val = lead.state

        if from_val == to_val:
            return

        if not is_valid_state_transition(from_val, to_val):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state transition from {from_val} to {to_val}",
            )

        LeadStateHistoryService.record_transition(
            db,
            lead_id=lead.id,
            from_state=from_val,
            to_state=to_val,
            changed_by=actor,
            note=note,
        )
        lead.state = to_val
        lead.state_changed_at = _now_utc()

    @staticmethod
    def update_lead(
        db: Session,
        *,
        lead_id: UUID,
        update: LeadUpdate,
        actor: Account,
    ) -> Lead:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found",
            )

        LeadService._assert_write_scope(lead, actor)

        if update.assigned_account_id is not None:
            LeadService._assert_assign_permission(actor)
            account = db.get(Account, update.assigned_account_id)
            if account is None or not account.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid assignee account",
                )
            if account.role not in (Role.ATTORNEY.value, Role.INTAKE_COORDINATOR.value):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Assignee must have an assignable role",
                )
            lead.assigned_account_id = update.assigned_account_id

        if update.state is not None:
            LeadService._apply_state_change(
                db,
                lead=lead,
                to_state=update.state,
                actor=actor,
            )

        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def transition_lead(
        db: Session,
        *,
        lead_id: UUID,
        to_state: LeadState,
        actor: Account,
        note: str | None = None,
    ) -> Lead:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found",
            )

        LeadService._assert_write_scope(lead, actor)
        LeadService._apply_state_change(
            db,
            lead=lead,
            to_state=to_state,
            actor=actor,
            note=note,
        )
        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def export_leads_csv(
        db: Session,
        *,
        params: LeadListParams,
        current_account_id: UUID | None = None,
    ) -> str:
        export_params = params.model_copy(update={"page": 1, "page_size": 10_000})
        items, _ = LeadService.list_leads(
            db,
            params=export_params,
            current_account_id=current_account_id,
        )

        assignee_ids = {lead.assigned_account_id for lead in items if lead.assigned_account_id}
        assignees: dict[UUID, Account] = {}
        if assignee_ids:
            for account in db.scalars(select(Account).where(Account.id.in_(assignee_ids))):
                assignees[account.id] = account

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["id", "first_name", "last_name", "email", "state", "source", "assignee", "created_at"]
        )
        for lead in items:
            assignee_name = ""
            if lead.assigned_account_id and lead.assigned_account_id in assignees:
                acc = assignees[lead.assigned_account_id]
                assignee_name = f"{acc.first_name} {acc.last_name}"
            writer.writerow(
                [
                    str(lead.id),
                    lead.first_name,
                    lead.last_name,
                    lead.email,
                    lead.state,
                    lead.source or "",
                    assignee_name,
                    lead.created_at.isoformat(),
                ]
            )
        return buffer.getvalue()

    @staticmethod
    def archive_lead(db: Session, *, lead_id: UUID, actor: Account) -> None:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found",
            )

        LeadService._assert_write_scope(lead, actor)

        if lead.archived_at is None:
            lead.archived_at = _now_utc()

        db.commit()
