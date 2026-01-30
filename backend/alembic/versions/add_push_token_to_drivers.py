"""add push_token to drivers

Revision ID: a1b2c3d4e5f6
Revises: 22be62588e1e
Create Date: 2026-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '22be62588e1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('drivers', sa.Column('push_token', sa.String(255), nullable=True, comment='FCM token para push notifications'))


def downgrade() -> None:
    op.drop_column('drivers', 'push_token')
