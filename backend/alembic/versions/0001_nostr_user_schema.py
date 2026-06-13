"""nostr user schema

Revision ID: 0001_nostr_user_schema
Revises:
Create Date: 2026-06-13

Replaces email/password/provider schema with Nostr pubkey identity.
Uses generic sa.Uuid and sa.JSON types (no postgresql-specific dialects)
so the migration runs on both PostgreSQL (production) and SQLite (CI).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_nostr_user_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("pubkey", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pubkey"),
    )
    op.create_index("ix_users_pubkey", "users", ["pubkey"], unique=True)

    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("participant_limit", sa.Integer(), nullable=True),
        sa.Column("team_count", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "allocated", "archived", name="event_status"),
            nullable=False,
        ),
        sa.Column("registration_slug", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_slug"),
    )
    op.create_index(
        "ix_events_registration_slug", "events", ["registration_slug"], unique=True
    )

    op.create_table(
        "event_co_organizers",
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "invited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("event_id", "user_id"),
    )

    op.create_table(
        "participants",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column(
            "skill_level",
            sa.Enum(
                "beginner", "intermediate", "advanced", "professional",
                name="skill_level",
            ),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(
                "frontend", "backend", "fullstack", "ai_ml", "ux", "devops",
                "blockchain", "mobile", "product", "marketing",
                name="participant_role",
            ),
            nullable=False,
        ),
        sa.Column("years_experience", sa.Integer(), nullable=False),
        sa.Column("tech_stack", sa.JSON(), nullable=False),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_participants_event_id", "participants", ["event_id"], unique=False
    )

    op.create_table(
        "allocation_configs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("weight_experience", sa.Float(), nullable=False),
        sa.Column("weight_skill", sa.Float(), nullable=False),
        sa.Column("role_constraints", sa.JSON(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )

    op.create_table(
        "allocations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("snapshot_hash", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "published", name="allocation_status"),
            nullable=False,
        ),
        sa.Column("constraint_warnings", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_allocations_event_id", "allocations", ["event_id"], unique=False
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("allocation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("fairness_score", sa.Float(), nullable=True),
        sa.Column("skill_score", sa.Float(), nullable=True),
        sa.Column("role_balance_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_allocation_id", "teams", ["allocation_id"], unique=False)

    op.create_table(
        "team_members",
        sa.Column("team_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("participant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("team_id", "participant_id"),
    )


def downgrade() -> None:
    op.drop_table("team_members")
    op.drop_index("ix_teams_allocation_id", table_name="teams")
    op.drop_table("teams")
    op.drop_index("ix_allocations_event_id", table_name="allocations")
    op.drop_table("allocations")
    op.drop_table("allocation_configs")
    op.drop_index("ix_participants_event_id", table_name="participants")
    op.drop_table("participants")
    op.drop_table("event_co_organizers")
    op.drop_index("ix_events_registration_slug", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_users_pubkey", table_name="users")
    op.drop_table("users")
