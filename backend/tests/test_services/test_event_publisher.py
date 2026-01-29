"""
Testes para Event Publisher Service.
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.services.event_publisher import event_publisher


@pytest.mark.asyncio
async def test_publish_order_event():
    """Testa publicação de evento de pedido."""
    with patch('app.services.event_publisher.event_publisher._get_redis') as mock_redis:
        mock_redis_client = AsyncMock()
        mock_redis.return_value = mock_redis_client
        
        order_id = str(uuid4())
        customer_id = str(uuid4())
        
        result = await event_publisher.publish_order_event(
            event_type="order.created",
            order_id=order_id,
            order_number=123,
            customer_id=customer_id,
            customer_phone="5541999999999",
            status="pending",
        )
        
        assert result is True
        mock_redis_client.xadd.assert_called_once()


@pytest.mark.asyncio
async def test_publish_payment_event():
    """Testa publicação de evento de pagamento."""
    with patch('app.services.event_publisher.event_publisher._get_redis') as mock_redis:
        mock_redis_client = AsyncMock()
        mock_redis.return_value = mock_redis_client
        
        payment_id = str(uuid4())
        order_id = str(uuid4())
        
        result = await event_publisher.publish_payment_event(
            event_type="payment.confirmed",
            payment_id=payment_id,
            order_id=order_id,
            order_number=123,
            amount=100.00,
            status="confirmed",
        )
        
        assert result is True
        mock_redis_client.xadd.assert_called_once()


@pytest.mark.asyncio
async def test_publish_notification():
    """Testa publicação de notificação."""
    with patch('app.services.event_publisher.event_publisher._get_redis') as mock_redis:
        mock_redis_client = AsyncMock()
        mock_redis.return_value = mock_redis_client
        
        result = await event_publisher.publish_notification(
            notification_type="whatsapp",
            recipient_phone="5541999999999",
            message="Teste",
        )
        
        assert result is True
        mock_redis_client.xadd.assert_called_once()