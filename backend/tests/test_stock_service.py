"""Testes para o serviço de estoque."""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


def make_balance(depot=100, in_transit=0, with_customers=0):
    balance = MagicMock()
    balance.quantity_depot = depot
    balance.quantity_in_transit = in_transit
    balance.quantity_with_customers = with_customers
    balance.last_updated = None
    return balance


def make_product(code="P13", min_stock=10):
    p = MagicMock()
    p.id = uuid4()
    p.code = code
    p.name = f"Botijão {code}"
    p.min_stock_alert = min_stock
    p.cost_price = Decimal("50.00")
    return p


@pytest.mark.asyncio
async def test_open_vehicle_load_reduces_depot_increases_transit():
    """open_vehicle_load reduz quantity_depot e aumenta quantity_in_transit."""
    from app.services.estoque.stock_service import add_stock_movement
    from app.models.estoque.stock_movement import MovementType

    db = AsyncMock()
    balance = make_balance(depot=50)
    product = make_product()

    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=balance)
    db.execute = AsyncMock(return_value=execute_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.begin_nested = MagicMock()
    db.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    db.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)

    # Patch redis_ws_bridge to avoid redis dependency
    with patch('app.services.estoque.stock_service.redis_ws_bridge') as mock_bridge:
        mock_bridge.publish_event = AsyncMock()
        # Patch select for product lookup
        execute_result2 = AsyncMock()
        execute_result2.scalar_one_or_none = MagicMock(return_value=product)
        db.execute = AsyncMock(side_effect=[execute_result, execute_result2])

        movement = await add_stock_movement(
            db=db,
            stock_product_id=product.id,
            movement_type=MovementType.carga_veiculo.value,
            quantity=10,
            direction="saida",
            created_by=1,
        )

    # depot should decrease, in_transit should increase
    assert balance.quantity_depot == 40
    assert balance.quantity_in_transit == 10


@pytest.mark.asyncio
async def test_stock_cannot_go_negative():
    """Estoque insuficiente lança StockInsuficienteError."""
    from app.services.estoque.stock_service import add_stock_movement, StockInsuficienteError
    from app.models.estoque.stock_movement import MovementType

    db = AsyncMock()
    balance = make_balance(depot=5)  # only 5
    product = make_product()

    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=balance)
    db.execute = AsyncMock(return_value=execute_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.begin_nested = MagicMock()
    db.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    db.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch('app.services.estoque.stock_service.select'):
        with pytest.raises(StockInsuficienteError):
            await add_stock_movement(
                db=db,
                stock_product_id=product.id,
                movement_type=MovementType.carga_veiculo.value,
                quantity=10,  # more than available (5)
                direction="saida",
                created_by=1,
            )


@pytest.mark.asyncio
async def test_close_vehicle_load_restores_balance():
    """close_vehicle_load com retorno restaura saldo corretamente."""
    from app.services.estoque.stock_service import add_stock_movement
    from app.models.estoque.stock_movement import MovementType

    db = AsyncMock()
    balance = make_balance(depot=0, in_transit=20)
    product = make_product()

    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=balance)
    execute_result2 = AsyncMock()
    execute_result2.scalar_one_or_none = MagicMock(return_value=product)
    db.execute = AsyncMock(side_effect=[execute_result, execute_result2])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.begin_nested = MagicMock()
    db.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    db.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch('app.services.estoque.stock_service.redis_ws_bridge') as mock_bridge:
        mock_bridge.publish_event = AsyncMock()
        await add_stock_movement(
            db=db,
            stock_product_id=product.id,
            movement_type=MovementType.retorno_veiculo.value,
            quantity=5,
            direction="entrada",
            created_by=1,
        )

    # in_transit decreases, depot increases
    assert balance.quantity_in_transit == 15
    assert balance.quantity_depot == 5


def test_auto_deduct_on_delivery_is_callable():
    """Verificar que auto_deduct_on_delivery existe."""
    from app.services.estoque.stock_service import auto_deduct_on_delivery
    assert callable(auto_deduct_on_delivery)
