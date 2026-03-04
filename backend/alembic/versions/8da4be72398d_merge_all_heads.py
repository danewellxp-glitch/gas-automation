"""merge_all_heads

Revision ID: 8da4be72398d
Revises: 20260201_gps, 20260205_fix_botcontext, 20260206_conv_snapshots, 20260207_perf_indexes, 20260209_driver_bairro, 20260213_idempotency_lid, a1b2c3d4e5f6, b7887529d1b8
Create Date: 2026-03-02 18:10:48.839142

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8da4be72398d'
down_revision: Union[str, None] = ('20260201_gps', '20260205_fix_botcontext', '20260206_conv_snapshots', '20260207_perf_indexes', '20260209_driver_bairro', '20260213_idempotency_lid', 'a1b2c3d4e5f6', 'b7887529d1b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
