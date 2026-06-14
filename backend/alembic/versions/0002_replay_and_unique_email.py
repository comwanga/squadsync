"""replay protection + unique participant email

Revision ID: 0002_replay_and_unique_email
Revises: 0001_nostr_user_schema
Create Date: 2026-06-14

Adds:
- used_auth_events table for NIP-98 replay protection (H1)
- unique (event_id, email) constraint on participants (H4)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_replay_and_unique_email"
down_revision: Union[str, None] = "0001_nostr_user_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "used_auth_events",
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )

    with op.batch_alter_table("participants") as batch_op:
        batch_op.create_unique_constraint(
            "uq_participant_event_email", ["event_id", "email"]
        )


def downgrade() -> None:
    with op.batch_alter_table("participants") as batch_op:
        batch_op.drop_constraint("uq_participant_event_email", type_="unique")
    op.drop_table("used_auth_events")
