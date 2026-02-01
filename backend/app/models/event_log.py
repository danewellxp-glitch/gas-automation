"""
Modelo de Log de Eventos.
Auditoria e rastreamento de todas as ações do sistema.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EventLog(Base):
    """
    Modelo de Log de Eventos para auditoria.

    Attributes:
        event_type: Tipo do evento (order.created, payment.confirmed, etc)
        entity_type: Tipo da entidade (order, payment, customer, delivery)
        entity_id: ID da entidade relacionada
        actor_type: Tipo do ator (system, customer, operator, webhook)
        actor_id: ID do ator (telefone do cliente, id do operador, etc)
        payload: Dados completos do evento em JSON
        ip_address: IP de origem (se aplicável)
    """

    __tablename__ = "event_logs"

    # ID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Tipo do evento
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Tipo do evento (ex: order.created, payment.confirmed)"
    )

    # Entidade relacionada
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Tipo da entidade (order, payment, customer, delivery)"
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID da entidade relacionada"
    )

    # Ator (quem causou o evento)
    actor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="system",
        comment="Tipo do ator (system, customer, operator, webhook)"
    )
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="ID do ator (telefone, user_id, etc)"
    )

    # Dados do evento
    payload: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Dados completos do evento"
    )

    # Metadados
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="IP de origem"
    )

    # Timestamp (sem updated_at pois logs são imutáveis)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Índices
    __table_args__ = (
        Index("ix_event_logs_type_entity", "event_type", "entity_type"),
        Index("ix_event_logs_entity_created", "entity_type", "entity_id", "created_at"),
        # Índice para queries JSONB por phone (usado em chats.py)
        Index("ix_event_logs_payload_phone", payload["phone"].astext),
    )

    def __repr__(self) -> str:
        return f"<EventLog(type={self.event_type}, entity={self.entity_type}:{self.entity_id})>"


# Tipos de eventos padronizados
class EventTypes:
    """Constantes para tipos de eventos."""

    # Pedidos
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_PAID = "order.paid"
    ORDER_DISPATCHED = "order.dispatched"
    ORDER_DELIVERED = "order.delivered"
    ORDER_CANCELLED = "order.cancelled"

    # Pagamentos
    PAYMENT_CREATED = "payment.created"
    PAYMENT_PENDING = "payment.pending"
    PAYMENT_CONFIRMED = "payment.confirmed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    PAYMENT_WEBHOOK = "payment.webhook"

    # Entregas
    DELIVERY_ASSIGNED = "delivery.assigned"
    DELIVERY_PICKED_UP = "delivery.picked_up"
    DELIVERY_IN_TRANSIT = "delivery.in_transit"
    DELIVERY_DELIVERED = "delivery.delivered"
    DELIVERY_FAILED = "delivery.failed"

    # Clientes
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"

    # WhatsApp
    WHATSAPP_MESSAGE_RECEIVED = "whatsapp.message_received"
    WHATSAPP_MESSAGE_SENT = "whatsapp.message_sent"
    WHATSAPP_BUTTON_CLICKED = "whatsapp.button_clicked"

    # Sistema
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


class ActorTypes:
    """Constantes para tipos de atores."""
    SYSTEM = "system"
    CUSTOMER = "customer"
    OPERATOR = "operator"
    WEBHOOK = "webhook"
    ADMIN = "admin"
    SCHEDULER = "scheduler"
