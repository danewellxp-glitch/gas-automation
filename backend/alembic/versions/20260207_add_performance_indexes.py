"""Add performance indexes for dashboard and delivery queries

Revision ID: 20260207_perf_indexes
Revises: None (standalone - execute manually)
Create Date: 2026-02-07

Indexes adicionados:
- orders(created_at, status): usado em 30+ queries do dashboard
- orders(created_at, status, total_amount): covering index para somas financeiras
- deliveries(status, delivered_at, actual_delivery_minutes): metricas de entrega
- driver_time_logs(driver_id, date, status): metricas de motorista
"""
from alembic import op

revision = '20260207_perf_indexes'
down_revision = None


def upgrade() -> None:
    # Index mais critico: dashboard filtra por created_at + status em 30+ queries
    op.create_index(
        'ix_orders_created_at_status',
        'orders',
        ['created_at', 'status'],
        if_not_exists=True,
    )

    # Covering index para queries financeiras (evita table access para SUM(total_amount))
    op.create_index(
        'ix_orders_created_at_status_amount',
        'orders',
        ['created_at', 'status', 'total_amount'],
        if_not_exists=True,
    )

    # Metricas de performance de entrega (tempo medio, entregas no prazo)
    op.create_index(
        'ix_deliveries_status_delivered_minutes',
        'deliveries',
        ['status', 'delivered_at', 'actual_delivery_minutes'],
        if_not_exists=True,
    )

    # Metricas de motorista (filtra por driver_id + date + status)
    op.create_index(
        'ix_driver_time_logs_driver_date_status',
        'driver_time_logs',
        ['driver_id', 'date', 'status'],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index('ix_driver_time_logs_driver_date_status', table_name='driver_time_logs')
    op.drop_index('ix_deliveries_status_delivered_minutes', table_name='deliveries')
    op.drop_index('ix_orders_created_at_status_amount', table_name='orders')
    op.drop_index('ix_orders_created_at_status', table_name='orders')
