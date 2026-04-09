"""merge two heads: nota_fiscal + driver_segmentos

Revision ID: 20260329_merge_heads
Revises: 20260325_add_nota_fiscal_tables, 20260329_driver_segmentos
Create Date: 2026-03-29

"""
from typing import Sequence, Union

revision: str = '20260329_merge_heads'
down_revision: Union[str, tuple] = (
    '20260325_add_nota_fiscal_tables',
    '20260329_driver_segmentos',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
