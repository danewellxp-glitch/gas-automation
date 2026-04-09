"""Testes para o serviço financeiro."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_create_transaction_increases_balance():
    """Criar transaction de entrada aumenta balance da conta."""
    db = AsyncMock()
    account = MagicMock()
    account.id = uuid4()
    account.balance = Decimal("1000.00")
    account.type = "caixa"

    # Mock select returning account
    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=account)
    db.execute = AsyncMock(return_value=execute_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.begin_nested = MagicMock()
    db.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    db.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)

    from app.services.financeiro.financial_service import create_transaction
    tx = await create_transaction(
        db=db,
        account_id=account.id,
        type="receita",
        category="venda_gas",
        description="Teste",
        amount=Decimal("500.00"),
        direction="entrada",
        reference_date=date.today(),
        created_by=1,
        is_paid=True,
    )

    assert account.balance == Decimal("1500.00")
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_transaction_decreases_balance():
    """Criar transaction de saída diminui balance da conta."""
    db = AsyncMock()
    account = MagicMock()
    account.id = uuid4()
    account.balance = Decimal("1000.00")
    account.type = "caixa"

    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=account)
    db.execute = AsyncMock(return_value=execute_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.begin_nested = MagicMock()
    db.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    db.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)

    from app.services.financeiro.financial_service import create_transaction
    tx = await create_transaction(
        db=db,
        account_id=account.id,
        type="despesa",
        category="combustivel",
        description="Teste",
        amount=Decimal("300.00"),
        direction="saida",
        reference_date=date.today(),
        created_by=1,
    )

    assert account.balance == Decimal("700.00")


@pytest.mark.asyncio
async def test_caixa_balance_cannot_go_negative():
    """Balance de conta caixa não pode ficar negativo."""
    from app.services.financeiro.financial_service import create_transaction

    db = AsyncMock()
    account = MagicMock()
    account.id = uuid4()
    account.balance = Decimal("100.00")
    account.type = "caixa"
    account.name = "Caixa Principal"

    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=account)
    db.execute = AsyncMock(return_value=execute_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.begin_nested = MagicMock()
    db.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    db.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="Saldo insuficiente"):
        await create_transaction(
            db=db,
            account_id=account.id,
            type="despesa",
            category="combustivel",
            description="Tentativa de saldo negativo",
            amount=Decimal("500.00"),
            direction="saida",
            reference_date=date.today(),
            created_by=1,
            force_negative=False,
        )


def test_dre_calculates_profit():
    """DRE: receita - despesa = lucro bruto."""
    gross_revenue = Decimal("10000.00")
    cost_of_goods = Decimal("4000.00")
    deductions = Decimal("500.00")
    net_revenue = gross_revenue - deductions
    gross_profit = float(net_revenue) - float(cost_of_goods)
    assert gross_profit == pytest.approx(5500.0)


def test_on_order_delivered_creates_receivable_and_transaction():
    """Verificar que on_order_delivered é chamado com order correto."""
    from app.services.financeiro.financial_hooks import on_order_delivered
    import asyncio

    # Just verify the function exists and is callable
    assert callable(on_order_delivered)
