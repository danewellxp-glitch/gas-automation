"""Add drivers and cargas tables

Revision ID: 20260124_drivers_cargas
Revises: 20260121_asaas_payment
Create Date: 2026-01-24

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260124_drivers_cargas"
down_revision = "20260121_asaas_payment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==================== drivers ====================
    op.create_table(
        "drivers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False, comment="Nome completo do entregador"),
        sa.Column("phone", sa.String(20), nullable=False, comment="Telefone para contato"),
        sa.Column("email", sa.String(100), nullable=True, comment="Email opcional"),
        sa.Column("vehicle_type", sa.String(50), nullable=True, comment="Tipo de veículo (moto, carro, etc.)"),
        sa.Column("license_plate", sa.String(10), nullable=True, comment="Placa do veículo"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'offline'"),
            comment="Status atual do entregador",
        ),
        sa.Column(
            "current_location",
            sa.JSON(),
            nullable=True,
            comment="Localização atual: {'latitude': float, 'longitude': float, 'timestamp': datetime}",
        ),
        sa.Column("rating", sa.Float(), nullable=False, server_default=sa.text("5.0"), comment="Avaliação média (0-5)"),
        sa.Column(
            "total_deliveries",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Total de entregas realizadas",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_online", sa.DateTime(timezone=True), nullable=True, comment="Última vez que ficou online"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("phone", name="uq_drivers_phone"),
    )

    op.create_index("ix_drivers_phone", "drivers", ["phone"])
    op.create_index("ix_drivers_status_active", "drivers", ["status", "is_active"])

    # ==================== cargas_veiculo ====================
    op.create_table(
        "cargas_veiculo",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drivers.id"),
            nullable=False,
        ),
        sa.Column("data_saida", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_retorno", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'criada'"),
            comment="Status: criada, em_rota, finalizada",
        ),
        sa.Column("observacoes", sa.String(500), nullable=True, comment="Observações gerais"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_cargas_driver_status", "cargas_veiculo", ["driver_id", "status"])
    op.create_index("ix_cargas_data_saida", "cargas_veiculo", ["data_saida"])
    op.create_index("ix_cargas_veiculo_driver_id", "cargas_veiculo", ["driver_id"])
    op.create_index("ix_cargas_veiculo_status", "cargas_veiculo", ["status"])

    # ==================== carga_itens ====================
    op.create_table(
        "carga_itens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "carga_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cargas_veiculo.id"),
            nullable=False,
        ),
        sa.Column(
            "produto_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("qtd_saida", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("qtd_retorno_cheio", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("qtd_retorno_vazio", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("qtd_vendida", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_carga_itens_carga_produto", "carga_itens", ["carga_id", "produto_id"])
    op.create_index("ix_carga_itens_carga_id", "carga_itens", ["carga_id"])
    op.create_index("ix_carga_itens_produto_id", "carga_itens", ["produto_id"])


def downgrade() -> None:
    op.drop_index("ix_carga_itens_produto_id", table_name="carga_itens")
    op.drop_index("ix_carga_itens_carga_id", table_name="carga_itens")
    op.drop_index("ix_carga_itens_carga_produto", table_name="carga_itens")
    op.drop_table("carga_itens")

    op.drop_index("ix_cargas_veiculo_status", table_name="cargas_veiculo")
    op.drop_index("ix_cargas_veiculo_driver_id", table_name="cargas_veiculo")
    op.drop_index("ix_cargas_data_saida", table_name="cargas_veiculo")
    op.drop_index("ix_cargas_driver_status", table_name="cargas_veiculo")
    op.drop_table("cargas_veiculo")

    op.drop_index("ix_drivers_status_active", table_name="drivers")
    op.drop_index("ix_drivers_phone", table_name="drivers")
    op.drop_table("drivers")

