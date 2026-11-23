"""0009_user_briefings

Revision ID: 0009_user_briefings
Revises: 0008_intel_agent_runs
Create Date: 2026-11-21 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0009_user_briefings'
down_revision: Union[str, None] = '0008_intel_agent_runs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Briefing Type Enum
    briefing_type_enum = postgresql.ENUM(
        'daily_digest', 'deep_dossier', 'weekly_radar',
        name='briefing_type', schema='tenant', create_type=False
    )
    briefing_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Table: tenant.user_briefings
    op.create_table(
        'user_briefings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('briefing_type', briefing_type_enum, nullable=False, server_default='deep_dossier'),
        sa.Column('domain', sa.String(100), nullable=True),
        sa.Column('executive_summary', sa.Text(), nullable=False),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('source_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='tenant'
    )
    op.create_index('ix_user_briefings_user_id', 'user_briefings', ['user_id'], schema='tenant')
    op.create_index('ix_user_briefings_briefing_type', 'user_briefings', ['briefing_type'], schema='tenant')
    op.create_index('ix_user_briefings_domain', 'user_briefings', ['domain'], schema='tenant')
    op.create_index('ix_user_briefings_created_at', 'user_briefings', ['created_at'], schema='tenant')

    # Grant permissions to deva_app_user
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE tenant.user_briefings TO deva_app_user;")

    # Enable and Force Row-Level Security (RLS)
    op.execute("ALTER TABLE tenant.user_briefings ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenant.user_briefings FORCE ROW LEVEL SECURITY;")

    # Create Isolation Policy
    op.execute("""
    CREATE POLICY user_briefings_isolation_policy ON tenant.user_briefings
    FOR ALL
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS user_briefings_isolation_policy ON tenant.user_briefings;")
    op.drop_table('user_briefings', schema='tenant')
    op.execute("DROP TYPE IF EXISTS tenant.briefing_type;")
