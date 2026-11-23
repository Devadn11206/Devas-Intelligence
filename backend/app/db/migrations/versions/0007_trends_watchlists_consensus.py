"""0007_trends_watchlists_consensus

Revision ID: 0007_trends_watchlists_consensus
Revises: 0005_intel_entity_links
Create Date: 2026-11-21 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '0007_trends_watchlists_consensus'
down_revision: Union[str, None] = '0005_intel_entity_links'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums for signal_classification and consensus_status in intel schema
    signal_classification_enum = postgresql.ENUM(
        'breakthrough_momentum', 'hype_spike', 'steady_adoption', 'cooling',
        name='signal_classification', schema='intel', create_type=False
    )
    signal_classification_enum.create(op.get_bind(), checkfirst=True)

    consensus_status_enum = postgresql.ENUM(
        'verified_consensus', 'single_source', 'disputed',
        name='consensus_status', schema='intel', create_type=False
    )
    consensus_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add consensus fields to intel.event_clusters
    op.add_column(
        'event_clusters',
        sa.Column(
            'consensus_status',
            postgresql.ENUM(
                'verified_consensus', 'single_source', 'disputed',
                name='consensus_status', schema='intel', create_type=False
            ),
            nullable=False,
            server_default='single_source',
        ),
        schema='intel'
    )
    op.add_column(
        'event_clusters',
        sa.Column('consensus_summary', sa.Text(), nullable=True),
        schema='intel'
    )

    # 3. Create intel.trend_snapshots table
    op.create_table(
        'trend_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('topic_tag', sa.String(100), nullable=False),
        sa.Column('domain', sa.String(100), nullable=False, server_default='AI & Software'),
        sa.Column('window_date', sa.DateTime(timezone=False), nullable=False),
        sa.Column('paper_count_7d', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('repo_count_7d', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('news_count_7d', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('velocity_growth_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('hype_to_substance_ratio', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column(
            'signal_classification',
            postgresql.ENUM(
                'breakthrough_momentum', 'hype_spike', 'steady_adoption', 'cooling',
                name='signal_classification', schema='intel', create_type=False
            ),
            nullable=False,
            server_default='steady_adoption',
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('topic_tag', 'window_date', name='uq_trend_topic_window_date'),
        schema='intel'
    )
    op.create_index('ix_trend_snapshots_topic_tag', 'trend_snapshots', ['topic_tag'], schema='intel')
    op.create_index('ix_trend_snapshots_domain', 'trend_snapshots', ['domain'], schema='intel')
    op.create_index('ix_trend_snapshots_window_date', 'trend_snapshots', ['window_date'], schema='intel')
    op.create_index('ix_trend_snapshots_signal', 'trend_snapshots', ['signal_classification'], schema='intel')
    op.create_index('ix_trend_snapshots_topic_date', 'trend_snapshots', ['topic_tag', 'window_date'], schema='intel')

    # 4. Create tenant.semantic_watchlists table
    op.create_table(
        'semantic_watchlists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_embedding', Vector(768), nullable=True),
        sa.Column('min_similarity', sa.Float(), nullable=False, server_default='0.78'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='tenant'
    )
    op.create_index('ix_semantic_watchlists_user_id', 'semantic_watchlists', ['user_id'], schema='tenant')
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_watchlists_embedding_hnsw ON tenant.semantic_watchlists
    USING hnsw (query_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """)

    # 5. Create tenant.notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('watchlist_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.semantic_watchlists.id', ondelete='SET NULL'), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intel.documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='tenant'
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], schema='tenant')
    op.create_index('ix_notifications_watchlist_id', 'notifications', ['watchlist_id'], schema='tenant')
    op.create_index('ix_notifications_document_id', 'notifications', ['document_id'], schema='tenant')
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'], schema='tenant')

    # 6. RLS on tenant.semantic_watchlists and tenant.notifications (SEC-005) - separate statements
    op.execute("ALTER TABLE tenant.semantic_watchlists ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenant.semantic_watchlists FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY semantic_watchlists_isolation_policy ON tenant.semantic_watchlists
    FOR ALL
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)

    op.execute("ALTER TABLE tenant.notifications ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenant.notifications FORCE ROW LEVEL SECURITY;")
    op.execute("""
    CREATE POLICY notifications_isolation_policy ON tenant.notifications
    FOR ALL
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)

    # 7. Grant deva_app_user full permissions on all new tables and sequences
    op.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA intel TO deva_app_user;")
    op.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA intel TO deva_app_user;")
    op.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA tenant TO deva_app_user;")
    op.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA tenant TO deva_app_user;")


def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS notifications_isolation_policy ON tenant.notifications;")
    op.execute("DROP POLICY IF EXISTS semantic_watchlists_isolation_policy ON tenant.semantic_watchlists;")

    # Drop tables
    op.drop_table('notifications', schema='tenant')
    op.drop_table('semantic_watchlists', schema='tenant')
    op.drop_table('trend_snapshots', schema='intel')

    # Drop columns on event_clusters
    op.drop_column('event_clusters', 'consensus_summary', schema='intel')
    op.drop_column('event_clusters', 'consensus_status', schema='intel')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS intel.consensus_status;")
    op.execute("DROP TYPE IF EXISTS intel.signal_classification;")
