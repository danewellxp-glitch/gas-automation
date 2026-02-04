"""add tipo_documento to customers and customer_id to users

Revision ID: 20260204_customer_user
Revises: a1b2c3d4e5f6, 20260201_gps
Create Date: 2026-02-04

Adiciona:
- tipo_documento (PF/PJ) na tabela customers
- indice unico em cpf_cnpj (permite NULL)
- customer_id na tabela users (FK para customers)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '20260204_customer_user'
down_revision: Union[str, Sequence[str]] = ('a1b2c3d4e5f6', '20260201_gps', 'b7887529d1b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Adicionar tipo_documento na tabela customers
    op.add_column(
        'customers',
        sa.Column(
            'tipo_documento',
            sa.String(2),
            nullable=True,
            server_default='PF',
            comment='Tipo: PF (pessoa fisica) ou PJ (pessoa juridica)'
        )
    )

    # 2. Preencher tipo_documento baseado no tamanho do cpf_cnpj existente
    op.execute("""
        UPDATE customers
        SET tipo_documento = CASE
            WHEN LENGTH(cpf_cnpj) = 14 THEN 'PJ'
            ELSE 'PF'
        END
    """)

    # 3. Criar indice unico parcial no cpf_cnpj (permite multiplos NULLs)
    op.create_index(
        'ix_customers_cpf_cnpj_unique',
        'customers',
        ['cpf_cnpj'],
        unique=True,
        postgresql_where=sa.text('cpf_cnpj IS NOT NULL')
    )

    # 4. Adicionar customer_id na tabela users
    op.add_column(
        'users',
        sa.Column(
            'customer_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='FK para customer vinculado (opcional)'
        )
    )

    # 5. Criar indice no customer_id
    op.create_index(
        'ix_users_customer_id',
        'users',
        ['customer_id']
    )

    # 6. Criar foreign key
    op.create_foreign_key(
        'fk_users_customer',
        'users',
        'customers',
        ['customer_id'],
        ['id'],
        onupdate='CASCADE',
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remover na ordem inversa
    op.drop_constraint('fk_users_customer', 'users', type_='foreignkey')
    op.drop_index('ix_users_customer_id', table_name='users')
    op.drop_column('users', 'customer_id')
    op.drop_index('ix_customers_cpf_cnpj_unique', table_name='customers')
    op.drop_column('customers', 'tipo_documento')
