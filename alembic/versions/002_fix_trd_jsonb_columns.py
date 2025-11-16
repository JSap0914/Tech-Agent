"""Fix TRD columns to JSONB

Revision ID: 002
Revises: 001
Create Date: 2025-11-15

Changes:
- Convert api_specification from Text to JSONB
- Convert database_schema from Text to JSONB
- Convert tech_stack_document from Text to JSONB

These columns store structured JSON data, not plain text.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = '002'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Change columns to JSONB
    op.alter_column(
        'generated_trd_documents',
        'api_specification',
        type_=JSONB,
        postgresql_using='api_specification::jsonb',
        nullable=True
    )

    op.alter_column(
        'generated_trd_documents',
        'database_schema',
        type_=JSONB,
        postgresql_using='database_schema::jsonb',
        nullable=True
    )

    op.alter_column(
        'generated_trd_documents',
        'tech_stack_document',
        type_=JSONB,
        postgresql_using='tech_stack_document::jsonb',
        nullable=True
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Revert to Text
    op.alter_column(
        'generated_trd_documents',
        'api_specification',
        type_=sa.Text,
        postgresql_using='api_specification::text',
        nullable=True
    )

    op.alter_column(
        'generated_trd_documents',
        'database_schema',
        type_=sa.Text,
        postgresql_using='database_schema::text',
        nullable=True
    )

    op.alter_column(
        'generated_trd_documents',
        'tech_stack_document',
        type_=sa.Text,
        postgresql_using='tech_stack_document::text',
        nullable=True
    )
