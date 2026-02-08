"""
Testes para Daily Summary Service.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.daily_summary_service import daily_summary_service


@pytest.mark.asyncio
async def test_generate_summary():
    """Testa geração de resumo diário."""
    mock_db = AsyncMock()

    # Resultados sequenciais para cada db.execute() (sync result objects)
    mock_result_total = MagicMock()
    mock_result_total.scalar.return_value = 10

    mock_result_status = MagicMock()
    mock_result_status.fetchall.return_value = [
        ("pending", 2),
        ("paid", 3),
        ("delivered", 5),
    ]

    mock_result_revenue = MagicMock()
    mock_result_revenue.scalar.return_value = 500.00

    mock_result_payments = MagicMock()
    mock_result_payments.scalar.return_value = 450.00

    mock_result_customers = MagicMock()
    mock_result_customers.scalar.return_value = 2

    mock_db.execute = AsyncMock(side_effect=[
        mock_result_total,
        mock_result_status,
        mock_result_revenue,
        mock_result_payments,
        mock_result_customers,
    ])

    summary = await daily_summary_service.generate_summary(mock_db)

    assert summary["total_orders"] == 10
    assert summary["delivered_orders"] == 5
    assert summary["revenue"] == 500.00


def test_format_summary_text():
    """Testa formatação de resumo em texto."""
    summary = {
        "date": "2026-01-28",
        "total_orders": 10,
        "delivered_orders": 5,
        "pending_orders": 3,
        "cancelled_orders": 2,
        "revenue": 500.00,
        "payments_received": 450.00,
        "avg_ticket": 100.00,
        "new_customers": 2,
        "conversion_rate": 50.0,
    }
    
    text = daily_summary_service.format_summary_text(summary)
    
    assert "Resumo Diário" in text
    assert "10" in text
    assert "R$ 500.00" in text