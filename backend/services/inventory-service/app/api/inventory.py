"""
API de Estoque.
Endpoints para gestão de produtos e movimentações.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, BackgroundTasks

import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schemas ====================

class MovementType(str, Enum):
    """Tipo de movimentação de estoque."""
    IN = "IN"              # Entrada (compra, devolução)
    OUT = "OUT"            # Saída (venda, perda)
    ADJUSTMENT = "ADJUST"  # Ajuste de inventário
    RESERVE = "RESERVE"    # Reserva para pedido
    RELEASE = "RELEASE"    # Liberação de reserva


class ProductBase(BaseModel):
    """Schema base de produto."""
    code: str = Field(..., max_length=20, description="Código único (P13, P20, P45)")
    name: str = Field(..., max_length=200, description="Nome do produto")
    price: Decimal = Field(..., gt=0, description="Preço de venda")
    weight_kg: Optional[float] = Field(None, description="Peso em kg")
    description: Optional[str] = Field(None, max_length=500)


class ProductCreate(ProductBase):
    """Schema para criar produto."""
    initial_stock: int = Field(0, ge=0, description="Estoque inicial")
    min_stock_alert: int = Field(10, ge=0, description="Limite para alerta de estoque baixo")


class ProductUpdate(BaseModel):
    """Schema para atualizar produto."""
    name: Optional[str] = None
    price: Optional[Decimal] = None
    weight_kg: Optional[float] = None
    description: Optional[str] = None
    min_stock_alert: Optional[int] = None
    active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Resposta de produto."""
    id: UUID
    stock_quantity: int
    reserved_quantity: int
    available_quantity: int
    min_stock_alert: int
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class StockMovementCreate(BaseModel):
    """Schema para criar movimentação."""
    product_code: str
    movement_type: MovementType
    quantity: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=500)
    reference_id: Optional[str] = Field(None, description="ID do pedido/entrega relacionado")


class StockMovementResponse(BaseModel):
    """Resposta de movimentação."""
    id: UUID
    product_code: str
    movement_type: MovementType
    quantity: int
    previous_quantity: int
    new_quantity: int
    reason: Optional[str]
    reference_id: Optional[str]
    created_at: datetime


class ReserveRequest(BaseModel):
    """Request para reservar estoque."""
    product_code: str
    quantity: int = Field(..., gt=0)
    order_id: str


class StockAlertResponse(BaseModel):
    """Alerta de estoque baixo."""
    product_code: str
    product_name: str
    current_stock: int
    min_threshold: int
    alert_level: str  # LOW, CRITICAL, OUT_OF_STOCK


# ==================== In-Memory Storage (para demo) ====================
# Em produção, usar banco de dados PostgreSQL

PRODUCTS_DB: dict[str, dict] = {
    "P13": {
        "id": str(uuid4()),
        "code": "P13",
        "name": "Botijão P13 (13kg)",
        "price": Decimal("110.00"),
        "weight_kg": 13.0,
        "description": "Botijão de gás GLP 13kg - Uso residencial",
        "stock_quantity": 100,
        "reserved_quantity": 0,
        "min_stock_alert": 20,
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    },
    "P20": {
        "id": str(uuid4()),
        "code": "P20",
        "name": "Botijão P20 (20kg)",
        "price": Decimal("180.00"),
        "weight_kg": 20.0,
        "description": "Botijão de gás GLP 20kg - Uso comercial leve",
        "stock_quantity": 50,
        "reserved_quantity": 0,
        "min_stock_alert": 10,
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    },
    "P45": {
        "id": str(uuid4()),
        "code": "P45",
        "name": "Botijão P45 (45kg)",
        "price": Decimal("380.00"),
        "weight_kg": 45.0,
        "description": "Botijão de gás GLP 45kg - Uso comercial/industrial",
        "stock_quantity": 30,
        "reserved_quantity": 0,
        "min_stock_alert": 5,
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    },
}

MOVEMENTS_DB: list[dict] = []


# ==================== Redis Client ====================

async def get_redis() -> redis.Redis:
    """Retorna cliente Redis."""
    return redis.from_url(settings.redis_url)


async def publish_event(event_type: str, payload: dict):
    """Publica evento no Redis Stream."""
    try:
        r = await get_redis()
        await r.xadd(
            "inventory:events",
            {
                "type": event_type,
                "payload": str(payload),
            }
        )
        await r.close()
    except Exception as e:
        logger.error(f"Erro ao publicar evento: {e}")


# ==================== Endpoints - Produtos ====================

