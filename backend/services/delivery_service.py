"""
Delivery Service - Gerenciamento de Entregas
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryStatus
from app.models.order import Order


class DeliveryService:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> List[Delivery]:
        """Lista todas as entregas"""
        return self.session.exec(select(Delivery)).all()

    def list_active(self) -> List[Delivery]:
        """Lista entregas ativas"""
        return self.session.exec(
            select(Delivery).where(
                Delivery.status.in_([
                    DeliveryStatus.ASSIGNED.value,
                    DeliveryStatus.PICKED_UP.value,
                    DeliveryStatus.IN_TRANSIT.value,
                    DeliveryStatus.ARRIVED.value
                ])
            )
        ).all()

    def get_by_id(self, delivery_id: int) -> Optional[Delivery]:
        """Busca entrega por ID"""
        return self.session.get(Delivery, delivery_id)

    def create_delivery(self, order_id: int, driver_id: int, estimated_time: Optional[int] = 30) -> Optional[Delivery]:
        """Cria entrega para pedido com tempo estimado"""
        order = self.session.get(Order, order_id)
        if not order:
            return None

        # Verificar se já existe entrega para este pedido
        existing = self.session.exec(
            select(Delivery).where(Delivery.order_id == order_id)
        ).first()
        if existing:
            return existing

        delivery = Delivery(
            order_id=order_id,
            driver_id=driver_id,
            status=DeliveryStatus.ASSIGNED.value,
            bairro=order.bairro_entrega,
            estimated_minutes=estimated_time
        )

        # Atualizar status do pedido
        order.status = "assigned"

        self.session.add(delivery)
        self.session.add(order)
        self.session.commit()
        self.session.refresh(delivery)
        return delivery

    def get_available_driver(self) -> Optional[Driver]:
        """Busca entregador disponível mais próximo"""
        from app.models.driver import Driver, DriverStatus

        return self.session.exec(
            select(Driver).where(
                Driver.status == DriverStatus.AVAILABLE.value,
                Driver.is_active == True
            )
        ).first()

    def get_deliveries_by_driver(self, driver_id: int) -> List[Delivery]:
        """Lista entregas ativas de um entregador"""
        return self.session.exec(
            select(Delivery).where(
                Delivery.driver_id == driver_id,
                Delivery.status.in_([
                    DeliveryStatus.ASSIGNED.value,
                    DeliveryStatus.PICKED_UP.value,
                    DeliveryStatus.IN_TRANSIT.value,
                    DeliveryStatus.ARRIVED.value
                ])
            )
        ).all()

    def start_delivery(self, delivery_id: int) -> Optional[Delivery]:
        """Inicia entrega (saiu para entrega)"""
        delivery = self.get_by_id(delivery_id)
        if not delivery:
            return None

        delivery.status = DeliveryStatus.IN_TRANSIT.value
        delivery.update_status(DeliveryStatus.IN_TRANSIT.value)

        # Atualizar pedido
        delivery.order.status = "out_for_delivery"

        self.session.add(delivery)
        self.session.add(delivery.order)
        self.session.commit()
        self.session.refresh(delivery)
        return delivery

    def complete_delivery(self, delivery_id: int) -> Optional[Delivery]:
        """Finaliza entrega"""
        delivery = self.get_by_id(delivery_id)
        if not delivery:
            return None

        delivery.status = DeliveryStatus.DELIVERED.value
        delivery.update_status(DeliveryStatus.DELIVERED.value)

        # Atualizar pedido
        delivery.order.status = "delivered"

        self.session.add(delivery)
        self.session.add(delivery.order)
        self.session.commit()
        self.session.refresh(delivery)
        return delivery

    def fail_delivery(self, delivery_id: int, reason: str, driver_notes: Optional[str] = None) -> Optional[Delivery]:
        """Marca entrega como falha com motivo e observações do entregador"""
        delivery = self.get_by_id(delivery_id)
        if not delivery:
            return None

        delivery.status = DeliveryStatus.FAILED.value
        delivery.failure_reason = reason
        delivery.notes = driver_notes or f"Falha: {reason}"
        delivery.update_status(DeliveryStatus.FAILED.value)

        # Atualizar pedido
        delivery.order.status = "delivery_failed"

        self.session.add(delivery)
        self.session.add(delivery.order)
        self.session.commit()
        self.session.refresh(delivery)
        return delivery

    def add_delivery_notes(self, delivery_id: int, notes: str) -> Optional[Delivery]:
        """Adiciona observações à entrega"""
        delivery = self.get_by_id(delivery_id)
        if not delivery:
            return None

        delivery.notes = notes
        self.session.add(delivery)
        self.session.commit()
        self.session.refresh(delivery)
        return delivery