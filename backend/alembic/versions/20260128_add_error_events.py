"""add error_events table

Revision ID: 20260128_add_error_events
Revises: 20260128_add_user_password_flags
Create Date: 2026-01-28

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260128_add_error_events"
down_revision = "20260128_add_user_password_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("error_events"):
        op.create_table(
            "error_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("service", sa.String(length=50), nullable=False),
            sa.Column("error_type", sa.String(length=50), nullable=False),
            sa.Column("fingerprint", sa.String(length=128), nullable=False),
            sa.Column("message", sa.String(length=500), nullable=False),
            sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
            sa.Column("known_reason", sa.Text(), nullable=True),
            sa.Column("incident_title", sa.String(length=200), nullable=True),
            sa.Column("incident_id", sa.String(length=100), nullable=True),
        )

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("error_events")} if inspector.has_table("error_events") else set()
    if "ix_error_events_fingerprint" not in existing_indexes:
        op.create_index("ix_error_events_fingerprint", "error_events", ["fingerprint"], unique=True)
    if "ix_error_events_service" not in existing_indexes:
        op.create_index("ix_error_events_service", "error_events", ["service"], unique=False)
    if "ix_error_events_error_type" not in existing_indexes:
        op.create_index("ix_error_events_error_type", "error_events", ["error_type"], unique=False)
    if "ix_error_events_last_seen" not in existing_indexes:
        op.create_index("ix_error_events_last_seen", "error_events", ["last_seen"], unique=False)
    if "ix_error_events_status" not in existing_indexes:
        op.create_index("ix_error_events_status", "error_events", ["status"], unique=False)

    # drop server defaults (best-effort)
    try:
        op.alter_column("error_events", "count", server_default=None)
        op.alter_column("error_events", "status", server_default=None)
    except Exception:
        pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("error_events"):
        return

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("error_events")}
    for name in [
        "ix_error_events_status",
        "ix_error_events_last_seen",
        "ix_error_events_error_type",
        "ix_error_events_service",
        "ix_error_events_fingerprint",
    ]:
        if name in existing_indexes:
            op.drop_index(name, table_name="error_events")
    op.drop_table("error_events")

