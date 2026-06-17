"""lightning payout

Revision ID: 0007_lightning_payout
Revises: 0006_npub_and_team_notifications
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_lightning_payout"
down_revision: Union[str, None] = "0006_npub_and_team_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("participants") as b:
        b.add_column(sa.Column("lightning_address", sa.String(), nullable=True))

    op.create_table(
        "payouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("allocation_id", sa.Uuid(), nullable=False),
        sa.Column("team_label", sa.String(), nullable=False),
        sa.Column("total_sats", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payouts_event_id", "payouts", ["event_id"])
    op.create_index("ix_payouts_allocation_id", "payouts", ["allocation_id"])

    op.create_table(
        "payout_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payout_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("lightning_address", sa.String(), nullable=True),
        sa.Column("amount_sats", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("bolt11", sa.String(), nullable=True),
        sa.Column("preimage", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["payout_id"], ["payouts.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payout_items_payout_id", "payout_items", ["payout_id"])


def downgrade() -> None:
    op.drop_index("ix_payout_items_payout_id", table_name="payout_items")
    op.drop_table("payout_items")
    op.drop_index("ix_payouts_allocation_id", table_name="payouts")
    op.drop_index("ix_payouts_event_id", table_name="payouts")
    op.drop_table("payouts")
    with op.batch_alter_table("participants") as b:
        b.drop_column("lightning_address")