@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    active_only: bool = True,
    include_out_of_stock: bool = True,
):
    """Lista todos os produtos."""
    products = []
    for code, product in PRODUCTS_DB.items():
        if active_only and not product["active"]:
            continue

        available = product["stock_quantity"] - product["reserved_quantity"]
        if not include_out_of_stock and available <= 0:
            continue

        products.append({
            **product,
            "available_quantity": available,
        })

    return products


@router.get("/products/{product_code}", response_model=ProductResponse)
async def get_product(product_code: str):
    """Busca produto por código."""
    product = PRODUCTS_DB.get(product_code.upper())
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    return {
        **product,
        "available_quantity": product["stock_quantity"] - product["reserved_quantity"],
    }


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(request: ProductCreate):
    """Cria novo produto."""
    code = request.code.upper()

    if code in PRODUCTS_DB:
        raise HTTPException(status_code=400, detail="Código de produto já existe")

    product = {
        "id": str(uuid4()),
        "code": code,
        "name": request.name,
        "price": request.price,
        "weight_kg": request.weight_kg,
        "description": request.description,
        "stock_quantity": request.initial_stock,
        "reserved_quantity": 0,
        "min_stock_alert": request.min_stock_alert,
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    }

    PRODUCTS_DB[code] = product

    return {
        **product,
        "available_quantity": product["stock_quantity"],
    }


@router.patch("/products/{product_code}", response_model=ProductResponse)
async def update_product(product_code: str, request: ProductUpdate):
    """Atualiza produto."""
    code = product_code.upper()
    product = PRODUCTS_DB.get(code)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            product[key] = value

    product["updated_at"] = datetime.now(timezone.utc)

    return {
        **product,
        "available_quantity": product["stock_quantity"] - product["reserved_quantity"],
    }


# ==================== Endpoints - Estoque ====================

@router.post("/stock/movement", response_model=StockMovementResponse)
async def create_movement(
    request: StockMovementCreate,
    background_tasks: BackgroundTasks,
):
    """
    Registra movimentação de estoque.

    Tipos:
    - IN: Entrada de estoque
    - OUT: Saída de estoque
    - ADJUST: Ajuste de inventário
    """
    code = request.product_code.upper()
    product = PRODUCTS_DB.get(code)

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    previous_qty = product["stock_quantity"]

    # Aplicar movimentação
    if request.movement_type == MovementType.IN:
        product["stock_quantity"] += request.quantity
    elif request.movement_type == MovementType.OUT:
        if product["stock_quantity"] < request.quantity:
            raise HTTPException(status_code=400, detail="Estoque insuficiente")
        product["stock_quantity"] -= request.quantity
    elif request.movement_type == MovementType.ADJUSTMENT:
        # Ajuste pode ser positivo ou negativo baseado no reason
        product["stock_quantity"] = request.quantity
    elif request.movement_type == MovementType.RELEASE:
        # Liberar reserva
        product["reserved_quantity"] = max(0, product["reserved_quantity"] - request.quantity)

    new_qty = product["stock_quantity"]
    product["updated_at"] = datetime.now(timezone.utc)

    # Registrar movimentação
    movement = {
        "id": str(uuid4()),
        "product_code": code,
        "movement_type": request.movement_type,
        "quantity": request.quantity,
        "previous_quantity": previous_qty,
        "new_quantity": new_qty,
        "reason": request.reason,
        "reference_id": request.reference_id,
        "created_at": datetime.now(timezone.utc),
    }
    MOVEMENTS_DB.append(movement)

    # Verificar alerta de estoque baixo
    if new_qty <= product["min_stock_alert"]:
        background_tasks.add_task(
            publish_event,
            "stock.low",
            {
                "product_code": code,
                "current_stock": new_qty,
                "threshold": product["min_stock_alert"],
            }
        )

    # Publicar evento de movimentação
    background_tasks.add_task(
        publish_event,
        "stock.movement",
        {
            "product_code": code,
            "movement_type": request.movement_type.value,
            "quantity": request.quantity,
            "new_stock": new_qty,
        }
    )

    return movement


