"""Add audit_logs table

Revision ID: 003_audit_logs
Revises: 002_oauth_accounts
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_audit_logs'
down_revision = '002_oauth_accounts'
branch_label = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE audit_action AS ENUM (
            'login_success', 'login_failure', 'logout', 'token_refresh',
            'oauth_link', 'oauth_unlink', 'password_change', 'password_reset',
            'email_verification', 'permission_granted', 'permission_denied',
            'role_change', 'session_permission_change', 'team_member_added',
            'team_member_removed', 'material_download', 'session_view',
            'sensitive_data_access', 'team_created', 'team_updated',
            'team_deleted', 'session_created', 'session_updated',
            'session_deleted', 'material_created', 'material_updated',
            'material_deleted', 'session_export', 'material_batch_export',
            'research_report_generated'
        );
    """)

    op.execute("""
        CREATE TYPE resource_type AS ENUM (
            'user', 'team', 'session', 'material', 'oauth_account', 'system'
        );
    """)

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'timestamp',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        ),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column(
            'action',
            postgresql.ENUM(name='audit_action', create_type=False),
            nullable=False
        ),
        sa.Column(
            'resource_type',
            postgresql.ENUM(name='resource_type', create_type=False),
            nullable=False
        ),
        sa.Column('resource_id', sa.String(100), nullable=False),
        sa.Column('success', sa.Boolean, nullable=False, default=True),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('correlation_id', sa.String(36), nullable=False),
    )

    op.create_index(
        'ix_audit_logs_timestamp',
        'audit_logs',
        ['timestamp']
    )
    op.create_index(
        'ix_audit_logs_user_timestamp',
        'audit_logs',
        ['user_id', 'timestamp']
    )
    op.create_index(
        'ix_audit_logs_action',
        'audit_logs',
        ['action']
    )
    op.create_index(
        'ix_audit_logs_resource',
        'audit_logs',
        ['resource_type', 'resource_id']
    )
    op.create_index(
        'ix_audit_logs_success',
        'audit_logs',
        ['success']
    )
    op.create_index(
        'ix_audit_logs_correlation',
        'audit_logs',
        ['correlation_id']
    )


def downgrade() -> None:
    op.drop_index('ix_audit_logs_correlation', table_name='audit_logs')
    op.drop_index('ix_audit_logs_success', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_timestamp', table_name='audit_logs')
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')

    op.drop_table('audit_logs')

    op.execute('DROP TYPE resource_type;')
    op.execute('DROP TYPE audit_action;')
