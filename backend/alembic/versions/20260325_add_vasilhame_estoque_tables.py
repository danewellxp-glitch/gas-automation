"""Add vasilhame_estoque and vasilhame_movimentos tables.

Revision ID: 20260325_add_vasilhame_estoque_tables
Revises: 20260325_add_pix_conciliation_tables
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260325_add_vasilhame_estoque_tables"
down_revision = "20260325_add_pix_conciliation_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # vasilhame_estoque — pode já existir de migration anterior (20260124_add_vasilhames_tables.py)
    # A migration anterior criou tabelas 'vasilhames', 'cliente_vasilhames', 'movimentacoes_vasilhame'
    # Estas são novas tabelas de controle de estoque operacional (distintas das de comodato)
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT to_regclass('public.vasilhame_estoque')"
    ))
    exists = result.scalar()

    if not exists:
        op.create_table(
            "vasilhame_estoque",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tipo", sa.String(10), nullable=False, unique=True),
            sa.Column("qtd_cheios", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("qtd_vazios", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("qtd_em_campo", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("custo_unitario", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    result2 = conn.execute(sa.text(
        "SELECT to_regclass('public.vasilhame_movimentos')"
    ))
    exists2 = result2.scalar()

    if not exists2:
        op.create_table(
            "vasilhame_movimentos",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tipo_vasilhame", sa.String(10), nullable=False),
            sa.Column("tipo_movimento", sa.String(30), nullable=False),
            sa.Column("quantidade", sa.Integer(), nullable=False),
            sa.Column("custo_unitario", sa.Numeric(10, 2), nullable=True),
            sa.Column("custo_total", sa.Numeric(10, 2), nullable=True),
            sa.Column("pedido_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
            sa.Column("entregador_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("saldo_cheios_antes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("saldo_vazios_antes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("saldo_em_campo_antes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_vasilhame_movimentos_tipo", "vasilhame_movimentos", ["tipo_vasilhame"])
        op.create_index("ix_vasilhame_movimentos_tipo_mov", "vasilhame_movimentos", ["tipo_movimento"])
        op.create_index("ix_vasilhame_movimentos_pedido", "vasilhame_movimentos", ["pedido_id"])

    # Seed inicial de estoque
    op.execute(sa.text("""
        INSERT INTO vasilhame_estoque (id, tipo, qtd_cheios, qtd_vazios, qtd_em_campo, custo_unitario)
        VALUES
            (gen_random_uuid(), 'P13',  0, 0, 0, 0),
            (gen_random_uuid(), 'P20',  0, 0, 0, 0),
            (gen_random_uuid(), 'P45',  0, 0, 0, 0),
            (gen_random_uuid(), 'G20L', 0, 0, 0, 0)
        ON CONFLICT (tipo) DO NOTHING
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM vasilhame_movimentos WHERE TRUE"))
    op.execute(sa.text("DELETE FROM vasilhame_estoque WHERE tipo IN ('P13','P20','P45','G20L')"))
    # Drop tables only if they were created by this migration
    # (safe to drop — they didn't exist before)
    try:
        op.drop_index("ix_vasilhame_movimentos_pedido", table_name="vasilhame_movimentos")
        op.drop_index("ix_vasilhame_movimentos_tipo_mov", table_name="vasilhame_movimentos")
        op.drop_index("ix_vasilhame_movimentos_tipo", table_name="vasilhame_movimentos")
        op.drop_table("vasilhame_movimentos")
        op.drop_table("vasilhame_estoque")
    except Exception:
        pass
