"""fix_schema_customer_id_and_validate_fks

Revision ID: b7887529d1b8
Revises: 20260128_auditlog_meta
Create Date: 2026-01-28 23:57:12.559340

Corrige divergências de schema:
1. Garante que orders.customer_id seja NOT NULL
2. Valida todas as foreign keys existem
3. Remove registros órfãos se necessário
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'b7887529d1b8'
down_revision: Union[str, None] = '20260128_auditlog_meta'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Corrige schema:
    1. Remove registros órfãos (orders sem customer válido)
    2. Garante que customer_id seja NOT NULL
    3. Valida todas as foreign keys
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Verificar se orders.customer_id permite NULL
    orders_cols = {c["name"]: c for c in inspector.get_columns("orders")}
    customer_id_nullable = orders_cols.get("customer_id", {}).get("nullable", False)
    
    if customer_id_nullable:
        # 1. Remover registros órfãos (orders sem customer válido)
        op.execute(text("""
            DELETE FROM orders 
            WHERE customer_id IS NULL 
            OR customer_id NOT IN (SELECT id FROM customers)
        """))
        
        # 2. Garantir que customer_id seja NOT NULL
        op.alter_column(
            "orders",
            "customer_id",
            nullable=False,
            existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
            existing_nullable=True,
        )
    
    # 3. Validar outras foreign keys importantes
    # order_items.order_id -> orders.id
    op.execute(text("""
        DELETE FROM order_items 
        WHERE order_id NOT IN (SELECT id FROM orders)
    """))
    
    # payments.order_id -> orders.id
    op.execute(text("""
        DELETE FROM payments 
        WHERE order_id NOT IN (SELECT id FROM orders)
    """))
    
    # deliveries.order_id -> orders.id
    op.execute(text("""
        DELETE FROM deliveries 
        WHERE order_id NOT IN (SELECT id FROM orders)
    """))
    
    # orders.approved_by -> users.id (se existir)
    if "approved_by" in orders_cols:
        op.execute(text("""
            UPDATE orders 
            SET approved_by = NULL 
            WHERE approved_by IS NOT NULL 
            AND approved_by NOT IN (SELECT id FROM users)
        """))
    
    # customer.tipo_preco_id -> tipos_preco.id (se existir)
    customer_cols = {c["name"]: c for c in inspector.get_columns("customers")}
    if "tipo_preco_id" in customer_cols:
        op.execute(text("""
            UPDATE customers 
            SET tipo_preco_id = NULL 
            WHERE tipo_preco_id IS NOT NULL 
            AND tipo_preco_id NOT IN (SELECT id FROM tipos_preco)
        """))


def downgrade() -> None:
    """
    Reverte alterações: permite NULL novamente em customer_id.
    Nota: Não restaura registros deletados.
    """
    op.alter_column(
        "orders",
        "customer_id",
        nullable=True,
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        existing_nullable=False,
    )
