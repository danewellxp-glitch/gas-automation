"""add audit log request metadata

Revision ID: 20260128_auditlog_meta
Revises: 20260128_add_error_events
Create Date: 2026-01-28

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260128_auditlog_meta"
down_revision = "20260128_add_error_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("auditlog")}

    if "ip_address" not in cols:
        op.add_column("auditlog", sa.Column("ip_address", sa.String(length=64), nullable=True))

    if "user_agent" not in cols:
        op.add_column("auditlog", sa.Column("user_agent", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("auditlog")}

    if "user_agent" in cols:
        op.drop_column("auditlog", "user_agent")
    if "ip_address" in cols:
        op.drop_column("auditlog", "ip_address")

