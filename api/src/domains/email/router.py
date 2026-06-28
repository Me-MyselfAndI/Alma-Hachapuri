"""FastAPI routers — L6, E1–E4, E6.

Spec: docs/entities/email-notification.md.

Two routers (mount from ``src/main.py`` in a later slice):

* ``emails_router`` — ``/api/v1/emails`` (E1, E3, E4, E6)
* ``lead_emails_router`` — ``/api/v1/leads/{lead_id}/emails`` (L6, E2)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core.deps import get_db, require_any_permission, require_permission
from src.domains.email.preconditions import lead_emails_accessible
from src.domains.email.schemas import (
    EmailNotificationRead,
    EmailSendRequest,
    EmailTemplateInfo,
    Paginated,
)
from src.domains.email.service import EmailService
from src.domains.lead.models import Lead


emails_router = APIRouter(prefix="/api/v1/emails", tags=["emails"])
lead_emails_router = APIRouter(prefix="/api/v1/leads", tags=["emails"])


def _to_read(notification) -> EmailNotificationRead:
    return EmailNotificationRead.model_validate(notification)


@lead_emails_router.get(
    "/{lead_id}/emails",
    response_model=list[EmailNotificationRead],
    summary="ListLeadEmails (L6)",
)
def list_lead_emails(
    lead_id: UUID,
    conversation_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    _account: Any = Depends(require_permission("read_emails")),
) -> list[EmailNotificationRead]:
    lead = db.get(Lead, lead_id)
    if not lead_emails_accessible(lead_exists=lead is not None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    items = EmailService.list_for_lead(
        db, lead_id, conversation_id=conversation_id
    )
    return [_to_read(item) for item in items]


@lead_emails_router.post(
    "/{lead_id}/emails",
    response_model=EmailNotificationRead,
    status_code=status.HTTP_201_CREATED,
    summary="SendStaffEmail (E2)",
)
def send_staff_email(
    lead_id: UUID,
    body: EmailSendRequest,
    db: Session = Depends(get_db),
    _account: Any = Depends(require_permission("send_email")),
) -> EmailNotificationRead:
    notification = EmailService.send_template(
        db,
        lead_id=lead_id,
        template=body.template,
        recipient=body.recipient,
        conversation_id=body.conversation_id,
    )
    db.commit()
    db.refresh(notification)
    return _to_read(notification)


@emails_router.get(
    "/templates",
    response_model=list[EmailTemplateInfo],
    summary="ListEmailTemplates (E6)",
)
def list_email_templates(
    _account: Any = Depends(require_any_permission("send_email", "read_emails")),
) -> list[EmailTemplateInfo]:
    return [EmailTemplateInfo(**item) for item in EmailService.list_templates()]


@emails_router.get(
    "",
    response_model=Paginated[EmailNotificationRead],
    summary="ListAllEmails (E4)",
)
def list_all_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    template: str | None = Query(None),
    conversation_id: UUID | None = Query(None),
    lead_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    _account: Any = Depends(require_any_permission("read_emails", "manage_users")),
) -> Paginated[EmailNotificationRead]:
    items, total = EmailService.list_all(
        db,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        template=template,
        conversation_id=conversation_id,
        lead_id=lead_id,
    )
    return Paginated[EmailNotificationRead](
        items=[_to_read(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@emails_router.get(
    "/{email_id}",
    response_model=EmailNotificationRead,
    summary="GetEmailNotification (E1)",
)
def get_email_notification(
    email_id: UUID,
    db: Session = Depends(get_db),
    _account: Any = Depends(require_permission("read_emails")),
) -> EmailNotificationRead:
    notification = EmailService.get_by_id(db, email_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email notification not found",
        )

    if notification.lead_id is not None:
        lead = db.get(Lead, notification.lead_id)
        if lead is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found",
            )

    return _to_read(notification)


@emails_router.post(
    "/{email_id}/retry",
    response_model=EmailNotificationRead,
    summary="RetryFailedEmail (E3)",
)
def retry_failed_email(
    email_id: UUID,
    db: Session = Depends(get_db),
    _account: Any = Depends(require_permission("send_email")),
) -> EmailNotificationRead:
    notification = EmailService.retry_failed(db, email_id)
    db.commit()
    db.refresh(notification)
    return _to_read(notification)
