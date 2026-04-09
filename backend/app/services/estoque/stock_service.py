"""Serviço de Estoque — lógica de negócio do módulo de estoque."""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.estoque.stock_product import StockProduct
from app.models.estoque.stock_movement import StockMovement, MovementType
from app.models.estoque.stock_balance import StockBalance
from app.models.estoque.vehicle_load import VehicleLoad, VehicleLoadStatus
from app.models.estoque.vehicle_load_item import VehicleLoadItem
from app.models.estoque.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.estoque.purchase_order_item import PurchaseOrderItem
from app.schemas.estoque import LoadItemInput, ReturnItemInput

logger = logging.getLogger(__name__)


class StockInsuficienteError(Exception):
    pass


async def _get_balance(db: AsyncSession, stock_product_id: UUID) -> StockBalance:
    result = await db.execute(
        select(StockBalance).where(
            StockBalance.stock_product_id == stock_product_id
        ).with_for_update()
    )
    balance = result.scalar_one_or_none()
    if not balance:
        # auto-create if missing
        balance = StockBalance(
            stock_product_id=stock_product_id,
            quantity_depot=0,
            quantity_in_transit=0,
            quantity_with_customers=0,
        )
        db.add(balance)
        await db.flush()
    return balance


async def add_stock_movement(
    db: AsyncSession,
    stock_product_id: UUID,
    movement_type: str,
    quantity: int,
    direction: str,
    created_by: int,
    unit_cost: Optional[Decimal] = None,
    vehicle_load_id: Optional[UUID] = None,
    driver_id: Optional[UUID] = None,
    reference_id: Optional[UUID] = None,
    reference_type: Optional[str] = None,
    notes: Optional[str] = None,
) -> StockMovement:
    """Cria StockMovement e atualiza StockBalance."""
    async with db.begin_nested():
        balance = await _get_balance(db, stock_product_id)

        # Validate no negative depot
        if direction == "saida" and movement_type in [
            MovementType.carga_veiculo.value, MovementType.venda.value, MovementType.ajuste_saida.value, MovementType.perda.value
        ]:
            if balance.quantity_depot < quantity:
                result = await db.execute(select(StockProduct).where(StockProduct.id == stock_product_id))
                product = result.scalar_one_or_none()
                pname = product.name if product else str(stock_product_id)
                raise StockInsuficienteError(
                    f"Estoque insuficiente para '{pname}': "
                    f"disponível={balance.quantity_depot}, solicitado={quantity}"
                )

        # Update balance
        if direction == "entrada":
            if movement_type == MovementType.retorno_veiculo.value:
                balance.quantity_in_transit = max(0, balance.quantity_in_transit - quantity)
                balance.quantity_depot += quantity
            elif movement_type == MovementType.devolucao_cliente.value:
                balance.quantity_with_customers = max(0, balance.quantity_with_customers - quantity)
                balance.quantity_depot += quantity
            else:
                balance.quantity_depot += quantity
        else:
            if movement_type == MovementType.carga_veiculo.value:
                balance.quantity_depot -= quantity
                balance.quantity_in_transit += quantity
            elif movement_type == MovementType.venda.value:
                balance.quantity_depot -= quantity
                balance.quantity_with_customers += quantity
            else:
                balance.quantity_depot = max(0, balance.quantity_depot - quantity)

        balance.last_updated = datetime.now(timezone.utc)

        total_cost = (unit_cost * quantity) if unit_cost else None

        movement = StockMovement(
            stock_product_id=stock_product_id,
            movement_type=movement_type,
            quantity=quantity,
            direction=direction,
            unit_cost=unit_cost,
            total_cost=total_cost,
            vehicle_load_id=vehicle_load_id,
            driver_id=driver_id,
            reference_id=reference_id,
            reference_type=reference_type,
            notes=notes,
            created_by=created_by,
        )
        db.add(movement)
        await db.flush()

    # Fire WS alert if low stock
    try:
        result = await db.execute(select(StockProduct).where(StockProduct.id == stock_product_id))
        product = result.scalar_one_or_none()
        if product and balance.quantity_depot < product.min_stock_alert:
            from app.core.redis_websocket_bridge import redis_ws_bridge
            await redis_ws_bridge.publish_event("stock_alert_low", {
                "product_id": str(stock_product_id),
                "product_code": product.code,
                "quantity_depot": balance.quantity_depot,
                "min_stock_alert": product.min_stock_alert,
                "target_roles": ["estoque", "admin", "owner"],
            })
    except Exception as e:
        logger.warning(f"Erro ao disparar alerta de estoque: {e}")

    return movement


