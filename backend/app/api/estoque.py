"""API do módulo de Estoque."""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.auth_models import User
from app.models.estoque.supplier import Supplier
from app.models.estoque.stock_product import StockProduct
from app.models.estoque.stock_movement import StockMovement, MovementType
from app.models.estoque.stock_balance import StockBalance
from app.models.estoque.vehicle_load import VehicleLoad, VehicleLoadStatus
from app.models.estoque.vehicle_load_item import VehicleLoadItem
from app.models.estoque.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.estoque.purchase_order_item import PurchaseOrderItem
from app.schemas.estoque import (
    ManualAdjustmentInput,
    PurchaseOrderCreate, PurchaseOrderReceive, PurchaseOrderResponse,
    StockBalanceResponse, StockMovementResponse, StockProductCreate,
    StockProductResponse, StockProductUpdate,
    SupplierCreate, SupplierResponse, SupplierUpdate,
    VehicleLoadClose, VehicleLoadCreate, VehicleLoadResponse,
    EstoqueDashboardResponse,
)
from app.services.estoque.stock_service import (
    add_stock_movement,
    auto_deduct_on_delivery,
    close_vehicle_load,
    get_stock_report,
    open_vehicle_load,
    receive_purchase_order,
    StockInsuficienteError,
)

router = APIRouter(tags=["Estoque"])

ALLOWED_ROLES = ["estoque", "admin", "owner", "financeiro"]


def _require_estoque(user: User) -> None:
    if user.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")


# ---- Dashboard ----

@router.get("/dashboard")
async def estoque_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    report = await get_stock_report(db)
    return report


# ---- Vasilhames Posição (fonte unificada) ----

