"""Serviço Financeiro — lógica de negócio do módulo financeiro."""
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financeiro.account import Account
from app.models.financeiro.transaction import Transaction, TransactionType
from app.models.financeiro.receivable import Receivable, ReceivableStatus
from app.models.financeiro.payable import Payable, PayableStatus
from app.schemas.financeiro import (
    CashFlowDayResponse,
    CashFlowResponse,
    DREResponse,
    FinanceiroDashboardResponse,
)

logger = logging.getLogger(__name__)


class StockInsuficienteError(Exception):
    pass


async def create_transaction(
    db: AsyncSession,
    account_id: UUID,
    type: str,
    category: str,
    description: str,
    amount: Decimal,
    direction: str,
    reference_date: date,
    created_by: int,
    due_date: Optional[date] = None,
    is_paid: bool = True,
    order_id: Optional[UUID] = None,
    receivable_id: Optional[UUID] = None,
    payable_id: Optional[UUID] = None,
    cost_center_id: Optional[UUID] = None,
    notes: Optional[str] = None,
    force_negative: bool = False,
) -> Transaction:
    """Cria uma transação e atualiza o saldo da conta."""
    async with db.begin_nested():
        # Lock the account row
        result = await db.execute(
            select(Account).where(Account.id == account_id).with_for_update()
        )
        account = result.scalar_one_or_none()
        if not account:
            raise ValueError(f"Conta {account_id} não encontrada")

        # Update balance
        if direction == "entrada":
            account.balance += amount
        else:
            new_balance = account.balance - amount
            if new_balance < 0 and account.type == "caixa" and not force_negative:
                raise ValueError(
                    f"Saldo insuficiente na conta '{account.name}'. "
                    f"Saldo atual: R$ {account.balance:.2f}"
                )
            account.balance = new_balance

        paid_at = datetime.now(timezone.utc) if is_paid else None

        tx = Transaction(
            account_id=account_id,
            type=type,
            category=category,
            description=description,
            amount=amount,
            direction=direction,
            reference_date=reference_date,
            due_date=due_date,
            paid_at=paid_at,
            is_paid=is_paid,
            order_id=order_id,
            receivable_id=receivable_id,
            payable_id=payable_id,
            cost_center_id=cost_center_id,
            created_by=created_by,
            notes=notes,
        )
        db.add(tx)
        await db.flush()

    return tx


async def register_order_payment(
    db: AsyncSession,
    order_id: UUID,
    amount: Decimal,
    created_by: int,
    customer_id: Optional[UUID] = None,
    payment_method: Optional[str] = None,
) -> Transaction:
    """Registra pagamento de pedido — cria Receivable + Transaction."""
    # Get default account
    result = await db.execute(
        select(Account).where(Account.is_active == True, Account.deleted_at == None).limit(1)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise ValueError("Nenhuma conta ativa encontrada para registrar o pagamento")

    today = date.today()

    # Create receivable as received
    receivable = Receivable(
        customer_id=customer_id,
        order_id=order_id,
        description=f"Pagamento pedido",
        amount=amount,
        due_date=today,
        received_at=datetime.now(timezone.utc),
        status=ReceivableStatus.recebido.value,
        payment_method=payment_method,
    )
    db.add(receivable)
    await db.flush()

    # Create transaction
    tx = await create_transaction(
        db=db,
        account_id=account.id,
        type=TransactionType.receita.value,
        category="venda_gas",
        description="Receita de venda de gás",
        amount=amount,
        direction="entrada",
        reference_date=today,
        is_paid=True,
        order_id=order_id,
        receivable_id=receivable.id,
        created_by=created_by,
    )
    return tx


async def get_dashboard(db: AsyncSession) -> FinanceiroDashboardResponse:
    """Retorna KPIs do painel financeiro."""
    today = date.today()
    first_of_month = today.replace(day=1)

    # Total balance across all active accounts
    result = await db.execute(
        select(func.sum(Account.balance)).where(
            Account.is_active == True, Account.deleted_at == None
        )
    )
    total_balance = result.scalar() or Decimal("0.00")

    # Revenue this month
    result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.type == TransactionType.receita.value,
                Transaction.reference_date >= first_of_month,
                Transaction.deleted_at == None,
            )
        )
    )
    revenue_month = result.scalar() or Decimal("0.00")

    # Expense this month
    result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.type == TransactionType.despesa.value,
                Transaction.reference_date >= first_of_month,
                Transaction.deleted_at == None,
            )
        )
    )
    expense_month = result.scalar() or Decimal("0.00")

    # Revenue today
    result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.type == TransactionType.receita.value,
                Transaction.reference_date == today,
                Transaction.deleted_at == None,
            )
        )
    )
    revenue_today = result.scalar() or Decimal("0.00")

    # Expense today
    result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.type == TransactionType.despesa.value,
                Transaction.reference_date == today,
                Transaction.deleted_at == None,
            )
        )
    )
    expense_today = result.scalar() or Decimal("0.00")

    # Overdue receivables
    result = await db.execute(
        select(func.count(Receivable.id)).where(
            and_(
                Receivable.status == ReceivableStatus.pendente.value,
                Receivable.due_date < today,
                Receivable.deleted_at == None,
            )
        )
    )
    overdue_receivables = result.scalar() or 0

    # Overdue payables
    result = await db.execute(
        select(func.count(Payable.id)).where(
            and_(
                Payable.status == PayableStatus.pendente.value,
                Payable.due_date < today,
                Payable.deleted_at == None,
            )
        )
    )
    overdue_payables = result.scalar() or 0

    return FinanceiroDashboardResponse(
        total_balance=total_balance,
        revenue_month=revenue_month,
        expense_month=expense_month,
        profit_month=revenue_month - expense_month,
        overdue_receivables=overdue_receivables,
        overdue_payables=overdue_payables,
        revenue_today=revenue_today,
        expense_today=expense_today,
    )


