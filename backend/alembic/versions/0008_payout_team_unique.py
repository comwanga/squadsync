"""unique payout per team per allocation

Enforces idempotent payouts: a winning team can only be paid once. Re-attempts
go through the retry endpoint, which reuses the existing payout's items.

Revision ID: 0008_payout_team_unique
Revises: 0007_lightning_payout
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008_payout_team_unique"
down_revision: Union[str, None] = "0007_lightning_payout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("payouts") as b:
        b.create_unique_constraint(
            "uq_payout_allocation_team", ["allocation_id", "team_label"]
        )


def downgrade() -> None:
    with op.batch_alter_table("payouts") as b:
        b.drop_constraint("uq_payout_allocation_team", type_="unique")
