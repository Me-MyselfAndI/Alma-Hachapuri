"""email notification nullable lead + pending_intake_id

Revision ID: b8f2a1c3d4e5
Revises: 3dffc1e2279e
Create Date: 2026-06-27 22:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8f2a1c3d4e5"
down_revision: Union[str, Sequence[str], None] = "3dffc1e2279e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "email_notifications",
        "lead_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
    op.add_column(
        "email_notifications",
        sa.Column(
            "pending_intake_id",
            sa.UUID(),
            nullable=True,
            comment="Set for S7a email_verification rows (pre-lead).",
        ),
    )
    op.create_foreign_key(
        "fk_email_notifications_pending_intake_id",
        "email_notifications",
        "lead_intake_pending",
        ["pending_intake_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_email_notifications_pending_intake_id"),
        "email_notifications",
        ["pending_intake_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_email_notifications_pending_intake_id"),
        table_name="email_notifications",
    )
    op.drop_constraint(
        "fk_email_notifications_pending_intake_id",
        "email_notifications",
        type_="foreignkey",
    )
    op.drop_column("email_notifications", "pending_intake_id")
    op.alter_column(
        "email_notifications",
        "lead_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
