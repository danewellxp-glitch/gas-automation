"""Schemas Pydantic v2 para módulo Financeiro."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---- Account ----

class AccountCreate(BaseModel):
    name: str = Field(..., max_length=100)
    type: str = Field(default="caixa")
    bank_name: Optional[str] = None
    agency: Optional[str] = None
    account_number: Optional[str] = None
    initial_balance: Decimal = Decimal("0.00")


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    bank_name: Optional[str] = None
    agency: Optional[str] = None
    account_number: Optional[str] = None
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    type: str
    bank_name: Optional[str]
    agency: Optional[str]
    account_number: Optional[str]
    balance: Decimal
    initial_balance: Decimal
    is_active: bool
    created_at: datetime


# ---- Transaction ----

class TransactionCreate(BaseModel):
    account_id: UUID
    type: str
    category: str
    description: str = Field(..., max_length=300)
    amount: Decimal = Field(..., gt=0)
    direction: str = Field(..., pattern="^(entrada|saida)$")
    reference_date: date
    due_date: Optional[date] = None
    is_paid: bool = False
    order_id: Optional[UUID] = None
    cost_center_id: Optional[UUID] = None
    notes: Optional[str] = None


class TransactionUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    reference_date: Optional[date] = None
    due_date: Optional[date] = None
    is_paid: Optional[bool] = None
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: UUID
    type: str
    category: str
    description: str
    amount: Decimal
    direction: str
    reference_date: date
    due_date: Optional[date]
    paid_at: Optional[datetime]
    is_paid: bool
    order_id: Optional[UUID]
    notes: Optional[str]
    created_at: datetime


class PaginatedTransactionsResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ---- Receivable ----

class ReceivableCreate(BaseModel):
    customer_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    description: str = Field(..., max_length=300)
    amount: Decimal = Field(..., gt=0)
    due_date: date
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class ReceivableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    customer_id: Optional[UUID]
    order_id: Optional[UUID]
    description: str
    amount: Decimal
    due_date: date
    received_at: Optional[datetime]
    status: str
    payment_method: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ---- Payable ----

class PayableCreate(BaseModel):
    supplier_id: Optional[UUID] = None
    category: str
    description: str = Field(..., max_length=300)
    amount: Decimal = Field(..., gt=0)
    due_date: date
    recurrence: Optional[str] = None
    notes: Optional[str] = None


class PayableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    supplier_id: Optional[UUID]
    category: str
    description: str
    amount: Decimal
    due_date: date
    paid_at: Optional[datetime]
    status: str
    recurrence: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ---- KPIs / Dashboard ----

class FinanceiroDashboardResponse(BaseModel):
    total_balance: Decimal
    revenue_month: Decimal
    expense_month: Decimal
    profit_month: Decimal
    overdue_receivables: int
    overdue_payables: int
    revenue_today: Decimal
    expense_today: Decimal


class DREResponse(BaseModel):
    period_start: date
    period_end: date
    gross_revenue: Decimal
    deductions: Decimal
    net_revenue: Decimal
    cost_of_goods: Decimal
    gross_profit: Decimal
    operating_expenses: dict
    ebitda: Decimal


class CashFlowDayResponse(BaseModel):
    date: date
    income: Decimal
    expense: Decimal
    balance: Decimal
    is_projected: bool


class CashFlowResponse(BaseModel):
    days: List[CashFlowDayResponse]
    opening_balance: Decimal


# ---- Cost Centers ----

class CostCenterCreate(BaseModel):
    name: str = Field(..., max_length=100)
    type: str
    reference_id: Optional[UUID] = None


class CostCenterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    type: str
    reference_id: Optional[UUID]
    is_active: bool