async def get_dre(db: AsyncSession, start_date: date, end_date: date) -> DREResponse:
    """DRE simplificado."""
    # Gross revenue
    result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.type == TransactionType.receita.value,
                Transaction.reference_date >= start_date,
                Transaction.reference_date <= end_date,
                Transaction.deleted_at == None,
            )
        )
    )
    gross_revenue = result.scalar() or Decimal("0.00")

    # Expenses by category
    result = await db.execute(
        select(Transaction.category, func.sum(Transaction.amount)).where(
            and_(
                Transaction.type == TransactionType.despesa.value,
                Transaction.reference_date >= start_date,
                Transaction.reference_date <= end_date,
                Transaction.deleted_at == None,
            )
        ).group_by(Transaction.category)
    )
    rows = result.all()
    operating_expenses = {row[0]: float(row[1]) for row in rows}

    total_expenses = sum(operating_expenses.values())
    cost_of_goods = float(operating_expenses.get("compra_gas", 0))
    deductions = float(operating_expenses.get("impostos", 0))
    net_revenue = float(gross_revenue) - deductions
    gross_profit = net_revenue - cost_of_goods
    ebitda = gross_profit - (total_expenses - cost_of_goods - deductions)

    return DREResponse(
        period_start=start_date,
        period_end=end_date,
        gross_revenue=gross_revenue,
        deductions=Decimal(str(deductions)),
        net_revenue=Decimal(str(net_revenue)),
        cost_of_goods=Decimal(str(cost_of_goods)),
        gross_profit=Decimal(str(gross_profit)),
        operating_expenses=operating_expenses,
        ebitda=Decimal(str(ebitda)),
    )


async def get_cash_flow(
    db: AsyncSession, account_id: Optional[UUID], days: int = 30
) -> CashFlowResponse:
    """Fluxo de caixa: realizado + projeção."""
    today = date.today()
    start_date = today - timedelta(days=15)
    end_date = today + timedelta(days=15)

    # Get opening balance
    if account_id:
        result = await db.execute(
            select(Account.balance).where(Account.id == account_id)
        )
        current_balance = result.scalar() or Decimal("0.00")
    else:
        result = await db.execute(
            select(func.sum(Account.balance)).where(
                Account.is_active == True, Account.deleted_at == None
            )
        )
        current_balance = result.scalar() or Decimal("0.00")

    # Get transactions per day (past)
    conditions = [
        Transaction.reference_date >= start_date,
        Transaction.reference_date <= today,
        Transaction.deleted_at == None,
    ]
    if account_id:
        conditions.append(Transaction.account_id == account_id)

    result = await db.execute(
        select(
            Transaction.reference_date,
            Transaction.direction,
            func.sum(Transaction.amount)
        ).where(and_(*conditions)).group_by(Transaction.reference_date, Transaction.direction)
    )
    tx_rows = result.all()

    # Get projected (future) from payables/receivables
    future_income: dict = {}
    future_expense: dict = {}

    recv_result = await db.execute(
        select(Receivable.due_date, func.sum(Receivable.amount)).where(
            and_(
                Receivable.status == ReceivableStatus.pendente.value,
                Receivable.due_date > today,
                Receivable.due_date <= end_date,
                Receivable.deleted_at == None,
            )
        ).group_by(Receivable.due_date)
    )
    for r in recv_result.all():
        future_income[r[0]] = r[1]

    pay_result = await db.execute(
        select(Payable.due_date, func.sum(Payable.amount)).where(
            and_(
                Payable.status == PayableStatus.pendente.value,
                Payable.due_date > today,
                Payable.due_date <= end_date,
                Payable.deleted_at == None,
            )
        ).group_by(Payable.due_date)
    )
    for r in pay_result.all():
        future_expense[r[0]] = r[1]

    # Build daily map
    daily: dict = {}
    for ref_date, direction, total in tx_rows:
        if ref_date not in daily:
            daily[ref_date] = {"income": Decimal("0.00"), "expense": Decimal("0.00")}
        if direction == "entrada":
            daily[ref_date]["income"] += total
        else:
            daily[ref_date]["expense"] += total

    # Build result days
    days_list = []
    running_balance = current_balance
    all_dates = sorted(set(
        list(daily.keys()) +
        [today + timedelta(days=i) for i in range(1, 16)] +
        list(future_income.keys()) + list(future_expense.keys())
    ))

    for d in all_dates:
        if start_date <= d <= end_date:
            is_proj = d > today
            inc = daily.get(d, {}).get("income", Decimal("0.00")) if not is_proj else future_income.get(d, Decimal("0.00"))
            exp = daily.get(d, {}).get("expense", Decimal("0.00")) if not is_proj else future_expense.get(d, Decimal("0.00"))
            if not is_proj:
                running_balance = running_balance  # already included in current_balance for past
            days_list.append(CashFlowDayResponse(
                date=d,
                income=inc,
                expense=exp,
                balance=running_balance + inc - exp if is_proj else inc - exp,
                is_projected=is_proj,
            ))

    return CashFlowResponse(days=days_list, opening_balance=current_balance)
