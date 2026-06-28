"""EmailService — S7a, S7, template render, conversation threading.

Spec: docs/entities/email-notification.md.
"""

from __future__ import annotations

import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.config import settings
from src.domains.account.models import Account
from src.domains.email.models import EmailNotification
from src.domains.email.preconditions import (
    EmailStatus,
    can_retry_failed_send,
    pick_conversation_id,
)
from src.domains.lead.models import Lead, LeadIntakePending


logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """SMTP send failed — S7a callers roll back on this."""


class EmailService:
    """Stateless namespace for outbound email operations."""

    TEMPLATE_CATALOG: dict[str, dict[str, str]] = {
        "email_verification": {
            "description": "Verify email before lead creation",
            "default_recipient": "pending_intake",
        },
        "prospect_confirmation": {
            "description": "Acknowledge lead submission",
            "default_recipient": "prospect",
        },
        "attorney_new_lead": {
            "description": "Notify assigned attorney of new lead",
            "default_recipient": "assigned_attorney",
        },
        "prospect_follow_up": {
            "description": "Staff follow-up to prospect",
            "default_recipient": "prospect",
        },
    }

    STAFF_TEMPLATES: frozenset[str] = frozenset(
        {"prospect_confirmation", "prospect_follow_up"}
    )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def render_template(template: str, context: dict[str, Any]) -> tuple[str, str]:
        """Return ``(subject, html_body)`` for a template key."""

        if template == "email_verification":
            first_name = context.get("first_name", "there")
            verify_url = context["verify_url"]
            expires_at = context.get("expires_at", "")
            subject = "Verify your email to complete your submission"
            html = (
                f"<p>Hi {first_name},</p>"
                f"<p>Please verify your email by clicking the link below:</p>"
                f'<p><a href="{verify_url}">Verify email</a></p>'
                f"<p>This link expires at {expires_at}.</p>"
            )
            return subject, html

        if template == "prospect_confirmation":
            first_name = context.get("first_name", "there")
            subject = "We received your submission"
            html = (
                f"<p>Hi {first_name},</p>"
                f"<p>Thank you — we received your submission and will be in touch soon.</p>"
            )
            return subject, html

        if template == "attorney_new_lead":
            prospect_name = context.get("prospect_name", "New prospect")
            lead_id = context.get("lead_id", "")
            lead_url = context.get("lead_url", "")
            subject = f"New lead: {prospect_name}"
            html = (
                f"<p>A new lead has been assigned to you.</p>"
                f"<p><strong>{prospect_name}</strong></p>"
                f'<p><a href="{lead_url}">View lead {lead_id}</a></p>'
            )
            return subject, html

        if template == "prospect_follow_up":
            first_name = context.get("first_name", "there")
            subject = "Follow-up on your submission"
            html = (
                f"<p>Hi {first_name},</p>"
                f"<p>We wanted to follow up regarding your recent submission.</p>"
            )
            return subject, html

        raise ValueError(f"Unknown email template: {template}")

    @staticmethod
    def _send_smtp(*, recipient: str, subject: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["To"] = recipient
        msg["From"] = f"noreply@{settings.smtp_host}"
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.send_message(msg)
        except smtplib.SMTPException as exc:
            raise EmailDeliveryError(str(exc)) from exc

    @staticmethod
    def _existing_conversation_id(
        db: Session, *, lead_id: UUID, recipient: str
    ) -> UUID | None:
        normalized = EmailService._normalize_email(recipient)
        return db.scalar(
            select(EmailNotification.conversation_id)
            .where(
                EmailNotification.lead_id == lead_id,
                EmailNotification.recipient == normalized,
            )
            .order_by(EmailNotification.created_at.asc())
            .limit(1)
        )

    @staticmethod
    def resolve_conversation_id(
        db: Session,
        *,
        lead_id: UUID,
        recipient: str,
        conversation_id: UUID | None = None,
    ) -> UUID:
        """Return existing thread id or create new UUID for first message in thread."""

        existing = EmailService._existing_conversation_id(
            db, lead_id=lead_id, recipient=recipient
        )
        return pick_conversation_id(
            provided=conversation_id,
            existing_for_lead_recipient=existing,
            new_id=uuid.uuid4(),
        )

    @staticmethod
    def list_by_conversation(
        db: Session, conversation_id: UUID
    ) -> list[EmailNotification]:
        stmt = (
            select(EmailNotification)
            .where(EmailNotification.conversation_id == conversation_id)
            .order_by(EmailNotification.created_at.asc())
        )
        return list(db.scalars(stmt))

    @staticmethod
    def get_by_id(db: Session, email_id: UUID) -> EmailNotification | None:
        return db.get(EmailNotification, email_id)

    @staticmethod
    def list_for_lead(
        db: Session,
        lead_id: UUID,
        *,
        conversation_id: UUID | None = None,
    ) -> list[EmailNotification]:
        stmt = select(EmailNotification).where(EmailNotification.lead_id == lead_id)
        if conversation_id is not None:
            stmt = stmt.where(EmailNotification.conversation_id == conversation_id)
        stmt = stmt.order_by(EmailNotification.created_at.desc())
        return list(db.scalars(stmt))

    @staticmethod
    def list_all(
        db: Session,
        *,
        page: int,
        page_size: int,
        status_filter: str | None = None,
        template: str | None = None,
        conversation_id: UUID | None = None,
        lead_id: UUID | None = None,
    ) -> tuple[list[EmailNotification], int]:
        base = select(EmailNotification)
        count_q = select(func.count()).select_from(EmailNotification)

        if status_filter is not None:
            base = base.where(EmailNotification.status == status_filter)
            count_q = count_q.where(EmailNotification.status == status_filter)
        if template is not None:
            base = base.where(EmailNotification.template == template)
            count_q = count_q.where(EmailNotification.template == template)
        if conversation_id is not None:
            base = base.where(EmailNotification.conversation_id == conversation_id)
            count_q = count_q.where(EmailNotification.conversation_id == conversation_id)
        if lead_id is not None:
            base = base.where(EmailNotification.lead_id == lead_id)
            count_q = count_q.where(EmailNotification.lead_id == lead_id)

        total = int(db.scalar(count_q) or 0)
        stmt = (
            base.order_by(EmailNotification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(db.scalars(stmt)), total

    @staticmethod
    def list_templates() -> list[dict[str, str]]:
        """E6 — staff-visible templates (excludes system-only keys)."""

        return [
            {
                "key": key,
                "description": meta["description"],
                "default_recipient": meta["default_recipient"],
            }
            for key, meta in EmailService.TEMPLATE_CATALOG.items()
            if key in EmailService.STAFF_TEMPLATES
        ]

    @staticmethod
    def _resolve_recipient_for_lead(
        db: Session,
        *,
        lead: Lead,
        template: str,
        recipient: str | None,
    ) -> str:
        if recipient is not None:
            return EmailService._normalize_email(recipient)

        default_kind = EmailService.TEMPLATE_CATALOG[template]["default_recipient"]
        if default_kind == "prospect":
            return lead.email
        if default_kind == "assigned_attorney":
            if lead.assigned_account_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Lead has no assigned attorney for this template",
                )
            account = db.get(Account, lead.assigned_account_id)
            if account is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Assigned attorney account not found",
                )
            return EmailService._normalize_email(account.work_email or account.email)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot resolve default recipient for template {template}",
        )

    @staticmethod
    def _build_lead_context(db: Session, *, lead: Lead, template: str) -> dict[str, Any]:
        if template in {"prospect_confirmation", "prospect_follow_up"}:
            return {"first_name": lead.first_name, "lead_id": str(lead.id)}

        if template == "attorney_new_lead":
            prospect_name = f"{lead.first_name} {lead.last_name}".strip()
            return {
                "prospect_name": prospect_name,
                "lead_id": str(lead.id),
                "lead_url": f"{settings.webapp_url}/leads/{lead.id}",
            }

        raise ValueError(f"No lead context builder for template {template}")

    @staticmethod
    def _attempt_send(
        db: Session,
        notification: EmailNotification,
        *,
        subject: str,
        html_body: str,
        raise_on_failure: bool = False,
    ) -> EmailNotification:
        try:
            EmailService._send_smtp(
                recipient=notification.recipient,
                subject=subject,
                html_body=html_body,
            )
            notification.status = EmailStatus.SENT.value
            notification.sent_at = datetime.now(timezone.utc)
            notification.error_message = None
        except EmailDeliveryError as exc:
            notification.status = EmailStatus.FAILED.value
            notification.error_message = str(exc)
            logger.warning(
                "Email send failed template=%s recipient=%s",
                notification.template,
                notification.recipient,
            )
            if raise_on_failure:
                raise
        db.flush()
        return notification

    @staticmethod
    def send_verification_email(
        db: Session,
        *,
        pending_intake_id: UUID,
        email: str,
        token: str,
    ) -> EmailNotification:
        """S7a — must succeed or caller rolls back pending intake."""

        pending = db.get(LeadIntakePending, pending_intake_id)
        if pending is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending intake not found",
            )

        normalized = EmailService._normalize_email(email)
        verify_url = f"{settings.webapp_url}/verify?token={token}"
        context = {
            "first_name": pending.first_name,
            "verify_url": verify_url,
            "expires_at": pending.expires_at.isoformat(),
        }
        subject, html_body = EmailService.render_template("email_verification", context)

        notification = EmailNotification(
            lead_id=None,
            pending_intake_id=pending_intake_id,
            conversation_id=uuid.uuid4(),
            recipient=normalized,
            template="email_verification",
            subject=subject,
            status=EmailStatus.PENDING.value,
        )
        db.add(notification)
        db.flush()

        try:
            EmailService._attempt_send(
                db,
                notification,
                subject=subject,
                html_body=html_body,
                raise_on_failure=True,
            )
        except EmailDeliveryError as exc:
            raise EmailDeliveryError(str(exc)) from exc

        return notification

    @staticmethod
    def send_lead_created_notifications(
        db: Session, *, lead: Lead
    ) -> list[EmailNotification]:
        """S7 — never raises; logs failures."""

        results: list[EmailNotification] = []

        prospect_context = EmailService._build_lead_context(
            db, lead=lead, template="prospect_confirmation"
        )
        subject, html = EmailService.render_template(
            "prospect_confirmation", prospect_context
        )
        prospect_conv = EmailService.resolve_conversation_id(
            db, lead_id=lead.id, recipient=lead.email
        )
        prospect_row = EmailNotification(
            lead_id=lead.id,
            conversation_id=prospect_conv,
            recipient=lead.email,
            template="prospect_confirmation",
            subject=subject,
            status=EmailStatus.PENDING.value,
        )
        db.add(prospect_row)
        db.flush()
        EmailService._attempt_send(
            db, prospect_row, subject=subject, html_body=html, raise_on_failure=False
        )
        results.append(prospect_row)

        try:
            attorney_email = EmailService._resolve_recipient_for_lead(
                db, lead=lead, template="attorney_new_lead", recipient=None
            )
        except HTTPException as exc:
            logger.warning(
                "Skipping attorney_new_lead for lead %s: %s", lead.id, exc.detail
            )
            attorney_row = EmailNotification(
                lead_id=lead.id,
                conversation_id=uuid.uuid4(),
                recipient="",
                template="attorney_new_lead",
                subject="New lead notification (failed)",
                status=EmailStatus.FAILED.value,
                error_message=str(exc.detail),
            )
            db.add(attorney_row)
            db.flush()
            results.append(attorney_row)
            return results

        attorney_context = EmailService._build_lead_context(
            db, lead=lead, template="attorney_new_lead"
        )
        subject, html = EmailService.render_template(
            "attorney_new_lead", attorney_context
        )
        attorney_conv = EmailService.resolve_conversation_id(
            db, lead_id=lead.id, recipient=attorney_email
        )
        attorney_row = EmailNotification(
            lead_id=lead.id,
            conversation_id=attorney_conv,
            recipient=attorney_email,
            template="attorney_new_lead",
            subject=subject,
            status=EmailStatus.PENDING.value,
        )
        db.add(attorney_row)
        db.flush()
        EmailService._attempt_send(
            db, attorney_row, subject=subject, html_body=html, raise_on_failure=False
        )
        results.append(attorney_row)

        return results

    @staticmethod
    def send_template(
        db: Session,
        *,
        lead_id: UUID,
        template: str,
        recipient: str | None = None,
        context: dict[str, Any] | None = None,
        conversation_id: UUID | None = None,
    ) -> EmailNotification:
        """E2 — render template, send via SMTP, update status."""

        if template not in EmailService.STAFF_TEMPLATES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Template not allowed for staff send: {template}",
            )

        lead = db.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found",
            )

        resolved_recipient = EmailService._resolve_recipient_for_lead(
            db, lead=lead, template=template, recipient=recipient
        )
        resolved_conv = EmailService.resolve_conversation_id(
            db,
            lead_id=lead_id,
            recipient=resolved_recipient,
            conversation_id=conversation_id,
        )
        render_context = context or EmailService._build_lead_context(
            db, lead=lead, template=template
        )
        subject, html_body = EmailService.render_template(template, render_context)

        notification = EmailNotification(
            lead_id=lead_id,
            conversation_id=resolved_conv,
            recipient=resolved_recipient,
            template=template,
            subject=subject,
            status=EmailStatus.PENDING.value,
        )
        db.add(notification)
        db.flush()
        EmailService._attempt_send(
            db,
            notification,
            subject=subject,
            html_body=html_body,
            raise_on_failure=False,
        )
        return notification

    @staticmethod
    def retry_failed(db: Session, email_id: UUID) -> EmailNotification:
        """E3 — re-render and retry SMTP for a failed row."""

        notification = db.get(EmailNotification, email_id)
        if notification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email notification not found",
            )

        if not can_retry_failed_send(status=notification.status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only failed notifications can be retried",
            )

        if notification.lead_id is not None:
            lead = db.get(Lead, notification.lead_id)
            if lead is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lead not found",
                )
            context = EmailService._build_lead_context(
                db, lead=lead, template=notification.template
            )
        elif notification.template == "email_verification":
            pending = db.get(LeadIntakePending, notification.pending_intake_id)
            if pending is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Cannot retry verification email without pending intake",
                )
            context = {
                "first_name": pending.first_name,
                "verify_url": f"{settings.webapp_url}/verify?token=RETRY_NOT_AVAILABLE",
                "expires_at": pending.expires_at.isoformat(),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot rebuild context for retry",
            )

        subject, html_body = EmailService.render_template(
            notification.template, context
        )
        notification.subject = subject
        notification.status = EmailStatus.PENDING.value
        notification.error_message = None
        db.flush()

        EmailService._attempt_send(
            db,
            notification,
            subject=subject,
            html_body=html_body,
            raise_on_failure=False,
        )
        return notification
