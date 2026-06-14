"""universal strength taxonomy

Revision ID: 0003
Revises: 0002_replay_and_unique_email
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002_replay_and_unique_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pre-launch: clear participants so the not-null strength/experience columns
    # can be added without back-fill. Allocations reference participants, so clear
    # downstream rows first to respect FKs.
    op.execute("DELETE FROM team_members")
    op.execute("DELETE FROM teams")
    op.execute("DELETE FROM allocations")
    op.execute("DELETE FROM participants")

    with op.batch_alter_table("participants") as b:
        b.drop_column("role")
        b.drop_column("skill_level")
        b.drop_column("years_experience")
        b.add_column(sa.Column("experience_level", sa.String(), nullable=False, server_default="beginner"))
        b.add_column(sa.Column("primary_strength", sa.String(), nullable=False, server_default="other"))
        b.add_column(sa.Column("strength_other", sa.String(), nullable=True))
        b.add_column(sa.Column("normalized_strength", sa.String(), nullable=True))
        b.add_column(sa.Column("strength_source", sa.String(), nullable=False, server_default="preset"))


def downgrade() -> None:
    with op.batch_alter_table("participants") as b:
        b.drop_column("strength_source")
        b.drop_column("normalized_strength")
        b.drop_column("strength_other")
        b.drop_column("primary_strength")
        b.drop_column("experience_level")
        b.add_column(sa.Column("role", sa.String(), nullable=True))
        b.add_column(sa.Column("skill_level", sa.String(), nullable=True))
        b.add_column(sa.Column("years_experience", sa.Integer(), nullable=True))
