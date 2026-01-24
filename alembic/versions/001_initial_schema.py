from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("orcid_id", sa.String(length=19), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_orcid_id", "users", ["orcid_id"], unique=True)

    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_teams_name", "teams", ["name"], unique=False)
    op.create_index("ix_teams_created_by_id", "teams", ["created_by_id"], unique=False)

    op.create_table(
        "team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Enum("owner", "admin", "member", "viewer", name="team_role"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_member"),
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"], unique=False)
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"], unique=False)
    op.create_index(
        "ix_team_members_team_user",
        "team_members",
        ["team_id", "user_id"],
        unique=False,
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("topic_tags", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_sessions_team_id", "sessions", ["team_id"], unique=False)
    op.create_index("ix_sessions_created_by", "sessions", ["created_by_id"], unique=False)
    op.create_index(
        "ix_sessions_team_archived",
        "sessions",
        ["team_id", "is_archived"],
        unique=False,
    )

    op.create_table(
        "session_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "permission",
            sa.Enum("read", "write", "admin", name="session_permission"),
            nullable=False,
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "user_id", name="uq_session_participant"),
    )
    op.create_index("ix_session_participants_session_id", "session_participants", ["session_id"], unique=False)
    op.create_index("ix_session_participants_user_id", "session_participants", ["user_id"], unique=False)
    op.create_index(
        "ix_session_participants_session_user",
        "session_participants",
        ["session_id", "user_id"],
        unique=False,
    )

    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "material_type",
            sa.Enum("paper", "sequence", "image", "experiment", "note", name="material_type"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("qdrant_point_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_materials_session_id", "materials", ["session_id"], unique=False)
    op.create_index("ix_materials_uploaded_by", "materials", ["uploaded_by_id"], unique=False)
    op.create_index("ix_materials_qdrant_point", "materials", ["qdrant_point_id"], unique=False)
    op.create_index(
        "ix_materials_session_type",
        "materials",
        ["session_id", "material_type"],
        unique=False,
    )

    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_activity_logs_session_id", "activity_logs", ["session_id"], unique=False)
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"], unique=False)
    op.create_index(
        "ix_activity_logs_session_action",
        "activity_logs",
        ["session_id", "action_type"],
        unique=False,
    )
    op.create_index(
        "ix_activity_logs_entity",
        "activity_logs",
        ["entity_type", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_activity_logs_entity", table_name="activity_logs")
    op.drop_index("ix_activity_logs_session_action", table_name="activity_logs")
    op.drop_index("ix_activity_logs_user_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_session_id", table_name="activity_logs")
    op.drop_table("activity_logs")

    op.drop_index("ix_materials_session_type", table_name="materials")
    op.drop_index("ix_materials_qdrant_point", table_name="materials")
    op.drop_index("ix_materials_uploaded_by", table_name="materials")
    op.drop_index("ix_materials_session_id", table_name="materials")
    op.drop_table("materials")

    op.drop_index("ix_session_participants_session_user", table_name="session_participants")
    op.drop_index("ix_session_participants_user_id", table_name="session_participants")
    op.drop_index("ix_session_participants_session_id", table_name="session_participants")
    op.drop_table("session_participants")

    op.drop_index("ix_sessions_team_archived", table_name="sessions")
    op.drop_index("ix_sessions_created_by", table_name="sessions")
    op.drop_index("ix_sessions_team_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_team_members_team_user", table_name="team_members")
    op.drop_index("ix_team_members_user_id", table_name="team_members")
    op.drop_index("ix_team_members_team_id", table_name="team_members")
    op.drop_table("team_members")

    op.drop_index("ix_teams_created_by_id", table_name="teams")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_table("teams")

    op.drop_index("ix_users_orcid_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS team_role")
    op.execute("DROP TYPE IF EXISTS session_permission")
    op.execute("DROP TYPE IF EXISTS material_type")