@router.get("/vasilhames/posicao")
async def vasilhames_posicao(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna posição atual de vasilhames (cheios/vazios/em campo) — mesma fonte que o Financeiro."""
    _require_estoque(current_user)
    from app.models.financeiro.vasilhame_estoque import VasilhameEstoque
    from decimal import Decimal

    TODOS_TIPOS = ["P13", "P20", "P45", "G20L"]

    # Garantir que todos os tipos existam
    for tipo in TODOS_TIPOS:
        r = await db.execute(select(VasilhameEstoque).where(VasilhameEstoque.tipo == tipo))
        if not r.scalar_one_or_none():
            db.add(VasilhameEstoque(tipo=tipo, qtd_cheios=0, qtd_vazios=0, qtd_em_campo=0, custo_unitario=Decimal("0.00")))
    await db.commit()

    result = await db.execute(select(VasilhameEstoque).order_by(VasilhameEstoque.tipo))
    estoques = result.scalars().all()
    return [
        {
            "tipo": e.tipo,
            "qtd_cheios": e.qtd_cheios,
            "qtd_vazios": e.qtd_vazios,
            "qtd_em_campo": e.qtd_em_campo,
            "custo_unitario": float(e.custo_unitario),
            "valor_estoque": float(e.qtd_cheios * e.custo_unitario),
        }
        for e in estoques
    ]


@router.post("/vasilhames/ajuste")
async def vasilhames_ajuste_direto(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ajusta diretamente cheios e vazios de um tipo de vasilhame.
    Usado pela Contagem de Estoque e Ajuste Manual.
    Emite WebSocket 'vasilhame_update' para sincronizar Financeiro em tempo real.
    """
    _require_estoque(current_user)
    from app.models.financeiro.vasilhame_estoque import VasilhameEstoque, VasilhameMovimento
    from decimal import Decimal

    TODOS_TIPOS = ["P13", "P20", "P45", "G20L"]
    tipo = body.get("tipo", "").upper()
    if tipo not in TODOS_TIPOS:
        raise HTTPException(400, f"Tipo inválido: {tipo}. Válidos: {TODOS_TIPOS}")

    # Garantir que o registro existe
    r = await db.execute(select(VasilhameEstoque).where(VasilhameEstoque.tipo == tipo).with_for_update())
    estoque = r.scalar_one_or_none()
    if not estoque:
        estoque = VasilhameEstoque(tipo=tipo, qtd_cheios=0, qtd_vazios=0, qtd_em_campo=0, custo_unitario=Decimal("0.00"))
        db.add(estoque)
        await db.flush()

    antes_cheios = estoque.qtd_cheios
    antes_vazios = estoque.qtd_vazios

    # Atualizar valores se fornecidos
    if "qtd_cheios" in body:
        estoque.qtd_cheios = max(0, int(body["qtd_cheios"]))
    if "qtd_vazios" in body:
        estoque.qtd_vazios = max(0, int(body["qtd_vazios"]))

    # Registrar movimento de ajuste
    obs = body.get("observacao", f"Ajuste manual via Estoque: cheios {antes_cheios}→{estoque.qtd_cheios}, vazios {antes_vazios}→{estoque.qtd_vazios}")
    mov = VasilhameMovimento(
        tipo_vasilhame=tipo,
        tipo_movimento="ajuste_contagem",
        quantidade=abs(estoque.qtd_cheios - antes_cheios) + abs(estoque.qtd_vazios - antes_vazios),
        saldo_cheios_antes=antes_cheios,
        saldo_vazios_antes=antes_vazios,
        saldo_em_campo_antes=estoque.qtd_em_campo,
        observacao=obs,
        created_by=current_user.id,
    )
    db.add(mov)
    await db.commit()

    # Buscar posição atualizada de todos os tipos para broadcast WebSocket
    all_result = await db.execute(select(VasilhameEstoque).order_by(VasilhameEstoque.tipo))
    posicao = [
        {
            "tipo": e.tipo,
            "qtd_cheios": e.qtd_cheios,
            "qtd_vazios": e.qtd_vazios,
            "qtd_em_campo": e.qtd_em_campo,
        }
        for e in all_result.scalars().all()
    ]

    # Emitir evento WebSocket para Financeiro e Estoque sincronizarem em tempo real
    try:
        from app.api.websocket import emit_vasilhame_update
        await emit_vasilhame_update(posicao)
    except Exception:
        pass  # WebSocket é best-effort

    return {"tipo": tipo, "qtd_cheios": estoque.qtd_cheios, "qtd_vazios": estoque.qtd_vazios, "qtd_em_campo": estoque.qtd_em_campo, "ok": True}


# ---- Products ----

@router.get("/products", response_model=List[StockProductResponse])
async def list_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(select(StockProduct).where(StockProduct.is_active == True).order_by(StockProduct.code))
    return result.scalars().all()


@router.post("/products", response_model=StockProductResponse, status_code=201)
async def create_product(
    body: StockProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    sp = StockProduct(**body.model_dump())
    db.add(sp)
    await db.flush()

    # Create stock balance
    balance = StockBalance(stock_product_id=sp.id)
    db.add(balance)
    await db.commit()
    await db.refresh(sp)
    return sp


@router.put("/products/{product_id}", response_model=StockProductResponse)
async def update_product(
    product_id: UUID,
    body: StockProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(select(StockProduct).where(StockProduct.id == product_id))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(404, "Produto não encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(sp, field, value)
    await db.commit()
    await db.refresh(sp)
    return sp


# ---- Balance ----

@router.get("/balance", response_model=List[StockBalanceResponse])
async def list_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(
        select(StockBalance, StockProduct).join(
            StockProduct, StockBalance.stock_product_id == StockProduct.id
        ).where(StockProduct.is_active == True)
    )
    rows = result.all()
    out = []
    for balance, product in rows:
        out.append(StockBalanceResponse(
            stock_product_id=balance.stock_product_id,
            quantity_depot=balance.quantity_depot,
            quantity_in_transit=balance.quantity_in_transit,
            quantity_with_customers=balance.quantity_with_customers,
            last_updated=balance.last_updated,
            product_code=product.code,
            product_name=product.name,
            is_low_stock=balance.quantity_depot < product.min_stock_alert,
        ))
    return out


@router.get("/balance/{product_id}", response_model=StockBalanceResponse)
async def get_balance(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(
        select(StockBalance, StockProduct).join(
            StockProduct, StockBalance.stock_product_id == StockProduct.id
        ).where(StockBalance.stock_product_id == product_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Saldo de produto não encontrado")
    balance, product = row
    return StockBalanceResponse(
        stock_product_id=balance.stock_product_id,
        quantity_depot=balance.quantity_depot,
        quantity_in_transit=balance.quantity_in_transit,
        quantity_with_customers=balance.quantity_with_customers,
        last_updated=balance.last_updated,
        product_code=product.code,
        product_name=product.name,
        is_low_stock=balance.quantity_depot < product.min_stock_alert,
    )


# ---- Movements ----

@router.get("/movements", response_model=List[StockMovementResponse])
async def list_movements(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    movement_type: Optional[str] = None,
    product_id: Optional[UUID] = None,
    driver_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    filters = []
    if movement_type:
        filters.append(StockMovement.movement_type == movement_type)
    if product_id:
        filters.append(StockMovement.stock_product_id == product_id)
    if driver_id:
        filters.append(StockMovement.driver_id == driver_id)
    if start_date:
        filters.append(func.date(StockMovement.created_at) >= start_date)
    if end_date:
        filters.append(func.date(StockMovement.created_at) <= end_date)

    q = select(StockMovement)
    if filters:
        q = q.where(and_(*filters))
    q = q.order_by(StockMovement.created_at.desc())
    offset = (page - 1) * per_page
    q = q.offset(offset).limit(per_page)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/movements/adjustment", response_model=StockMovementResponse, status_code=201)
async def manual_adjustment(
    body: ManualAdjustmentInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    movement_type = (
        MovementType.ajuste_entrada.value if body.direction == "entrada"
        else MovementType.ajuste_saida.value
    )
    try:
        mv = await add_stock_movement(
            db=db,
            stock_product_id=body.stock_product_id,
            movement_type=movement_type,
            quantity=body.quantity,
            direction=body.direction,
            created_by=current_user.id,
            notes=body.notes,
        )
        await db.commit()
        await db.refresh(mv)
        return mv
    except StockInsuficienteError as e:
        raise HTTPException(422, str(e))


# ---- Vehicle Loads ----

@router.get("/vehicle-loads", response_model=List[VehicleLoadResponse])
async def list_vehicle_loads(
    driver_id: Optional[UUID] = None,
    load_date: Optional[date] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    filters = []
    if driver_id:
        filters.append(VehicleLoad.driver_id == driver_id)
    if load_date:
        filters.append(VehicleLoad.load_date == load_date)
    if status_filter:
        filters.append(VehicleLoad.status == status_filter)
    q = select(VehicleLoad).options(selectinload(VehicleLoad.items))
    if filters:
        q = q.where(and_(*filters))
    q = q.order_by(VehicleLoad.load_date.desc())
    result = await db.execute(q)
    loads = result.scalars().all()
    return [_load_to_response(vl) for vl in loads]


@router.get("/vehicle-loads/open", response_model=List[VehicleLoadResponse])
async def open_vehicle_loads(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(
        select(VehicleLoad).options(selectinload(VehicleLoad.items)).where(
            VehicleLoad.status.in_([VehicleLoadStatus.aberta.value, VehicleLoadStatus.em_rota.value])
        )
    )
    loads = result.scalars().all()
    return [_load_to_response(vl) for vl in loads]


@router.get("/vehicle-loads/{load_id}", response_model=VehicleLoadResponse)
async def get_vehicle_load(
    load_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(
        select(VehicleLoad).options(selectinload(VehicleLoad.items)).where(VehicleLoad.id == load_id)
    )
    vl = result.scalar_one_or_none()
    if not vl:
        raise HTTPException(404, "Carga não encontrada")
    return _load_to_response(vl)


@router.post("/vehicle-loads", response_model=VehicleLoadResponse, status_code=201)
async def create_vehicle_load(
    body: VehicleLoadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    try:
        vl = await open_vehicle_load(
            db=db,
            driver_id=body.driver_id,
            items=body.items,
            load_date=body.load_date,
            created_by=current_user.id,
            notes=body.notes,
        )
        await db.commit()
        await db.refresh(vl)
        # reload items
        result = await db.execute(
            select(VehicleLoad).options(selectinload(VehicleLoad.items)).where(VehicleLoad.id == vl.id)
        )
        vl = result.scalar_one()
        return _load_to_response(vl)
    except (StockInsuficienteError, ValueError) as e:
        raise HTTPException(422, str(e))


@router.post("/vehicle-loads/{load_id}/close", response_model=VehicleLoadResponse)
async def close_load(
    load_id: UUID,
    body: VehicleLoadClose,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    try:
        vl = await close_vehicle_load(
            db=db,
            vehicle_load_id=load_id,
            returned_items=body.returned_items,
            closed_by=current_user.id,
            notes=body.notes,
        )
        await db.commit()
        result = await db.execute(
            select(VehicleLoad).options(selectinload(VehicleLoad.items)).where(VehicleLoad.id == vl.id)
        )
        vl = result.scalar_one()
        return _load_to_response(vl)
    except ValueError as e:
        raise HTTPException(422, str(e))


def _load_to_response(vl: VehicleLoad) -> VehicleLoadResponse:
    items = []
    if hasattr(vl, "items") and vl.items:
        for item in vl.items:
            from app.schemas.estoque import VehicleLoadItemResponse
            items.append(VehicleLoadItemResponse(
                id=item.id,
                stock_product_id=item.stock_product_id,
                quantity_loaded=item.quantity_loaded,
                quantity_delivered=item.quantity_delivered,
                quantity_returned=item.quantity_returned,
            ))
    return VehicleLoadResponse(
        id=vl.id,
        driver_id=vl.driver_id,
        load_date=vl.load_date,
        status=vl.status,
        closed_at=vl.closed_at,
        notes=vl.notes,
        created_at=vl.created_at,
        items=items,
    )


# ---- Suppliers ----

@router.get("/suppliers", response_model=List[SupplierResponse])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(select(Supplier).where(Supplier.deleted_at == None).order_by(Supplier.name))
    return result.scalars().all()


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    body: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.put("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: UUID,
    body: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at == None))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(404, "Fornecedor não encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(supplier, field, value)
    await db.commit()
    await db.refresh(supplier)
    return supplier


# ---- Purchase Orders ----

@router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
async def list_purchase_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    filters = [PurchaseOrder.deleted_at == None]
    if status_filter:
        filters.append(PurchaseOrder.status == status_filter)
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
        .where(and_(*filters)).order_by(PurchaseOrder.order_date.desc())
    )
    pos = result.scalars().all()
    return [_po_to_response(po) for po in pos]


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at == None)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(404, "Pedido de compra não encontrado")
    return _po_to_response(po)


@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=201)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    total = sum(item.quantity_ordered * item.unit_cost for item in body.items)
    po = PurchaseOrder(
        supplier_id=body.supplier_id,
        order_date=body.order_date,
        expected_delivery_date=body.expected_delivery_date,
        status=PurchaseOrderStatus.rascunho.value,
        total_cost=total,
        notes=body.notes,
    )
    db.add(po)
    await db.flush()

    for item in body.items:
        poi = PurchaseOrderItem(
            purchase_order_id=po.id,
            stock_product_id=item.stock_product_id,
            quantity_ordered=item.quantity_ordered,
            unit_cost=item.unit_cost,
            subtotal=item.quantity_ordered * item.unit_cost,
        )
        db.add(poi)

    await db.commit()
    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po.id)
    )
    po = result.scalar_one()
    return _po_to_response(po)


@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_po(
    po_id: UUID,
    body: PurchaseOrderReceive,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    try:
        po = await receive_purchase_order(
            db=db,
            purchase_order_id=po_id,
            received_items=body.items,
            received_by=current_user.id,
        )
        await db.commit()
        result = await db.execute(
            select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po.id)
        )
        po = result.scalar_one()
        return _po_to_response(po)
    except ValueError as e:
        raise HTTPException(422, str(e))


def _po_to_response(po: PurchaseOrder) -> PurchaseOrderResponse:
    from app.schemas.estoque import PurchaseOrderItemResponse
    items = []
    if hasattr(po, "items") and po.items:
        for item in po.items:
            items.append(PurchaseOrderItemResponse(
                id=item.id,
                stock_product_id=item.stock_product_id,
                quantity_ordered=item.quantity_ordered,
                quantity_received=item.quantity_received,
                unit_cost=item.unit_cost,
                subtotal=item.subtotal,
            ))
    return PurchaseOrderResponse(
        id=po.id,
        supplier_id=po.supplier_id,
        order_date=po.order_date,
        expected_delivery_date=po.expected_delivery_date,
        status=po.status,
        total_cost=po.total_cost,
        notes=po.notes,
        received_at=po.received_at,
        created_at=po.created_at,
        items=items,
    )


# ---- Reports ----

@router.get("/reports/daily")
async def daily_report(
    report_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    target_date = report_date or date.today()
    result = await db.execute(
        select(StockMovement).where(
            func.date(StockMovement.created_at) == target_date
        ).order_by(StockMovement.created_at.desc())
    )
    movements = result.scalars().all()
    return {"date": target_date, "count": len(movements), "movements": [
        {"id": str(m.id), "type": m.movement_type, "product_id": str(m.stock_product_id),
         "quantity": m.quantity, "direction": m.direction, "created_at": m.created_at.isoformat()}
        for m in movements
    ]}


@router.get("/reports/low-stock")
async def low_stock_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    result = await db.execute(
        select(StockBalance, StockProduct).join(
            StockProduct, StockBalance.stock_product_id == StockProduct.id
        ).where(StockProduct.is_active == True)
    )
    rows = result.all()
    low = [
        {
            "code": p.code, "name": p.name,
            "quantity_depot": b.quantity_depot,
            "min_stock_alert": p.min_stock_alert,
            "deficit": p.min_stock_alert - b.quantity_depot,
        }
        for b, p in rows if b.quantity_depot < p.min_stock_alert
    ]
    return {"low_stock_products": low, "count": len(low)}


@router.get("/reports/by-driver")
async def report_by_driver(
    report_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_estoque(current_user)
    target_date = report_date or date.today()
    result = await db.execute(
        select(VehicleLoad).options(selectinload(VehicleLoad.items))
        .where(VehicleLoad.load_date == target_date)
    )
    loads = result.scalars().all()
    out = []
    for vl in loads:
        total_loaded = sum(i.quantity_loaded for i in vl.items)
        total_delivered = sum(i.quantity_delivered for i in vl.items)
        total_returned = sum(i.quantity_returned for i in vl.items)
        out.append({
            "driver_id": str(vl.driver_id),
            "load_date": vl.load_date.isoformat(),
            "status": vl.status,
            "total_loaded": total_loaded,
            "total_delivered": total_delivered,
            "total_returned": total_returned,
        })
    return {"date": target_date, "drivers": out}
