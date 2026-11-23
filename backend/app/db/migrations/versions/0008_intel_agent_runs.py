"""0008_intel_agent_runs

Revision ID: 0008_intel_agent_runs
Revises: 0007_trends_watchlists_consensus
Create Date: 2026-11-21 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0008_intel_agent_runs'
down_revision: Union[str, None] = '0007_trends_watchlists_consensus'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_type', sa.String(100), nullable=False),
        sa.Column('query_or_topic', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='completed'),
        sa.Column('steps_executed', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('step_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='intel'
    )
    op.create_index('ix_agent_runs_workflow_type', 'agent_runs', ['workflow_type'], schema='intel')
    op.create_index('ix_agent_runs_status', 'agent_runs', ['status'], schema='intel')
    op.create_index('ix_agent_runs_created_at', 'agent_runs', ['created_at'], schema='intel')

    op.execute("GRANT ALL PRIVILEGES ON TABLE intel.agent_runs TO deva_app_user;")


def downgrade() -> None:
    op.drop_table('agent_runs', schema='intel')
