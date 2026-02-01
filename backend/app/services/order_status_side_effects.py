"""
Side-effects quando o status do pedido muda (especialmente delivered).

Centraliza notificações WebSocket, event publisher, etc.
Usado por orders.py (PATCH status) e drivers.py (PUT delivery status delivered).
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.order import Order, OrderStatus
from app.services.event_publisher import event_publisher

logger = logging.getLogger(__name__)


async def notify_order_status_change(
    order: Order, old_status: str, new_status: str
) -> None:
    """Notifica cliente sobre mudança de status do pedido via event publisher."""
    try:
        event_map = {
            OrderStatus.PAID.value: "order.paid",
            OrderStatus.PREPARING.value: "order.preparing",
            OrderStatus.DISPATCHED.value: "order.dispatched",
            OrderStatus.DELIVERED.value: "order.delivered",
            OrderStatus.CANCELLED.value: "order.cancelled",
        }
        event_type = event_map.get(new_status)
        if not event_type:
            return

        customer_phone = order.customer.phone if order.customer else None
        customer_email = order.customer.email if order.customer else None

        await event_publisher.publish_order_event(
            event_type=event_type,
            order_id=str(order.id),
            order_number=order.order_number,
            customer_id=str(order.customer_id),
            customer_phone=customer_phone,
            customer_email=customer_email,
            status=new_status,
        )
    except Exception as e:
        logger.error(f"Erro ao notificar mudança de status: {e}", exc_info=True)


async def notify_operators_order_update(
    order: Order, old_status: str, new_status: str
) -> None:
    """Notifica operadores sobre atualização de pedido via WebSocket."""
    try:
        from app.api.websocket import UserRole, manager as ws_manager

        message = {
            "type": "order_update",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": new_status,
            "old_status": old_status,
            "customer_name": order.customer.name if order.customer else None,
            "total_amount": float(order.total_amount),
            "bairro": order.delivery_bairro,
        }

        if order.delivery_bairro:
            await ws_manager.broadcast_to_neighborhood(message, order.delivery_bairro)
        else:
            await ws_manager.broadcast_to_role(message, UserRole.OPERATOR)

        await ws_manager.broadcast_to_role(message, UserRole.ADMIN)
    except Exception as e:
        logger.error(f"Erro ao notificar operadores: {e}", exc_info=True)


async def on_order_delivered(order_id: UUID) -> None:
    """
    Side-effects quando um pedido é marcado como entregue (delivered).
    Usado quando o driver marca entrega como delivered no app mobile.
    Cria sessão própria para não depender da sessão da request.
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Order)
                .options(selectinload(Order.customer))
                .where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
            if not order:
                logger.warning(f"on_order_delivered: pedido {order_id} não encontrado")
                return

            await notify_order_status_change(order, "dispatched", "delivered")
            await notify_operators_order_update(order, "dispatched", "delivered")
        except Exception as e:
            logger.error(
                f"Erro em on_order_delivered para pedido {order_id}: {e}",
                exc_info=True,
            )
