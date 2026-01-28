"""add user password flags

Revision ID: 20260128_add_user_password_flags
Revises: 20260128_file_export
Create Date: 2026-01-28

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260128_add_user_password_flags"
down_revision = "20260128_file_export"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}

    if "must_change_password" not in cols:
        op.add_column(
            "users",
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
        # remover default server após backfill (mantém default no app)
        op.alter_column("users", "must_change_password", server_default=None)

    if "temp_password_issued_at" not in cols:
        op.add_column("users", sa.Column("temp_password_issued_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}

    if "temp_password_issued_at" in cols:
        op.drop_column("users", "temp_password_issued_at")
    if "must_change_password" in cols:
        op.drop_column("users", "must_change_password")

