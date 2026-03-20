"""add_business_settings

Revision ID: 20260320_add_business_settings
Revises: 8da4be72398d
Create Date: 2026-03-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
import json

revision = "20260320_add_business_settings"
down_revision = "8da4be72398d"
branch_labels = None
depends_on = None

DEFAULT_OPERATING_HOURS = {
    "monday":    {"open": "08:00", "close": "18:00", "enabled": True},
    "tuesday":   {"open": "08:00", "close": "18:00", "enabled": True},
    "wednesday": {"open": "08:00", "close": "18:00", "enabled": True},
    "thursday":  {"open": "08:00", "close": "18:00", "enabled": True},
    "friday":    {"open": "08:00", "close": "18:00", "enabled": True},
    "saturday":  {"open": "08:00", "close": "18:00", "enabled": True},
    "sunday":    {"open": "08:00", "close": "18:00", "enabled": False},
}

DEFAULT_MONTHLY_GOALS = {"revenue": 0.0, "orders": 0.0, "new_customers": 0.0}


def upgrade() -> None:
    op.create_table(
        "business_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operating_hours", JSONB(), nullable=False, server_default="{}"),
        sa.Column("monthly_goals",   JSONB(), nullable=False, server_default="{}"),
        sa.Column("enabled_bairros", JSONB(), nullable=False, server_default="[]"),
        sa.Column("promotions",      JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        f"""INSERT INTO business_settings (id, operating_hours, monthly_goals, enabled_bairros, promotions)
        VALUES (1, '{json.dumps(DEFAULT_OPERATING_HOURS)}'::jsonb, '{json.dumps(DEFAULT_MONTHLY_GOALS)}'::jsonb, '[]'::jsonb, '[]'::jsonb)
        ON CONFLICT (id) DO NOTHING"""
    )


def downgrade() -> None:
    op.drop_table("business_settings")
