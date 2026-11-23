"""0003_intel_ingestion_schema

Revision ID: 0003_intel_ingestion_schema
Revises: 0002_tenant_auth_rls
Create Date: 2026-11-20 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003_intel_ingestion_schema'
down_revision: Union[str, None] = '0002_tenant_auth_rls'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enums in intel schema
    source_category_enum = postgresql.ENUM(
        'research', 'academic_metadata', 'code', 'model_ecosystem', 'company_blog', 'tech_news',
        name='source_category', schema='intel', create_type=False
    )
    source_category_enum.create(op.get_bind(), checkfirst=True)

    source_health_status_enum = postgresql.ENUM(
        'healthy', 'degraded', 'failing', 'disabled',
        name='source_health_status', schema='intel', create_type=False
    )
    source_health_status_enum.create(op.get_bind(), checkfirst=True)

    ingestion_job_status_enum = postgresql.ENUM(
        'queued', 'running', 'completed', 'partial_success', 'failed',
        name='ingestion_job_status', schema='intel', create_type=False
    )
    ingestion_job_status_enum.create(op.get_bind(), checkfirst=True)

    content_type_enum = postgresql.ENUM(
        'paper', 'repo', 'model', 'article', 'tool',
        name='content_type', schema='intel', create_type=False
    )
    content_type_enum.create(op.get_bind(), checkfirst=True)

    processing_status_enum = postgresql.ENUM(
        'raw_ingested', 'processed', 'failed',
        name='processing_status', schema='intel', create_type=False
    )
    processing_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Table: intel.sources
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('category', source_category_enum, nullable=False),
        sa.Column('adapter_key', sa.String(50), nullable=False),
        sa.Column('base_url', sa.String(512), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('refresh_interval_minutes', sa.Integer(), nullable=False, server_default=sa.text('360')),
        sa.Column('rate_limit_rpm', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('health_status', source_health_status_enum, nullable=False, server_default='healthy'),
        sa.Column('attribution_text', sa.String(255), nullable=False, server_default=''),
        sa.Column('license_terms', sa.String(255), nullable=False, server_default=''),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='intel',
    )
    op.create_index('ix_intel_sources_slug', 'sources', ['slug'], unique=True, schema='intel')

    # 3. Table: intel.ingestion_jobs
    op.create_table(
        'ingestion_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intel.sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('status', ingestion_job_status_enum, nullable=False, server_default='queued'),
        sa.Column('triggered_by', sa.String(50), nullable=False, server_default='scheduler'),
        sa.Column('records_fetched', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('records_inserted', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('records_updated', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('records_quarantined', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        schema='intel',
    )
    op.create_index('ix_intel_ingestion_jobs_source_id', 'ingestion_jobs', ['source_id'], schema='intel')
    op.create_index('ix_intel_ingestion_jobs_celery_task_id', 'ingestion_jobs', ['celery_task_id'], schema='intel')

    # 4. Table: intel.quarantined_records
    op.create_table(
        'quarantined_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intel.sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intel.ingestion_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('raw_payload', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('validation_error', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='intel',
    )
    op.create_index('ix_intel_quarantined_source_id', 'quarantined_records', ['source_id'], schema='intel')
    op.create_index('ix_intel_quarantined_job_id', 'quarantined_records', ['job_id'], schema='intel')

    # 5. Table: intel.documents
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intel.sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_type', content_type_enum, nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('canonical_url', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('summary_raw', sa.Text(), nullable=False, server_default=''),
        sa.Column('content_raw', sa.Text(), nullable=True),
        sa.Column('authors', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('processing_status', processing_status_enum, nullable=False, server_default='raw_ingested'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('canonical_url', name='uq_documents_canonical_url'),
        sa.UniqueConstraint('source_id', 'external_id', name='uq_source_external_id'),
        schema='intel',
    )
    op.create_index('ix_intel_documents_source_id', 'documents', ['source_id'], schema='intel')
    op.create_index('ix_intel_documents_content_type', 'documents', ['content_type'], schema='intel')
    op.create_index('ix_intel_documents_external_id', 'documents', ['external_id'], schema='intel')
    op.create_index('ix_intel_documents_content_hash', 'documents', ['content_hash'], schema='intel')
    op.create_index('ix_intel_documents_published_at', 'documents', ['published_at'], schema='intel')
    op.create_index('ix_intel_documents_type_published', 'documents', ['content_type', 'published_at'], schema='intel')

    # 6. Grant permissions to non-superuser app role deva_app_user
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA intel TO deva_app_user;")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA intel TO deva_app_user;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA intel GRANT ALL ON TABLES TO deva_app_user;")


def downgrade() -> None:
    op.drop_table('documents', schema='intel')
    op.drop_table('quarantined_records', schema='intel')
    op.drop_table('ingestion_jobs', schema='intel')
    op.drop_table('sources', schema='intel')

    op.execute("DROP TYPE IF EXISTS intel.processing_status;")
    op.execute("DROP TYPE IF EXISTS intel.content_type;")
    op.execute("DROP TYPE IF EXISTS intel.ingestion_job_status;")
    op.execute("DROP TYPE IF EXISTS intel.source_health_status;")
    op.execute("DROP TYPE IF EXISTS intel.source_category;")