async def open_vehicle_load(
    db: AsyncSession,
    driver_id: UUID,
    items: List[LoadItemInput],
    load_date: date,
    created_by: int,
    notes: Optional[str] = None,
) -> VehicleLoad:
    """Abre carga do dia para um entregador."""
    # Check for existing open load
    result = await db.execute(
        select(VehicleLoad).where(
            and_(
                VehicleLoad.driver_id == driver_id,
                VehicleLoad.load_date == load_date,
                VehicleLoad.status != VehicleLoadStatus.encerrada.value,
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError(f"Já existe carga aberta para este driver em {load_date}")

    vehicle_load = VehicleLoad(
        driver_id=driver_id,
        load_date=load_date,
        status=VehicleLoadStatus.em_rota.value,
        loaded_by=created_by,
        notes=notes,
    )
    db.add(vehicle_load)
    await db.flush()

    for item in items:
        # Create stock movement: carga_veiculo = saida
        await add_stock_movement(
            db=db,
            stock_product_id=item.stock_product_id,
            movement_type=MovementType.carga_veiculo.value,
            quantity=item.quantity_loaded,
            direction="saida",
            created_by=created_by,
            vehicle_load_id=vehicle_load.id,
            driver_id=driver_id,
            reference_id=vehicle_load.id,
            reference_type="vehicle_load",
        )

        load_item = VehicleLoadItem(
            vehicle_load_id=vehicle_load.id,
            stock_product_id=item.stock_product_id,
            quantity_loaded=item.quantity_loaded,
        )
        db.add(load_item)

    await db.flush()
    return vehicle_load


async def close_vehicle_load(
    db: AsyncSession,
    vehicle_load_id: UUID,
    returned_items: List[ReturnItemInput],
    closed_by: int,
    notes: Optional[str] = None,
) -> VehicleLoad:
    """Encerra a carga do dia e registra retornos com split cheios/vazios no vasilhame_estoque."""
    result = await db.execute(
        select(VehicleLoad).where(VehicleLoad.id == vehicle_load_id).with_for_update()
    )
    vehicle_load = result.scalar_one_or_none()
    if not vehicle_load:
        raise ValueError(f"Carga {vehicle_load_id} não encontrada")
    if vehicle_load.status == VehicleLoadStatus.encerrada.value:
        raise ValueError("Esta carga já foi encerrada")

    # Get load items
    result = await db.execute(
        select(VehicleLoadItem).where(VehicleLoadItem.vehicle_load_id == vehicle_load_id)
    )
    load_items = result.scalars().all()
    items_map = {str(item.stock_product_id): item for item in load_items}

    for ret_item in returned_items:
        product_key = str(ret_item.stock_product_id)
        if product_key in items_map:
            li = items_map[product_key]
            li.quantity_returned = ret_item.quantity_returned
            li.quantity_delivered = li.quantity_loaded - ret_item.quantity_returned

        # Create retorno movement (total)
        if ret_item.quantity_returned > 0:
            await add_stock_movement(
                db=db,
                stock_product_id=ret_item.stock_product_id,
                movement_type=MovementType.retorno_veiculo.value,
                quantity=ret_item.quantity_returned,
                direction="entrada",
                created_by=closed_by,
                vehicle_load_id=vehicle_load_id,
                driver_id=vehicle_load.driver_id,
                reference_id=vehicle_load_id,
                reference_type="vehicle_load",
            )

        # --- Atualizar vasilhame_estoque com split cheios/vazios ---
        cheios = ret_item.cheios_retornados
        vazios = ret_item.vazios_retornados
        if cheios is not None or vazios is not None:
            try:
                # Descobrir o código do produto para mapear para tipo de vasilhame
                prod_result = await db.execute(
                    select(StockProduct).where(StockProduct.id == ret_item.stock_product_id)
                )
                sp = prod_result.scalar_one_or_none()
                tipo = (sp.code if sp else "").upper() if sp else None
                TIPOS_VALIDOS = {"P13", "P20", "P45", "G20L"}
                if tipo in TIPOS_VALIDOS:
                    from app.models.financeiro.vasilhame_estoque import VasilhameEstoque
                    from decimal import Decimal as D
                    ve_result = await db.execute(
                        select(VasilhameEstoque).where(VasilhameEstoque.tipo == tipo).with_for_update()
                    )
                    ve = ve_result.scalar_one_or_none()
                    if not ve:
                        ve = VasilhameEstoque(tipo=tipo, qtd_cheios=0, qtd_vazios=0, qtd_em_campo=0, custo_unitario=D("0.00"))
                        db.add(ve)
                        await db.flush()
                    # Subtrai de em_campo e soma na coluna correta
                    total_ret = (cheios or 0) + (vazios or 0)
                    ve.qtd_em_campo = max(0, ve.qtd_em_campo - total_ret)
                    if cheios:
                        ve.qtd_cheios += cheios
                    if vazios:
                        ve.qtd_vazios += vazios
            except Exception as ve_err:
                logger.warning(f"Erro ao atualizar vasilhame_estoque no fechamento de carga: {ve_err}")

    vehicle_load.status = VehicleLoadStatus.encerrada.value
    vehicle_load.closed_at = datetime.now(timezone.utc)
    if notes:
        vehicle_load.notes = notes

    await db.flush()

    # Emitir WebSocket para Financeiro e Estoque atualizarem em tempo real
    try:
        from app.models.financeiro.vasilhame_estoque import VasilhameEstoque
        all_ve = await db.execute(select(VasilhameEstoque).order_by(VasilhameEstoque.tipo))
        posicao = [
            {"tipo": e.tipo, "qtd_cheios": e.qtd_cheios, "qtd_vazios": e.qtd_vazios, "qtd_em_campo": e.qtd_em_campo}
            for e in all_ve.scalars().all()
        ]
        from app.api.websocket import emit_vasilhame_update
        await emit_vasilhame_update(posicao)
    except Exception:
        pass  # Best-effort

    return vehicle_load



async def receive_purchase_order(
    db: AsyncSession,
    purchase_order_id: UUID,
    received_items: list,
    received_by: int,
) -> PurchaseOrder:
    """Recebe um pedido de compra e atualiza estoque."""
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == purchase_order_id).with_for_update()
    )
    po = result.scalar_one_or_none()
    if not po:
        raise ValueError(f"Pedido de compra {purchase_order_id} não encontrado")
    if po.status == PurchaseOrderStatus.recebido.value:
        raise ValueError("Este pedido já foi recebido")

    for item in received_items:
        if item.quantity_received <= 0:
            continue

        unit_cost = item.unit_cost
        if unit_cost is None:
            # Get from PO item
            result2 = await db.execute(
                select(PurchaseOrderItem).where(
                    and_(
                        PurchaseOrderItem.purchase_order_id == purchase_order_id,
                        PurchaseOrderItem.stock_product_id == item.stock_product_id,
                    )
                )
            )
            poi = result2.scalar_one_or_none()
            unit_cost = poi.unit_cost if poi else Decimal("0.00")

        await add_stock_movement(
            db=db,
            stock_product_id=item.stock_product_id,
            movement_type=MovementType.compra.value,
            quantity=item.quantity_received,
            direction="entrada",
            created_by=received_by,
            unit_cost=unit_cost,
            reference_id=purchase_order_id,
            reference_type="purchase_order",
        )

        # Update cost price in stock product (weighted average)
        result3 = await db.execute(select(StockProduct).where(StockProduct.id == item.stock_product_id))
        sp = result3.scalar_one_or_none()
        if sp and unit_cost:
            sp.cost_price = unit_cost

        # Update PO item received qty
        result4 = await db.execute(
            select(PurchaseOrderItem).where(
                and_(
                    PurchaseOrderItem.purchase_order_id == purchase_order_id,
                    PurchaseOrderItem.stock_product_id == item.stock_product_id,
                )
            )
        )
        poi = result4.scalar_one_or_none()
        if poi:
            poi.quantity_received = item.quantity_received

    po.status = PurchaseOrderStatus.recebido.value
    po.received_at = datetime.now(timezone.utc)
    po.received_by = received_by
    await db.flush()
    return po


async def auto_deduct_on_delivery(db: AsyncSession, order_id: UUID) -> None:
    """Chamado quando Order.status → delivered. Baixa estoque."""
    try:
        from sqlalchemy.orm import selectinload
        from app.models.order import Order
        from app.config import settings

        if not getattr(settings, "stock_auto_deduct_on_delivery", True):
            return

        result = await db.execute(
            select(Order).options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return

        for item in order.items:
            # Find stock product by linked code
            result2 = await db.execute(
                select(StockProduct).where(
                    and_(
                        StockProduct.linked_product_code == item.product_code,
                        StockProduct.is_active == True,
                    )
                )
            )
            sp = result2.scalar_one_or_none()
            if not sp:
                # Try by code directly
                result2 = await db.execute(
                    select(StockProduct).where(
                        and_(StockProduct.code == item.product_code, StockProduct.is_active == True)
                    )
                )
                sp = result2.scalar_one_or_none()

            if not sp:
                logger.warning(f"auto_deduct: produto {item.product_code} não encontrado no estoque")
                continue

            # Check if driver has open vehicle load
            vehicle_load_id = None
            if order.delivery:
                driver_id = getattr(order.delivery, "driver_id", None)
                if driver_id:
                    today = date.today()
                    result3 = await db.execute(
                        select(VehicleLoad).where(
                            and_(
                                VehicleLoad.driver_id == driver_id,
                                VehicleLoad.load_date == today,
                                VehicleLoad.status == VehicleLoadStatus.em_rota.value,
                            )
                        )
                    )
                    vl = result3.scalar_one_or_none()
                    if vl:
                        vehicle_load_id = vl.id
                        # Update vehicle_load_item delivered count
                        result4 = await db.execute(
                            select(VehicleLoadItem).where(
                                and_(
                                    VehicleLoadItem.vehicle_load_id == vl.id,
                                    VehicleLoadItem.stock_product_id == sp.id,
                                )
                            )
                        )
                        vli = result4.scalar_one_or_none()
                        if vli:
                            vli.quantity_delivered += item.quantity

            await add_stock_movement(
                db=db,
                stock_product_id=sp.id,
                movement_type=MovementType.venda.value,
                quantity=item.quantity,
                direction="saida",
                created_by=1,
                vehicle_load_id=vehicle_load_id,
                reference_id=order_id,
                reference_type="order",
            )

        logger.info(f"auto_deduct: estoque baixado para pedido {order_id}")
    except StockInsuficienteError as e:
        logger.warning(f"auto_deduct: estoque insuficiente para pedido {order_id}: {e}")
    except Exception as e:
        logger.error(f"auto_deduct: erro para pedido {order_id}: {e}", exc_info=True)


async def get_stock_report(db: AsyncSession) -> dict:
    """Relatório de estoque atual."""
    result = await db.execute(
        select(StockBalance, StockProduct).join(
            StockProduct, StockBalance.stock_product_id == StockProduct.id
        ).where(StockProduct.is_active == True)
    )
    rows = result.all()

    balances = []
    low_stock_count = 0
    total_in_transit = 0

    for balance, product in rows:
        is_low = balance.quantity_depot < product.min_stock_alert
        if is_low:
            low_stock_count += 1
        total_in_transit += balance.quantity_in_transit
        balances.append({
            "stock_product_id": str(balance.stock_product_id),
            "product_code": product.code,
            "product_name": product.name,
            "quantity_depot": balance.quantity_depot,
            "quantity_in_transit": balance.quantity_in_transit,
            "quantity_with_customers": balance.quantity_with_customers,
            "last_updated": balance.last_updated,
            "is_low_stock": is_low,
            "cost_price": float(product.cost_price),
            "total_value": float(product.cost_price) * balance.quantity_depot,
        })

    # Open loads count
    result2 = await db.execute(
        select(func.count(VehicleLoad.id)).where(
            VehicleLoad.status.in_([VehicleLoadStatus.aberta.value, VehicleLoadStatus.em_rota.value])
        )
    )
    open_loads_count = result2.scalar() or 0

    # Movements today
    today = date.today()
    result3 = await db.execute(
        select(func.count(StockMovement.id)).where(
            func.date(StockMovement.created_at) == today
        )
    )
    movements_today = result3.scalar() or 0

    return {
        "balances": balances,
        "low_stock_count": low_stock_count,
        "total_in_transit": total_in_transit,
        "open_loads_count": open_loads_count,
        "movements_today": movements_today,
    }
