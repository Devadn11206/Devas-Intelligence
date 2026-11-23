"""0002_tenant_auth_rls

Revision ID: 0002_tenant_auth_rls
Revises: 0001_baseline_ext
Create Date: 2026-11-20 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002_tenant_auth_rls'
down_revision: Union[str, None] = '0001_baseline_ext'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enums in tenant schema
    user_role_enum = postgresql.ENUM(
        'guest', 'user', 'org_member', 'org_admin', 'platform_moderator', 'platform_admin', 'super_admin',
        name='user_role', schema='tenant', create_type=False
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    org_member_role_enum = postgresql.ENUM(
        'org_member', 'org_admin',
        name='org_member_role', schema='tenant', create_type=False
    )
    org_member_role_enum.create(op.get_bind(), checkfirst=True)

    bookmark_entity_type_enum = postgresql.ENUM(
        'paper', 'repo', 'model', 'article', 'tool',
        name='bookmark_entity_type', schema='tenant', create_type=False
    )
    bookmark_entity_type_enum.create(op.get_bind(), checkfirst=True)

    digest_frequency_enum = postgresql.ENUM(
        'daily', 'weekly', 'off',
        name='digest_frequency', schema='tenant', create_type=False
    )
    digest_frequency_enum.create(op.get_bind(), checkfirst=True)

    # 2. Table: tenant.users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('role', user_role_enum, nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('oauth_provider', sa.String(50), nullable=True),
        sa.Column('oauth_sub', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='tenant',
    )
    op.create_index('ix_tenant_users_email', 'users', ['email'], unique=True, schema='tenant')

    # 3. Table: tenant.organizations
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='tenant',
    )
    op.create_index('ix_tenant_organizations_slug', 'organizations', ['slug'], unique=True, schema='tenant')

    # 4. Table: tenant.organization_members
    op.create_table(
        'organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', org_member_role_enum, nullable=False, server_default='org_member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('org_id', 'user_id', name='uq_org_member'),
        schema='tenant',
    )

    # 5. Table: tenant.refresh_tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='tenant',
    )
    op.create_index('ix_tenant_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True, schema='tenant')

    # 6. Table: tenant.user_preferences (RLS enforced)
    op.create_table(
        'user_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('followed_topics', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('followed_technologies', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('followed_repos', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('digest_frequency', digest_frequency_enum, nullable=False, server_default='weekly'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='tenant',
    )
    op.create_index('ix_tenant_user_preferences_user_id', 'user_preferences', ['user_id'], schema='tenant')

    # 7. Table: tenant.bookmarks (RLS enforced)
    op.create_table(
        'bookmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenant.users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_type', bookmark_entity_type_enum, nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'entity_type', 'entity_id', name='uq_user_entity_bookmark'),
        schema='tenant',
    )
    op.create_index('ix_tenant_bookmarks_user_id', 'bookmarks', ['user_id'], schema='tenant')
    op.create_index('ix_tenant_bookmarks_entity_id', 'bookmarks', ['entity_id'], schema='tenant')
    op.create_index('ix_tenant_bookmarks_user_entity', 'bookmarks', ['user_id', 'entity_type'], schema='tenant')

    # 8. Table: tenant.audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema='tenant',
    )
    op.create_index('ix_tenant_audit_logs_actor_user_id', 'audit_logs', ['actor_user_id'], schema='tenant')
    op.create_index('ix_tenant_audit_logs_action', 'audit_logs', ['action'], schema='tenant')

    # 9. Non-Superuser Application Role (`deva_app_user`)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'deva_app_user') THEN
            CREATE ROLE deva_app_user WITH LOGIN PASSWORD 'deva_app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
        END IF;
    END
    $$;
    """)
    op.execute("GRANT USAGE ON SCHEMA intel TO deva_app_user;")
    op.execute("GRANT USAGE ON SCHEMA tenant TO deva_app_user;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA intel TO deva_app_user;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tenant TO deva_app_user;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA intel GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO deva_app_user;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA tenant GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO deva_app_user;")

    # 10. Enable and Force Row-Level Security (RLS)
    op.execute("ALTER TABLE tenant.user_preferences ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenant.user_preferences FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenant.bookmarks ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenant.bookmarks FORCE ROW LEVEL SECURITY;")

    # 11. Create RLS Policies
    op.execute("""
    CREATE POLICY user_preferences_isolation_policy ON tenant.user_preferences
    FOR ALL
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)

    op.execute("""
    CREATE POLICY bookmarks_isolation_policy ON tenant.bookmarks
    FOR ALL
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)


def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS bookmarks_isolation_policy ON tenant.bookmarks;")
    op.execute("DROP POLICY IF EXISTS user_preferences_isolation_policy ON tenant.user_preferences;")

    # Drop tables
    op.drop_table('audit_logs', schema='tenant')
    op.drop_table('bookmarks', schema='tenant')
    op.drop_table('user_preferences', schema='tenant')
    op.drop_table('refresh_tokens', schema='tenant')
    op.drop_table('organization_members', schema='tenant')
    op.drop_table('organizations', schema='tenant')
    op.drop_table('users', schema='tenant')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS tenant.digest_frequency;")
    op.execute("DROP TYPE IF EXISTS tenant.bookmark_entity_type;")
    op.execute("DROP TYPE IF EXISTS tenant.org_member_role;")
    op.execute("DROP TYPE IF EXISTS tenant.user_role;")
