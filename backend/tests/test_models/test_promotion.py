"""
Testes para modelo Promotion.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from app.models.promotion import Promotion


def test_promotion_is_valid():
    """Testa validação de promoção."""
    promotion = Promotion(
        code="TEST10",
        name="Teste 10%",
        discount_type="percentage",
        discount_value=Decimal("10"),
        min_order_value=Decimal("50"),
        valid_from=date.today() - timedelta(days=1),
        valid_until=date.today() + timedelta(days=30),
        is_active=True,
        usage_limit=100,
        usage_count=0,
    )
    
    # Válida
    is_valid, error = promotion.is_valid(Decimal("100"))
    assert is_valid is True
    assert error is None
    
    # Valor mínimo não atingido
    is_valid, error = promotion.is_valid(Decimal("30"))
    assert is_valid is False
    assert "mínimo" in error.lower()
    
    # Limite atingido
    promotion.usage_count = 100
    is_valid, error = promotion.is_valid(Decimal("100"))
    assert is_valid is False
    assert "limite" in error.lower()


def test_promotion_calculate_discount_percentage():
    """Testa cálculo de desconto percentual."""
    promotion = Promotion(
        code="TEST10",
        name="Teste 10%",
        discount_type="percentage",
        discount_value=Decimal("10"),
        valid_from=date.today(),
        is_active=True,
    )
    
    discount = promotion.calculate_discount(Decimal("100"))
    assert discount == Decimal("10.00")


def test_promotion_calculate_discount_fixed():
    """Testa cálculo de desconto fixo."""
    promotion = Promotion(
        code="TEST20",
        name="Teste R$20",
        discount_type="fixed",
        discount_value=Decimal("20"),
        valid_from=date.today(),
        is_active=True,
    )
    
    discount = promotion.calculate_discount(Decimal("100"))
    assert discount == Decimal("20.00")
    
    # Desconto não pode ser maior que valor do pedido
    discount = promotion.calculate_discount(Decimal("10"))
    assert discount == Decimal("10.00")