@router.post("/stock/reserve", response_model=dict)
async def reserve_stock(
    request: ReserveRequest,
    background_tasks: BackgroundTasks,
):
    """
    Reserva estoque para um pedido.

    A reserva diminui a quantidade disponível mas não o estoque total.
    Usado quando um pedido é criado mas ainda não foi pago/entregue.
    """
    code = request.product_code.upper()
    product = PRODUCTS_DB.get(code)

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    available = product["stock_quantity"] - product["reserved_quantity"]

    if available < request.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque disponível insuficiente. Disponível: {available}"
        )

    # Reservar
    product["reserved_quantity"] += request.quantity
    product["updated_at"] = datetime.now(timezone.utc)

    # Registrar movimentação
    movement = {
        "id": str(uuid4()),
        "product_code": code,
        "movement_type": MovementType.RESERVE,
        "quantity": request.quantity,
        "previous_quantity": product["stock_quantity"],
        "new_quantity": product["stock_quantity"],
        "reason": f"Reserva para pedido {request.order_id}",
        "reference_id": request.order_id,
        "created_at": datetime.now(timezone.utc),
    }
    MOVEMENTS_DB.append(movement)

    # Publicar evento
    background_tasks.add_task(
        publish_event,
        "stock.reserved",
        {
            "product_code": code,
            "quantity": request.quantity,
            "order_id": request.order_id,
        }
    )

    return {
        "status": "reserved",
        "product_code": code,
        "reserved_quantity": request.quantity,
        "available_after": available - request.quantity,
        "order_id": request.order_id,
    }


@router.post("/stock/release/{order_id}", response_model=dict)
async def release_reservation(order_id: str):
    """
    Libera reserva de estoque (pedido cancelado).
    """
    released = []

    for movement in MOVEMENTS_DB:
        if (
            movement.get("reference_id") == order_id
            and movement.get("movement_type") == MovementType.RESERVE
        ):
            code = movement["product_code"]
            qty = movement["quantity"]

            if code in PRODUCTS_DB:
                PRODUCTS_DB[code]["reserved_quantity"] -= qty
                PRODUCTS_DB[code]["reserved_quantity"] = max(0, PRODUCTS_DB[code]["reserved_quantity"])
                released.append({"code": code, "quantity": qty})

    return {
        "status": "released",
        "order_id": order_id,
        "released_items": released,
    }


@router.post("/stock/confirm/{order_id}", response_model=dict)
async def confirm_stock_out(order_id: str):
    """
    Confirma saída de estoque (pedido entregue).

    Converte reserva em saída definitiva.
    """
    confirmed = []

    for movement in MOVEMENTS_DB:
        if (
            movement.get("reference_id") == order_id
            and movement.get("movement_type") == MovementType.RESERVE
        ):
            code = movement["product_code"]
            qty = movement["quantity"]

            if code in PRODUCTS_DB:
                # Remover da reserva e do estoque
                PRODUCTS_DB[code]["reserved_quantity"] -= qty
                PRODUCTS_DB[code]["stock_quantity"] -= qty
                PRODUCTS_DB[code]["reserved_quantity"] = max(0, PRODUCTS_DB[code]["reserved_quantity"])
                confirmed.append({"code": code, "quantity": qty})

    return {
        "status": "confirmed",
        "order_id": order_id,
        "confirmed_items": confirmed,
    }


@router.get("/stock/alerts", response_model=List[StockAlertResponse])
async def get_stock_alerts():
    """
    Lista produtos com estoque baixo.
    """
    alerts = []

    for code, product in PRODUCTS_DB.items():
        if not product["active"]:
            continue

        available = product["stock_quantity"] - product["reserved_quantity"]
        threshold = product["min_stock_alert"]

        if available <= 0:
            level = "OUT_OF_STOCK"
        elif available <= settings.critical_stock_threshold:
            level = "CRITICAL"
        elif available <= threshold:
            level = "LOW"
        else:
            continue

        alerts.append(StockAlertResponse(
            product_code=code,
            product_name=product["name"],
            current_stock=available,
            min_threshold=threshold,
            alert_level=level,
        ))

    # Ordenar por nível de alerta (mais crítico primeiro)
    level_order = {"OUT_OF_STOCK": 0, "CRITICAL": 1, "LOW": 2}
    alerts.sort(key=lambda x: level_order.get(x.alert_level, 99))

    return alerts


@router.get("/stock/movements", response_model=List[StockMovementResponse])
async def list_movements(
    product_code: Optional[str] = None,
    movement_type: Optional[MovementType] = None,
    limit: int = 50,
):
    """Lista histórico de movimentações."""
    movements = MOVEMENTS_DB.copy()

    if product_code:
        movements = [m for m in movements if m["product_code"] == product_code.upper()]

    if movement_type:
        movements = [m for m in movements if m["movement_type"] == movement_type]

    # Ordenar por data (mais recente primeiro)
    movements.sort(key=lambda x: x["created_at"], reverse=True)

    return movements[:limit]
