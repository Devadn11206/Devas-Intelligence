"""0001_baseline_extensions

Revision ID: 0001_baseline_ext
Revises: 
Create Date: 2026-11-20 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_baseline_ext'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

    # Domain Schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS intel;")
    op.execute("CREATE SCHEMA IF NOT EXISTS tenant;")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS tenant CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS intel CASCADE;")
    op.execute("DROP EXTENSION IF EXISTS \"uuid-ossp\";")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
    op.execute("DROP EXTENSION IF EXISTS vector;")
