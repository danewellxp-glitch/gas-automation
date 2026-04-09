"""
Migration: add_categoria_produto_galao
Adiciona campos de categoria, volume_litros e requer_retorno_vasilhame à tabela products.
Suporte ao Galão de Água 20L (G20L) como produto de primeira classe.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260325_add_categoria_produto_galao"
down_revision = "20260325_add_product_price_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adiciona campo categoria com default 'gas' para não quebrar registros existentes
    op.add_column(
        "products",
        sa.Column(
            "categoria",
            sa.String(20),
            nullable=False,
            server_default="gas",
            comment="Categoria: gas, agua, outro",
        ),
    )

    # Torna weight_kg nullable (galão de água não tem peso em kg relevante)
    op.alter_column("products", "weight_kg", nullable=True)

    # Adiciona volume_litros (nullable — usado apenas para galões)
    op.add_column(
        "products",
        sa.Column(
            "volume_litros",
            sa.Integer(),
            nullable=True,
            comment="Volume em litros para galões (ex: 20 para G20L)",
        ),
    )

    # Adiciona requer_retorno_vasilhame com default True
    op.add_column(
        "products",
        sa.Column(
            "requer_retorno_vasilhame",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Se o vasilhame vazio deve retornar",
        ),
    )

    # Índice por categoria para filtros de listagem
    op.create_index("ix_products_categoria", "products", ["categoria"])

    # Atualiza produtos de gás existentes com volume_litros correto
    op.execute(
        "UPDATE products SET volume_litros = 13 WHERE code = 'P13' AND categoria = 'gas'"
    )
    op.execute(
        "UPDATE products SET volume_litros = 20 WHERE code = 'P20' AND categoria = 'gas'"
    )
    op.execute(
        "UPDATE products SET volume_litros = 45 WHERE code = 'P45' AND categoria = 'gas'"
    )


def downgrade() -> None:
    op.drop_index("ix_products_categoria", table_name="products")
    op.drop_column("products", "requer_retorno_vasilhame")
    op.drop_column("products", "volume_litros")
    op.alter_column("products", "weight_kg", nullable=False)
    op.drop_column("products", "categoria")
