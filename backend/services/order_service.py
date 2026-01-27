"""
Order Service - Gerenciamento de Pedidos
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.customer import Customer


class OrderService:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> List[Order]:
        """Lista todos os pedidos"""
        return self.session.exec(select(Order)).all()

    def list_pending(self) -> List[Order]:
        """Lista pedidos pendentes"""
        return self.session.exec(
            select(Order).where(Order.status == OrderStatus.PENDING)
        ).all()

    def list_in_delivery(self) -> List[Order]:
        """Lista pedidos em entrega"""
        return self.session.exec(
            select(Order).where(Order.status.in_([
                OrderStatus.IN_DELIVERY,
                OrderStatus.OUT_FOR_DELIVERY,
                OrderStatus.DELIVERED
            ]))
        ).all()

    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Busca pedido por ID"""
        return self.session.get(Order, order_id)

    def create(self, customer: Customer, items: List[dict], **kwargs) -> Order:
        """Cria novo pedido com cálculo automático de totais"""
        order = Order(
            customer=customer,
            **kwargs
        )

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        # Criar itens do pedido e calcular totais
        subtotal = 0
        for item_data in items:
            quantity = item_data.get('quantidade', item_data.get('quantity', 1))
            unit_price = item_data.get('preco', item_data.get('unit_price', 0))

            from app.models.order import OrderItem
            item = OrderItem(
                order_id=order.id,
                product_id=item_data['product_id'],
                quantity=quantity,
                unit_price=unit_price,
                total=unit_price * quantity
            )
            self.session.add(item)
            subtotal += unit_price * quantity

        # Atualizar totais no pedido
        delivery_fee = kwargs.get('delivery_fee', kwargs.get('taxa_entrega', 0))
        discount = kwargs.get('discount', kwargs.get('desconto', 0))

        order.subtotal = subtotal
        order.delivery_fee = delivery_fee
        order.discount = discount
        order.total = subtotal + delivery_fee - discount

        self.session.add(order)
        self.session.commit()
        return order

    def confirm(self, order_id: int) -> Optional[Order]:
        """Confirma pedido"""
        order = self.get_by_id(order_id)
        if not order:
            return None

        order.status = OrderStatus.CONFIRMED
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def cancel(self, order_id: int, reason: str = "") -> Optional[Order]:
        """Cancela pedido"""
        order = self.get_by_id(order_id)
        if not order:
            return None

        order.status = OrderStatus.CANCELLED
        order.notes = f"Cancelado: {reason}"
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order