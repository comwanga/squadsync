"""escrow agent events and payout escrow tracking

Revision ID: 0011_escrow_agent
Revises: 0010_reward_claims
Create Date: 2026-08-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_escrow_agent"
down_revision: Union[str, None] = "0010_reward_claims"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "escrow_agent_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("coordinate", sa.String(), nullable=False),
        sa.Column("event_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("coordinate"),
    )
    op.create_index(op.f("ix_escrow_agent_events_coordinate"), "escrow_agent_events", ["coordinate"], unique=False)
    op.create_index(op.f("ix_escrow_agent_events_user_id"), "escrow_agent_events", ["user_id"], unique=False)

    op.add_column("payouts", sa.Column("escrow_coordinate", sa.String(), nullable=True))
    op.add_column("payouts", sa.Column("escrow_status", sa.String(), nullable=False, server_default="direct"))


def downgrade() -> None:
    op.drop_column("payouts", "escrow_status")
    op.drop_column("payouts", "escrow_coordinate")
    op.drop_index(op.f("ix_escrow_agent_events_user_id"), table_name="escrow_agent_events")
    op.drop_index(op.f("ix_escrow_agent_events_coordinate"), table_name="escrow_agent_events")
    op.drop_table("escrow_agent_events")
