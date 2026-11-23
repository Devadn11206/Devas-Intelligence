"""0005_intel_entity_links

Revision ID: 0005_intel_entity_links
Revises: 0004_intel_proc_chunks
Create Date: 2026-11-20 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005_intel_entity_links'
down_revision: Union[str, None] = '0004_intel_proc_chunks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums for relation_type and link_method in intel schema
    relation_type_enum = postgresql.ENUM(
        'IMPLEMENTS', 'CITES', 'USES_MODEL', 'USES_DATASET', 'RELEASED_BY', 'RELATED_TO',
        name='relation_type', schema='intel', create_type=False
    )
    relation_type_enum.create(op.get_bind(), checkfirst=True)

    link_method_enum = postgresql.ENUM(
        'deterministic_url', 'arxiv_id_match', 'semantic_author_match',
        name='link_method', schema='intel', create_type=False
    )
    link_method_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create intel.entity_links table
    op.create_table(
        'entity_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'relation_type',
            postgresql.ENUM(
                'IMPLEMENTS', 'CITES', 'USES_MODEL', 'USES_DATASET', 'RELEASED_BY', 'RELATED_TO',
                name='relation_type', schema='intel', create_type=False
            ),
            nullable=False
        ),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column(
            'link_method',
            postgresql.ENUM(
                'deterministic_url', 'arxiv_id_match', 'semantic_author_match',
                name='link_method', schema='intel', create_type=False
            ),
            nullable=False
        ),
        sa.Column('evidence_snippet', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('source_entity_id != target_entity_id', name='ck_no_self_loops'),
        sa.ForeignKeyConstraint(['source_entity_id'], ['intel.documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_entity_id'], ['intel.documents.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('source_entity_id', 'target_entity_id', 'relation_type', name='uq_source_target_relation'),
        schema='intel'
    )

    op.create_index('ix_entity_links_source_entity_id', 'entity_links', ['source_entity_id'], schema='intel')
    op.create_index('ix_entity_links_target_entity_id', 'entity_links', ['target_entity_id'], schema='intel')
    op.create_index('ix_entity_links_relation_type', 'entity_links', ['relation_type'], schema='intel')

    # Grant permissions to deva_app_user
    op.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA intel TO deva_app_user;")
    op.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA intel TO deva_app_user;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS intel.entity_links CASCADE;")
    op.execute("DROP TYPE IF EXISTS intel.link_method;")
    op.execute("DROP TYPE IF EXISTS intel.relation_type;")
