"""Schemas Pydantic v2 para módulo de Estoque."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---- Supplier ----

class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=150)
    cnpj: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    cnpj: Optional[str]
    contact_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    is_active: bool
    created_at: datetime


# ---- StockProduct ----

class StockProductCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    unit: str = "unidade"
    cost_price: Decimal = Decimal("0.00")
    min_stock_alert: int = 10
    linked_product_code: Optional[str] = None


class StockProductUpdate(BaseModel):
    name: Optional[str] = None
    cost_price: Optional[Decimal] = None
    min_stock_alert: Optional[int] = None
    linked_product_code: Optional[str] = None
    is_active: Optional[bool] = None


class StockProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    unit: str
    cost_price: Decimal
    min_stock_alert: int
    linked_product_code: Optional[str]
    is_active: bool


# ---- StockBalance ----

class StockBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    stock_product_id: UUID
    quantity_depot: int
    quantity_in_transit: int
    quantity_with_customers: int
    last_updated: datetime
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    is_low_stock: bool = False


# ---- VehicleLoad ----

class LoadItemInput(BaseModel):
    stock_product_id: UUID
    quantity_loaded: int = Field(..., gt=0)


class VehicleLoadCreate(BaseModel):
    driver_id: UUID
    load_date: date
    items: List[LoadItemInput]
    notes: Optional[str] = None


class ReturnItemInput(BaseModel):
    stock_product_id: UUID
    quantity_returned: int = Field(..., ge=0)
    cheios_retornados: Optional[int] = Field(None, ge=0)   # Cheios que voltaram com o driver
    vazios_retornados: Optional[int] = Field(None, ge=0)   # Vazios que voltaram com o driver


class VehicleLoadClose(BaseModel):
    returned_items: List[ReturnItemInput]
    notes: Optional[str] = None


class VehicleLoadItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stock_product_id: UUID
    quantity_loaded: int
    quantity_delivered: int
    quantity_returned: int


class VehicleLoadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    driver_id: UUID
    load_date: date
    status: str
    closed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    items: List[VehicleLoadItemResponse] = []


# ---- StockMovement ----

class ManualAdjustmentInput(BaseModel):
    stock_product_id: UUID
    direction: str = Field(..., pattern="^(entrada|saida)$")
    quantity: int = Field(..., gt=0)
    notes: str = Field(..., min_length=5, description="Motivo do ajuste (obrigatório)")


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stock_product_id: UUID
    movement_type: str
    quantity: int
    direction: str
    unit_cost: Optional[Decimal]
    total_cost: Optional[Decimal]
    reference_type: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ---- PurchaseOrder ----

class PurchaseOrderItemInput(BaseModel):
    stock_product_id: UUID
    quantity_ordered: int = Field(..., gt=0)
    unit_cost: Decimal = Field(..., gt=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    order_date: date
    expected_delivery_date: Optional[date] = None
    items: List[PurchaseOrderItemInput]
    notes: Optional[str] = None


class ReceivedItemInput(BaseModel):
    stock_product_id: UUID
    quantity_received: int = Field(..., ge=0)
    unit_cost: Optional[Decimal] = None


class PurchaseOrderReceive(BaseModel):
    items: List[ReceivedItemInput]


class PurchaseOrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stock_product_id: UUID
    quantity_ordered: int
    quantity_received: int
    unit_cost: Decimal
    subtotal: Decimal


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    supplier_id: UUID
    order_date: date
    expected_delivery_date: Optional[date]
    status: str
    total_cost: Decimal
    notes: Optional[str]
    received_at: Optional[datetime]
    created_at: datetime
    items: List[PurchaseOrderItemResponse] = []


# ---- Dashboard ----

class EstoqueDashboardResponse(BaseModel):
    balances: List[StockBalanceResponse]
    low_stock_count: int
    total_in_transit: int
    open_loads_count: int
    movements_today: int
