"""
Fixtures compartilhados para testes dos handlers v2.
Todos os testes são unitários - mockam banco de dados e WebSocket.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)


@pytest.fixture
def conversation_context():
    """Contexto de conversa padrão."""
    return ConversationContext(
        phone="5541999999999",
        current_state=ConversationState.GREETING_INITIAL,
    )


@pytest.fixture
def customer_context():
    """Contexto de cliente conhecido."""
    return CustomerContext(
        customer_id="cust-123",
        name="João Silva",
        document="12345678901",
        customer_type="PF",
        addresses=[{
            "full_address": "Rua das Flores, 123 - Boqueirão",
            "bairro": "Boqueirão",
        }],
        order_count=3,
    )


@pytest.fixture
def customer_context_pj():
    """Contexto de cliente PJ."""
    return CustomerContext(
        customer_id="cust-456",
        name="Empresa XYZ LTDA",
        document="12345678000190",
        customer_type="PJ",
        addresses=[{
            "full_address": "Av. Brasil, 500 - Hauer",
            "bairro": "Hauer",
        }],
        order_count=10,
    )


@pytest.fixture
def order_context():
    """Contexto de pedido com itens."""
    return OrderContext(
        items=[{
            "product_code": "P13",
            "quantity": 2,
            "unit_price": 110.0,
            "subtotal": 220.0,
            "operation_type": "exchange",
        }],
        subtotal=220.0,
        delivery_fee=0.0,
        total=220.0,
        address={
            "full_address": "Rua das Flores, 123 - Boqueirão",
            "bairro": "Boqueirão",
        },
        operation_type="exchange",
        payment_method="pix",
    )


@pytest.fixture
def order_context_empty():
    """Contexto de pedido vazio."""
    return OrderContext()


@pytest.fixture
def customer_context_new():
    """Contexto de cliente novo (sem dados)."""
    return CustomerContext()


@pytest.fixture
def customer_context_with_last_order():
    """Cliente com último pedido para repeat."""
    return CustomerContext(
        customer_id="cust-789",
        name="Maria Souza",
        customer_type="PF",
        addresses=[{
            "full_address": "Rua Xaxim, 50 - Xaxim",
            "bairro": "Xaxim",
        }],
        last_order={
            "order_number": "1001",
            "total": 110.0,
            "items": [{
                "product_code": "P13",
                "quantity": 1,
                "unit_price": 110.0,
                "subtotal": 110.0,
            }],
        },
        order_count=5,
    )


@pytest.fixture
def mock_db_no_customer():
    """Mock para _get_customer_by_phone retornando None."""
    with patch(
        "app.core.handlers_v2.base.BaseHandler._get_customer_by_phone",
        new_callable=AsyncMock,
        return_value=None,
    ) as m:
        yield m


@pytest.fixture
def mock_db_customer():
    """Mock para _get_customer_by_phone retornando cliente."""
    customer = MagicMock()
    customer.id = "cust-123"
    customer.name = "João Silva"
    customer.phone = "5541999999999"
    customer.cpf_cnpj = "12345678901"
    customer.tipo_documento = "PF"
    customer.address = {
        "full_address": "Rua das Flores, 123 - Boqueirão",
        "bairro": "Boqueirão",
    }
    with patch(
        "app.core.handlers_v2.base.BaseHandler._get_customer_by_phone",
        new_callable=AsyncMock,
        return_value=customer,
    ) as m:
        yield m


@pytest.fixture
def mock_db_last_order():
    """Mock para _get_last_order retornando pedido."""
    order = MagicMock()
    order.id = "order-001"
    order.order_number = "1001"
    order.total_amount = Decimal("220.00")
    order.status = "pending"
    order.created_at = None
    with patch(
        "app.core.handlers_v2.base.BaseHandler._get_last_order",
        new_callable=AsyncMock,
        return_value=order,
    ) as m:
        yield m


@pytest.fixture
def mock_db_no_last_order():
    """Mock para _get_last_order retornando None."""
    with patch(
        "app.core.handlers_v2.base.BaseHandler._get_last_order",
        new_callable=AsyncMock,
        return_value=None,
    ) as m:
        yield m


@pytest.fixture
def mock_websocket():
    """Mock para WebSocket emit."""
    with patch("app.api.websocket.emit_new_message", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_async_session():
    """Mock para AsyncSessionLocal."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    with patch("app.database.AsyncSessionLocal", return_value=session) as m:
        yield session
