"""
Delivery Service - Gerenciamento de Entregas
"""

from typing import List, Optional
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryStatus
from app.models.driver import Driver, DriverStatus
from app.models.order import Order


async def suggest_driver(
    db: AsyncSession,
    order: Order,
    segmento: Optional[str] = None,
) -> List[dict]:
    """
    Sugere motoristas para um pedido com base no bairro e segmento de entrega.

    Critérios de ordenação:
    1. Motoristas com bairro_atendido que inclui o bairro do pedido (exato)
    2. Motoristas com segmento compatível (se fornecido)
    3. Menos entregas ativas

    Retorna lista de até 5 motoristas ranqueados.
    """
    bairro_pedido = (order.delivery_bairro or "").strip().lower()

    result = await db.execute(
        select(Driver).where(
            and_(Driver.is_active == True, Driver.status == DriverStatus.AVAILABLE.value)
        )
    )
    drivers = result.scalars().all()

    # Contar entregas ativas por motorista
    from app.models.delivery import Delivery, DeliveryStatus
    active_statuses = [
        DeliveryStatus.ASSIGNED.value,
        DeliveryStatus.PICKED_UP.value,
        DeliveryStatus.IN_TRANSIT.value,
        DeliveryStatus.ARRIVED.value,
    ]
    active_counts_result = await db.execute(
        select(Delivery.driver_id, func.count(Delivery.id).label("cnt"))
        .where(Delivery.status.in_(active_statuses))
        .group_by(Delivery.driver_id)
    )
    active_counts = {str(row.driver_id): row.cnt for row in active_counts_result.all()}

    def _driver_score(driver: Driver) -> tuple:
        bairros = [b.strip().lower() for b in (driver.bairros_atendidos or [])]
        bairro_single = (driver.bairro or "").strip().lower()
        all_bairros = set(bairros + ([bairro_single] if bairro_single else []))

        exact_bairro = bairro_pedido in all_bairros if bairro_pedido else False

        seg_match = True
        if segmento and driver.segmentos_atendidos:
            seg_match = segmento.lower() in [s.lower() for s in driver.segmentos_atendidos]

        active = active_counts.get(str(driver.id), 0)
        return (0 if exact_bairro else 1, 0 if seg_match else 1, active)

    ranked = sorted(drivers, key=_driver_score)

    return [
        {
            "driver_id": str(d.id),
            "nome": d.name,
            "phone": d.phone,
            "bairro": d.bairro,
            "bairros_atendidos": d.bairros_atendidos or [],
            "segmentos_atendidos": d.segmentos_atendidos or [],
            "entregas_ativas": active_counts.get(str(d.id), 0),
            "status": d.status,
            "vehicle_type": d.vehicle_type,
            "license_plate": d.license_plate,
        }
        for d in ranked[:5]
    ]


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

    def create_delivery(self, order_id: int, driver_id: int) -> Optional[Delivery]:
        """Cria entrega para pedido"""
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
            bairro=order.bairro_entrega
        )

        # Atualizar status do pedido
        order.status = "assigned"

        self.session.add(delivery)
        self.session.add(order)
        self.session.commit()
        self.session.refresh(delivery)
        return delivery

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

    def fail_delivery(self, delivery_id: int, reason: str) -> Optional[Delivery]:
        """Marca entrega como falha"""
        delivery = self.get_by_id(delivery_id)
        if not delivery:
            return None

        delivery.status = DeliveryStatus.FAILED.value
        delivery.failure_reason = reason
        delivery.update_status(DeliveryStatus.FAILED.value)

        # Atualizar pedido
        delivery.order.status = "delivery_failed"

        self.session.add(delivery)
        self.session.add(delivery.order)
        self.session.commit()
        self.session.refresh(delivery)
        return delivery