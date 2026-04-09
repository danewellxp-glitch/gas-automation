"""
Order Service - Gerenciamento de Pedidos
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.customer import Customer


async def validate_order_before_create(
    db: AsyncSession,
    customer_id,
    items: list,
) -> list[str]:
    """
    Valida dados antes de criar um pedido.
    Retorna lista de erros (vazia = OK).
    """
    from sqlalchemy import text

    errors = []

    if not items:
        errors.append("Pedido deve ter pelo menos um item.")

    if customer_id:
        result = await db.execute(
            text("SELECT id FROM customers WHERE id = :cid AND deleted_at IS NULL"),
            {"cid": str(customer_id)},
        )
        if not result.fetchone():
            errors.append(f"Cliente {customer_id} não encontrado ou inativo.")

    for idx, item in enumerate(items):
        product_id = item.get("product_id") or item.get("produto_id")
        qty = item.get("quantidade") or item.get("quantity", 0)
        if not product_id:
            errors.append(f"Item {idx + 1}: product_id ausente.")
        if not qty or qty <= 0:
            errors.append(f"Item {idx + 1}: quantidade inválida ({qty}).")

    return errors


class OrderService:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> List[Order]:
        """Lista todos os pedidos"""
        return self.session.exec(select(Order)).all()

    def list_pending(self) -> List[Order]:
        """Lista pedidos pendentes"""
        return self.session.exec(
            select(Order).where(Order.status == OrderStatus.PENDING.value)
        ).all()

    def list_in_delivery(self) -> List[Order]:
        """Lista pedidos em entrega (dispatched ou delivered)"""
        return self.session.exec(
            select(Order).where(Order.status.in_([
                OrderStatus.DISPATCHED.value,
                OrderStatus.DELIVERED.value
            ]))
        ).all()

    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Busca pedido por ID"""
        return self.session.get(Order, order_id)

    def create(self, customer: Customer, items: List[dict], **kwargs) -> Order:
        """Cria novo pedido"""
        # Calcular total
        total = sum(item.get('preco', 0) * item.get('quantidade', 1) for item in items)

        order = Order(
            customer=customer,
            total=total,
            **kwargs
        )

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        # Criar itens do pedido
        for item_data in items:
            from app.models.order import OrderItem
            item = OrderItem(
                order_id=order.id,
                product_id=item_data['product_id'],
                quantity=item_data['quantidade'],
                unit_price=item_data.get('preco', 0),
                total=item_data.get('preco', 0) * item_data.get('quantidade', 1)
            )
            self.session.add(item)

        self.session.commit()
        return order

    def confirm(self, order_id: int) -> Optional[Order]:
        """Confirma pedido (muda para PAID)"""
        order = self.get_by_id(order_id)
        if not order:
            return None

        order.status = OrderStatus.PAID.value
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def cancel(self, order_id: int, reason: str = "") -> Optional[Order]:
        """Cancela pedido"""
        order = self.get_by_id(order_id)
        if not order:
            return None

        order.status = OrderStatus.CANCELLED.value
        order.cancellation_reason = reason
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order