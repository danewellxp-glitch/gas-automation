"""
Testes para Operator Tracking Service.
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.services.operator_tracking_service import operator_tracking_service


@pytest.mark.asyncio
async def test_log_order_approval():
    """Testa registro de aprovação de pedido."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    operator_id = 1
    order_id = uuid4()
    
    await operator_tracking_service.log_order_approval(
        mock_db,
        operator_id=operator_id,
        order_id=order_id,
        approval_time_seconds=300.0,
    )
    
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_operator_metrics():
    """Testa cálculo de métricas de operador."""
    mock_db = AsyncMock()
    
    # Mock queries
    mock_result = AsyncMock()
    mock_result.scalar.return_value = 5.0  # 5 minutos
    
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    metrics = await operator_tracking_service.get_operator_metrics(
        mock_db,
        operator_id=1,
    )
    
    assert "operator_id" in metrics
    assert "avg_response_time_minutes" in metrics