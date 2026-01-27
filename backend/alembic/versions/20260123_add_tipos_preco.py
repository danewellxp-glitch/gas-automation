"""Add tipos_preco and produto_precos tables

Revision ID: 20260123_precos
Revises: 20260123_tipo_op
Create Date: 2026-01-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '20260123_precos'
down_revision = '20260123_tipo_op'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Criar tabela tipos_preco
    op.create_table(
        'tipos_preco',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('codigo', sa.String(20), unique=True, nullable=False),
        sa.Column('descricao', sa.String(100), nullable=False),
        sa.Column('percentual_desconto', sa.Numeric(5, 2), nullable=False, server_default='0.00'),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('firebird_id', sa.Integer(), unique=True, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Criar tabela produto_precos
    op.create_table(
        'produto_precos',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('produto_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tipo_preco_id', UUID(as_uuid=True), sa.ForeignKey('tipos_preco.id', ondelete='CASCADE'), nullable=False),
        sa.Column('preco', sa.Numeric(10, 2), nullable=False),
        sa.Column('vigencia_inicio', sa.Date(), nullable=False),
        sa.Column('vigencia_fim', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Índice para busca de preços
    op.create_index(
        'ix_produto_precos_busca',
        'produto_precos',
        ['produto_id', 'tipo_preco_id', 'vigencia_inicio']
    )

    # Adicionar coluna tipo_preco_id no customers
    op.add_column(
        'customers',
        sa.Column(
            'tipo_preco_id',
            UUID(as_uuid=True),
            sa.ForeignKey('tipos_preco.id', ondelete='SET NULL'),
            nullable=True
        )
    )

    # Inserir tipos de preço padrão
    op.execute("""
        INSERT INTO tipos_preco (id, codigo, descricao, percentual_desconto, firebird_id)
        VALUES
            (gen_random_uuid(), 'varejo', 'Varejo', 0.00, 1),
            (gen_random_uuid(), 'atacado', 'Atacado', 5.00, 2),
            (gen_random_uuid(), 'funcionario', 'Funcionário', 15.00, 3),
            (gen_random_uuid(), 'revenda', 'Revenda', 20.00, 4)
    """)


def downgrade() -> None:
    op.drop_column('customers', 'tipo_preco_id')
    op.drop_index('ix_produto_precos_busca')
    op.drop_table('produto_precos')
    op.drop_table('tipos_preco')
