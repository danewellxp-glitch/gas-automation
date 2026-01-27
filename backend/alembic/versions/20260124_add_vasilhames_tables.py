"""Add vasilhames (comodato) tables

Revision ID: 20260124_vasilhames
Revises: 20260123_precos
Create Date: 2026-01-24

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260124_vasilhames"
down_revision = "20260123_precos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==================== vasilhames ====================
    op.create_table(
        "vasilhames",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("codigo", sa.String(20), nullable=False, unique=True, comment="Código: P13, P45, P20, etc"),
        sa.Column("descricao", sa.String(100), nullable=False, comment="Descrição do vasilhame"),
        sa.Column("peso_kg", sa.Numeric(5, 2), nullable=False, comment="Peso do botijão vazio em kg"),
        sa.Column("valor_caucao", sa.Numeric(10, 2), nullable=False, comment="Valor da caução para venda"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "firebird_id",
            sa.Integer(),
            nullable=True,
            unique=True,
            comment="ID no Firebird (VASILHAMES.VASILHAME_ID)",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ==================== cliente_vasilhames ====================
    op.create_table(
        "cliente_vasilhames",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vasilhame_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vasilhames.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "quantidade",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Quantidade de botijões em posse do cliente",
        ),
        sa.Column(
            "valor_caucao_pago",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0.00"),
            comment="Valor total de caução pago pelo cliente",
        ),
        sa.Column(
            "data_primeiro_emprestimo",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data do primeiro empréstimo",
        ),
        sa.Column("observacoes", sa.Text(), nullable=True, comment="Observações sobre o comodato"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("customer_id", "vasilhame_id", name="uq_cliente_vasilhames_customer_vasilhame"),
    )

    op.create_index("ix_cliente_vasilhames_customer", "cliente_vasilhames", ["customer_id"])

    # ==================== movimentacoes_vasilhame ====================
    op.create_table(
        "movimentacoes_vasilhame",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "cliente_vasilhame_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cliente_vasilhames.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(20), nullable=False, comment="ENTRADA ou SAIDA"),
        sa.Column("quantidade", sa.Integer(), nullable=False, comment="Quantidade movimentada"),
        sa.Column(
            "valor_caucao",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0.00"),
            comment="Valor de caução cobrado/devolvido",
        ),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
            comment="Pedido relacionado",
        ),
        sa.Column("motivo", sa.String(100), nullable=False, comment="Motivo: venda, troca, devolucao, ajuste"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_movimentacoes_cliente", "movimentacoes_vasilhame", ["cliente_vasilhame_id"])
    op.create_index("ix_movimentacoes_order", "movimentacoes_vasilhame", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_movimentacoes_order", table_name="movimentacoes_vasilhame")
    op.drop_index("ix_movimentacoes_cliente", table_name="movimentacoes_vasilhame")
    op.drop_table("movimentacoes_vasilhame")

    op.drop_index("ix_cliente_vasilhames_customer", table_name="cliente_vasilhames")
    op.drop_table("cliente_vasilhames")

    op.drop_table("vasilhames")

