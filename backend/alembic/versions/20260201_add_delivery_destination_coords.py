"""add delivery_destination_lat/lng for GPS proximity tracking

Revision ID: 20260201_gps
Revises: a1b2c3d4e5f6
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260201_gps'
down_revision: Union[str, None] = '20260128_approved_by'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deliveries',
        sa.Column(
            'delivery_destination_lat',
            sa.Float(),
            nullable=True,
            comment='Latitude do destino (geocoding) para proximidade'
        )
    )
    op.add_column(
        'deliveries',
        sa.Column(
            'delivery_destination_lng',
            sa.Float(),
            nullable=True,
            comment='Longitude do destino (geocoding) para proximidade'
        )
    )
    op.add_column(
        'deliveries',
        sa.Column(
            'arrived_whatsapp_sent',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='Se WhatsApp "1 minuto" já foi enviado'
        )
    )


def downgrade() -> None:
    op.drop_column('deliveries', 'delivery_destination_lat')
    op.drop_column('deliveries', 'delivery_destination_lng')
    op.drop_column('deliveries', 'arrived_whatsapp_sent')
