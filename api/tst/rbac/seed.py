"""Shared seed data for RBAC route tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.core.permissions import Role
from src.domains.account.models import Account
from src.domains.account.schemas import AccountCreate
from src.domains.account.service import AccountService
from src.domains.email.models import EmailNotification
from src.domains.email.preconditions import EmailStatus
from src.domains.lead.models import Lead
from src.domains.lead.preconditions import LeadState
from src.domains.prospect.models import Prospect
from src.domains.resume_file.models import ResumeFile

UTC = timezone.utc
PDF_MIME = "application/pdf"


@dataclass
class RbacWorld:
    owner_attorney: Account
    other_attorney: Account
    admin: Account
    intake: Account
    readonly: Account
    lead: Lead
    prospect: Prospect
    failed_email: EmailNotification


def seed_rbac_world(db: Session) -> RbacWorld:
    """Accounts, one lead assigned to owner_attorney, prospect, failed email row."""

    owner = AccountService.create_account(
        db,
        AccountCreate(
            email="rbac-owner@firm.com",
            password="test-pass1",
            role=Role.ATTORNEY,
            first_name="Owner",
            last_name="Attorney",
            is_default_assignee=True,
        ),
    )
    other = AccountService.create_account(
        db,
        AccountCreate(
            email="rbac-other@firm.com",
            password="test-pass1",
            role=Role.ATTORNEY,
            first_name="Other",
            last_name="Attorney",
            is_default_assignee=False,
        ),
    )
    admin = AccountService.create_account(
        db,
        AccountCreate(
            email="rbac-admin@firm.com",
            password="test-pass1",
            role=Role.ADMIN,
            first_name="Admin",
            last_name="User",
        ),
    )
    intake = AccountService.create_account(
        db,
        AccountCreate(
            email="rbac-intake@firm.com",
            password="test-pass1",
            role=Role.INTAKE_COORDINATOR,
            first_name="Intake",
            last_name="Coord",
        ),
    )
    readonly = AccountService.create_account(
        db,
        AccountCreate(
            email="rbac-readonly@firm.com",
            password="test-pass1",
            role=Role.READONLY,
            first_name="Read",
            last_name="Only",
        ),
    )

    prospect = Prospect(
        id=uuid.uuid4(),
        email="prospect@example.com",
        first_name="Prospect",
        last_name="Person",
    )
    db.add(prospect)
    resume = ResumeFile(
        storage_key="rbac/test.pdf",
        original_filename="cv.pdf",
        mime_type=PDF_MIME,
        size_bytes=100,
    )
    db.add(resume)
    db.flush()

    now = datetime.now(UTC)
    lead = Lead(
        prospect_id=prospect.id,
        first_name="Jane",
        last_name="Doe",
        email="prospect@example.com",
        resume_file_id=resume.id,
        state=LeadState.PENDING.value,
        state_changed_at=now,
        assigned_account_id=owner.id,
        created_at=now,
        updated_at=now,
    )
    db.add(lead)
    db.flush()

    conv_id = uuid.uuid4()
    failed_email = EmailNotification(
        lead_id=lead.id,
        conversation_id=conv_id,
        recipient=lead.email,
        template="prospect_follow_up",
        subject="Failed follow up",
        status=EmailStatus.FAILED.value,
        error_message="smtp down",
    )
    db.add(failed_email)
    db.commit()
    db.refresh(lead)
    db.refresh(failed_email)

    return RbacWorld(
        owner_attorney=owner,
        other_attorney=other,
        admin=admin,
        intake=intake,
        readonly=readonly,
        lead=lead,
        prospect=prospect,
        failed_email=failed_email,
    )


def account_for_role(world: RbacWorld, role: Role) -> Account:
    return {
        Role.ADMIN: world.admin,
        Role.ATTORNEY: world.owner_attorney,
        Role.INTAKE_COORDINATOR: world.intake,
        Role.READONLY: world.readonly,
    }[role]
