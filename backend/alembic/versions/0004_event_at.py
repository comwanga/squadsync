"""event_at

Revision ID: 0004_event_at
Revises: 0003_universal_strength_taxonomy
Create Date: 2026-06-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_event_at"
down_revision: Union[str, None] = "0003_universal_strength_taxonomy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("events") as b:
        b.add_column(sa.Column("event_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("events") as b:
        b.drop_column("event_at")
