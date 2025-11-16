"""Initial schema for Tech Spec Agent

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-14 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Tech Spec Agent tables."""

    # Create tech_spec_sessions table
    op.create_table(
        'tech_spec_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('design_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('current_stage', sa.String(length=50), nullable=True),
        sa.Column('progress_percentage', sa.Float(), nullable=True),
        sa.Column('session_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('websocket_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'in_progress', 'paused', 'completed', 'failed')", name='valid_status'),
        sa.CheckConstraint('progress_percentage >= 0 AND progress_percentage <= 100', name='valid_progress'),
        sa.ForeignKeyConstraint(['design_job_id'], ['shared.design_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_tech_spec_sessions_created_at', 'tech_spec_sessions', ['created_at'], unique=False)
    op.create_index('ix_tech_spec_sessions_design_job_id', 'tech_spec_sessions', ['design_job_id'], unique=False)
    op.create_index('ix_tech_spec_sessions_project_id', 'tech_spec_sessions', ['project_id'], unique=False)
    op.create_index('ix_tech_spec_sessions_status', 'tech_spec_sessions', ['status'], unique=False)
    op.create_index('idx_session_status_created', 'tech_spec_sessions', ['status', sa.text('created_at DESC')], unique=False)

    # Create tech_research table
    op.create_table(
        'tech_research',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('technology_category', sa.String(length=50), nullable=False),
        sa.Column('gap_description', sa.Text(), nullable=True),
        sa.Column('researched_options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('selected_technology', sa.String(length=100), nullable=True),
        sa.Column('selection_reasoning', sa.Text(), nullable=True),
        sa.Column('decision_timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['tech_spec_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_tech_research_session_id', 'tech_research', ['session_id'], unique=False)
    op.create_index('ix_tech_research_technology_category', 'tech_research', ['technology_category'], unique=False)
    op.create_index('idx_research_session_category', 'tech_research', ['session_id', 'technology_category'], unique=False)

    # Create tech_conversations table
    op.create_table(
        'tech_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('research_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.CheckConstraint("role IN ('user', 'agent', 'system')", name='valid_role'),
        sa.ForeignKeyConstraint(['research_id'], ['tech_research.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['tech_spec_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_tech_conversations_session_id', 'tech_conversations', ['session_id'], unique=False)
    op.create_index('ix_tech_conversations_timestamp', 'tech_conversations', ['timestamp'], unique=False)
    op.create_index('idx_conversation_session_timestamp', 'tech_conversations', ['session_id', sa.text('timestamp DESC')], unique=False)

    # Create generated_trd_documents table
    op.create_table(
        'generated_trd_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trd_content', sa.Text(), nullable=True),
        sa.Column('api_specification', sa.Text(), nullable=True),
        sa.Column('database_schema', sa.Text(), nullable=True),
        sa.Column('architecture_diagram', sa.Text(), nullable=True),
        sa.Column('tech_stack_document', sa.Text(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('validation_report', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['tech_spec_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_generated_trd_documents_quality_score', 'generated_trd_documents', ['quality_score'], unique=False)
    op.create_index('ix_generated_trd_documents_session_id', 'generated_trd_documents', ['session_id'], unique=False)

    # Create agent_error_logs table
    op.create_table(
        'agent_error_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node', sa.String(length=100), nullable=False),
        sa.Column('error_type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('recovered', sa.Boolean(), nullable=True),
        sa.Column('recovery_strategy', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('retry_count >= 0', name='valid_retry_count'),
        sa.ForeignKeyConstraint(['session_id'], ['tech_spec_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_agent_error_logs_node', 'agent_error_logs', ['node'], unique=False)
    op.create_index('ix_agent_error_logs_recovered', 'agent_error_logs', ['recovered'], unique=False)
    op.create_index('ix_agent_error_logs_session_id', 'agent_error_logs', ['session_id'], unique=False)
    op.create_index('idx_error_node_recovered', 'agent_error_logs', ['node', 'recovered'], unique=False)


def downgrade() -> None:
    """Drop Tech Spec Agent tables."""

    op.drop_index('idx_error_node_recovered', table_name='agent_error_logs')
    op.drop_index('ix_agent_error_logs_session_id', table_name='agent_error_logs')
    op.drop_index('ix_agent_error_logs_recovered', table_name='agent_error_logs')
    op.drop_index('ix_agent_error_logs_node', table_name='agent_error_logs')
    op.drop_table('agent_error_logs')

    op.drop_index('ix_generated_trd_documents_session_id', table_name='generated_trd_documents')
    op.drop_index('ix_generated_trd_documents_quality_score', table_name='generated_trd_documents')
    op.drop_table('generated_trd_documents')

    op.drop_index('idx_conversation_session_timestamp', table_name='tech_conversations')
    op.drop_index('ix_tech_conversations_timestamp', table_name='tech_conversations')
    op.drop_index('ix_tech_conversations_session_id', table_name='tech_conversations')
    op.drop_table('tech_conversations')

    op.drop_index('idx_research_session_category', table_name='tech_research')
    op.drop_index('ix_tech_research_technology_category', table_name='tech_research')
    op.drop_index('ix_tech_research_session_id', table_name='tech_research')
    op.drop_table('tech_research')

    op.drop_index('idx_session_status_created', table_name='tech_spec_sessions')
    op.drop_index('ix_tech_spec_sessions_status', table_name='tech_spec_sessions')
    op.drop_index('ix_tech_spec_sessions_project_id', table_name='tech_spec_sessions')
    op.drop_index('ix_tech_spec_sessions_design_job_id', table_name='tech_spec_sessions')
    op.drop_index('ix_tech_spec_sessions_created_at', table_name='tech_spec_sessions')
    op.drop_table('tech_spec_sessions')
