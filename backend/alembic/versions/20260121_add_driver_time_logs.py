"""add driver time logs table

Revision ID: 20260121_time_logs
Revises: 
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20260121_time_logs'
down_revision = None
depends_on = None


def upgrade():
    op.create_table(
        'driver_time_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('drivers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),  # available, offline, busy, break
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer, nullable=True),  # calculado ao finalizar
        sa.Column('date', sa.Date, nullable=False, index=True),  # para queries por data
        sa.Column('metadata', postgresql.JSONB, nullable=True),  # dados extras
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Índices para performance
    op.create_index('ix_driver_time_logs_driver_date', 'driver_time_logs', ['driver_id', 'date'])
    op.create_index('ix_driver_time_logs_status_date', 'driver_time_logs', ['status', 'date'])
    op.create_index('ix_driver_time_logs_driver_status', 'driver_time_logs', ['driver_id', 'status'])


def downgrade():
    op.drop_index('ix_driver_time_logs_driver_status')
    op.drop_index('ix_driver_time_logs_status_date')
    op.drop_index('ix_driver_time_logs_driver_date')
    op.drop_table('driver_time_logs')
