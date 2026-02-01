"""
Modelo de Entrega.
Gerencia a alocação e status das entregas.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.order import Order


class DeliveryStatus(str, enum.Enum):
    """Status da entrega."""
    PENDING = "pending"           # Aguardando alocação
    ASSIGNED = "assigned"         # Entregador alocado
    PICKED_UP = "picked_up"       # Retirado para entrega
    IN_TRANSIT = "in_transit"     # Em trânsito
    ARRIVED = "arrived"           # Chegou no destino
    DELIVERED = "delivered"       # Entregue
    FAILED = "failed"             # Falha na entrega
    RETURNED = "returned"         # Devolvido


class Delivery(BaseModel):
    """
    Modelo de Entrega.

    Attributes:
        order_id: FK para pedido
        driver_id: ID do entregador (futuro: FK para tabela drivers)
        driver_name: Nome do entregador
        driver_phone: Telefone do entregador
        status: Status atual da entrega
        bairro: Bairro de destino (para alocação)
        estimated_minutes: Previsão em minutos
        actual_delivery_time: Tempo real de entrega
        notes: Observações
    """

    __tablename__ = "deliveries"

    # Relacionamento com pedido
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Entregador (simplificado para MVP)
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID do entregador (futuro: FK para drivers)"
    )
    driver_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Nome do entregador"
    )
    driver_phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Telefone do entregador"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default=DeliveryStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Localização
    bairro: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Bairro de destino"
    )

    # Tempos
    estimated_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=40,
        comment="Previsão de entrega em minutos"
    )
    actual_delivery_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Tempo real de entrega em minutos"
    )

    # Timestamps de cada etapa
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    picked_up_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    in_transit_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    arrived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Observações
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Observações da entrega"
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Motivo da falha (se aplicável)"
    )

    # Coordenadas GPS (futuro)
    last_location: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Última localização: {lat, lng, timestamp}"
    )

    # Destino geocodificado (para proximidade / auto-arrived)
    delivery_destination_lat: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Latitude do endereço de entrega (geocoding)"
    )
    delivery_destination_lng: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Longitude do endereço de entrega (geocoding)"
    )
    arrived_whatsapp_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Se WhatsApp '1 minuto' já foi enviado ao cliente"
    )

    # Relacionamento
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="delivery",
    )

    # Índices
    __table_args__ = (
        Index("ix_deliveries_status_bairro", "status", "bairro"),
        Index("ix_deliveries_driver_status", "driver_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Delivery(id={self.id}, status={self.status}, driver={self.driver_name})>"

    def update_status(self, new_status: str) -> None:
        """Atualiza status e timestamp correspondente."""
        from datetime import timezone
        now = datetime.now(timezone.utc)

        self.status = new_status

        if new_status == DeliveryStatus.ASSIGNED.value:
            self.assigned_at = now
        elif new_status == DeliveryStatus.PICKED_UP.value:
            self.picked_up_at = now
        elif new_status == DeliveryStatus.IN_TRANSIT.value:
            self.in_transit_at = now
        elif new_status == DeliveryStatus.ARRIVED.value:
            self.arrived_at = now
        elif new_status == DeliveryStatus.DELIVERED.value:
            self.delivered_at = now
            # Calcular tempo real de entrega
            if self.assigned_at:
                delta = now - self.assigned_at
                self.actual_delivery_minutes = int(delta.total_seconds() / 60)

    @property
    def is_active(self) -> bool:
        """Verifica se a entrega está em andamento."""
        return self.status in [
            DeliveryStatus.ASSIGNED.value,
            DeliveryStatus.PICKED_UP.value,
            DeliveryStatus.IN_TRANSIT.value,
            DeliveryStatus.ARRIVED.value,
        ]

    @property
    def is_completed(self) -> bool:
        """Verifica se a entrega foi finalizada."""
        return self.status in [
            DeliveryStatus.DELIVERED.value,
            DeliveryStatus.FAILED.value,
            DeliveryStatus.RETURNED.value,
        ]
