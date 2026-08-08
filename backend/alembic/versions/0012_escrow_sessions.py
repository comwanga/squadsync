"""escrow sessions

Revision ID: 0012_escrow_sessions
Revises: 0011_escrow_agent
Create Date: 2026-08-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_escrow_sessions"
down_revision: Union[str, None] = "0011_escrow_agent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "escrows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organizer_id", sa.Uuid(), nullable=False),
        sa.Column("agent_coordinate", sa.String(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("allocation_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("amount_sats", sa.Integer(), nullable=False),
        sa.Column("rail", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("release_policy", sa.JSON(), nullable=False),
        sa.Column("refund_policy", sa.JSON(), nullable=False),
        sa.Column("dispute_policy", sa.JSON(), nullable=False),
        sa.Column("funding_request", sa.String(), nullable=True),
        sa.Column("nwc_uri", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("funded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_escrows_organizer_id"), "escrows", ["organizer_id"], unique=False)
    op.create_index(op.f("ix_escrows_agent_coordinate"), "escrows", ["agent_coordinate"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_escrows_agent_coordinate"), table_name="escrows")
    op.drop_index(op.f("ix_escrows_organizer_id"), table_name="escrows")
    op.drop_table("escrows")
