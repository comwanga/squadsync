"""team rationale

Adds teams.rationale (cached AI explanation per team).

Revision ID: 0009_team_rationale
Revises: 0008_payout_team_unique
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_team_rationale"
down_revision: Union[str, None] = "0008_payout_team_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("teams") as b:
        b.add_column(sa.Column("rationale", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("teams") as b:
        b.drop_column("rationale")
