"""reward claim links

Revision ID: 0010_reward_claims
Revises: 0009_team_rationale
Create Date: 2026-07-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_reward_claims"
down_revision: Union[str, None] = "0009_team_rationale"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reward_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("allocation_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("total_sats", sa.Integer(), nullable=False),
        sa.Column("amount_sats", sa.Integer(), nullable=False),
        sa.Column("lightning_address", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("allocation_id", "team_id", "participant_id", name="uq_reward_claim_member"),
    )
    op.create_index(op.f("ix_reward_claims_allocation_id"), "reward_claims", ["allocation_id"], unique=False)
    op.create_index(op.f("ix_reward_claims_participant_id"), "reward_claims", ["participant_id"], unique=False)
    op.create_index(op.f("ix_reward_claims_team_id"), "reward_claims", ["team_id"], unique=False)
    op.create_index(op.f("ix_reward_claims_token"), "reward_claims", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_reward_claims_token"), table_name="reward_claims")
    op.drop_index(op.f("ix_reward_claims_team_id"), table_name="reward_claims")
    op.drop_index(op.f("ix_reward_claims_participant_id"), table_name="reward_claims")
    op.drop_index(op.f("ix_reward_claims_allocation_id"), table_name="reward_claims")
    op.drop_table("reward_claims")
