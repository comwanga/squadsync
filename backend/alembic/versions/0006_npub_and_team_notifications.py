"""npub and team_notifications

Revision ID: 0006_npub_and_team_notifications
Revises: 0005_feedback
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_npub_and_team_notifications"
down_revision: Union[str, None] = "0005_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("participants") as b:
        b.add_column(sa.Column("npub", sa.String(), nullable=True))

    op.create_table(
        "team_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("allocation_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("allocation_id", "participant_id", name="uq_team_notification"),
    )
    op.create_index("ix_team_notifications_allocation_id", "team_notifications", ["allocation_id"])
    op.create_index("ix_team_notifications_created_at", "team_notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_team_notifications_created_at", table_name="team_notifications")
    op.drop_index("ix_team_notifications_allocation_id", table_name="team_notifications")
    op.drop_table("team_notifications")
    with op.batch_alter_table("participants") as b:
        b.drop_column("npub")
