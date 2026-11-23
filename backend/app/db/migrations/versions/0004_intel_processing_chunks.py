"""0004_intel_processing_chunks

Revision ID: 0004_intel_proc_chunks
Revises: 0003_intel_ingestion_schema
Create Date: 2026-11-20 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '0004_intel_proc_chunks'
down_revision: Union[str, None] = '0003_intel_ingestion_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create intel.event_clusters
    op.create_table(
        'event_clusters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('canonical_title', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('primary_document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('centroid_embedding', Vector(768), nullable=True),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='intel'
    )

    # 2. Add columns to intel.documents
    op.add_column('documents', sa.Column('event_cluster_id', postgresql.UUID(as_uuid=True), nullable=True), schema='intel')
    op.add_column('documents', sa.Column('summary_ai', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='intel')
    op.add_column('documents', sa.Column('processing_error', sa.Text(), nullable=True), schema='intel')
    op.add_column('documents', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True), schema='intel')

    # Foreign keys and index for event_cluster_id
    op.create_foreign_key(
        'fk_documents_event_cluster_id_event_clusters',
        'documents', 'event_clusters',
        ['event_cluster_id'], ['id'],
        source_schema='intel', referent_schema='intel',
        ondelete='SET NULL'
    )
    op.create_index('ix_documents_event_cluster_id', 'documents', ['event_cluster_id'], schema='intel')

    # Add foreign key from event_clusters.primary_document_id -> documents.id
    op.create_foreign_key(
        'fk_event_clusters_primary_document_id_documents',
        'event_clusters', 'documents',
        ['primary_document_id'], ['id'],
        source_schema='intel', referent_schema='intel',
        ondelete='SET NULL'
    )

    # 3. Create intel.document_chunks
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('section_type', sa.String(length=50), nullable=False, server_default='overview'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'search_vector',
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', coalesce(content, ''))", persisted=True),
            nullable=True
        ),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['intel.documents.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk_index'),
        schema='intel'
    )

    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'], schema='intel')
    
    # GIN index for search_vector
    op.execute("CREATE INDEX ix_chunks_search_vector ON intel.document_chunks USING gin(search_vector);")

    # HNSW index for embedding using vector_cosine_ops
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON intel.document_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )

    # Grant permissions to deva_app_user
    op.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA intel TO deva_app_user;")
    op.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA intel TO deva_app_user;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS intel.document_chunks CASCADE;")
    op.drop_constraint('fk_event_clusters_primary_document_id_documents', 'event_clusters', schema='intel', type_='foreignkey')
    op.drop_constraint('fk_documents_event_cluster_id_event_clusters', 'documents', schema='intel', type_='foreignkey')
    op.drop_index('ix_documents_event_cluster_id', table_name='documents', schema='intel')
    op.drop_column('documents', 'processed_at', schema='intel')
    op.drop_column('documents', 'processing_error', schema='intel')
    op.drop_column('documents', 'summary_ai', schema='intel')
    op.drop_column('documents', 'event_cluster_id', schema='intel')
    op.execute("DROP TABLE IF EXISTS intel.event_clusters CASCADE;")
