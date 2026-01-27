"""update_user_model

Revision ID: 22be62588e1e
Revises: e68a4ae2e2ea
Create Date: 2026-01-18 21:33:49.069340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22be62588e1e'
down_revision: Union[str, None] = 'e68a4ae2e2ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
