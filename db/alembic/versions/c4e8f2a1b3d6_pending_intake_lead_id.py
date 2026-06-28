"""lead_intake_pending.lead_id for L1b idempotent verify

Revision ID: c4e8f2a1b3d6
Revises: b8f2a1c3d4e5
Create Date: 2026-06-27 23:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e8f2a1b3d6"
down_revision: Union[str, Sequence[str], None] = "b8f2a1c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lead_intake_pending",
        sa.Column(
            "lead_id",
            sa.UUID(),
            nullable=True,
            comment="Set when L1b completes; enables idempotent verify retries.",
        ),
    )
    op.create_foreign_key(
        "fk_lead_intake_pending_lead_id",
        "lead_intake_pending",
        "leads",
        ["lead_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_lead_intake_pending_lead_id"),
        "lead_intake_pending",
        ["lead_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_lead_intake_pending_lead_id"),
        table_name="lead_intake_pending",
    )
    op.drop_constraint(
        "fk_lead_intake_pending_lead_id",
        "lead_intake_pending",
        type_="foreignkey",
    )
    op.drop_column("lead_intake_pending", "lead_id")
