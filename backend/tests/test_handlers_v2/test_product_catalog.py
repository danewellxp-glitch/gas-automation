"""
Testes unitários para Product Catalog v2.
"""

import pytest
from decimal import Decimal

from app.core.product_catalog import (
    PRODUCTS_CATALOG,
    COVERAGE_AREAS,
    PAYMENT_METHODS,
    BUSINESS_HOURS,
    OPERATION_TYPES,
    get_product,
    get_active_products,
    get_coverage_area,
    is_area_covered,
    get_payment_methods_for_customer,
    calculate_price,
    is_business_open,
    can_deliver_now,
)


# ═══════════════════════════════════════════════════════════════
# Products
# ═══════════════════════════════════════════════════════════════


class TestProducts:
    """Testes para catálogo de produtos."""

    def test_three_products_exist(self):
        """Existem 3 produtos no catálogo."""
        assert len(PRODUCTS_CATALOG) == 3

    def test_p13_exists(self):
        """P13 existe no catálogo."""
        assert "P13" in PRODUCTS_CATALOG

    def test_p20_exists(self):
        """P20 existe no catálogo."""
        assert "P20" in PRODUCTS_CATALOG

    def test_p45_exists(self):
        """P45 existe no catálogo."""
        assert "P45" in PRODUCTS_CATALOG

    def test_p13_prices(self):
        """P13 tem preços corretos (site GÁSMASTER - gás de cozinha)."""
        p13 = PRODUCTS_CATALOG["P13"]
        assert p13.price_exchange == Decimal("110.00")
        assert p13.price_sale == Decimal("110.00")

    def test_p20_prices(self):
        """P20 tem preços corretos (site GÁSMASTER - industrial empilhadeiras)."""
        p20 = PRODUCTS_CATALOG["P20"]
        assert p20.price_exchange == Decimal("210.00")
        assert p20.price_sale == Decimal("210.00")

    def test_p45_prices(self):
        """P45 tem preços corretos (site GÁSMASTER - doméstico/industrial)."""
        p45 = PRODUCTS_CATALOG["P45"]
        assert p45.price_exchange == Decimal("430.00")
        assert p45.price_sale == Decimal("430.00")

    def test_p45_is_commercial(self):
        """P45 é produto comercial."""
        assert PRODUCTS_CATALOG["P45"].is_commercial is True

    def test_p13_not_commercial(self):
        """P13 não é comercial."""
        assert PRODUCTS_CATALOG["P13"].is_commercial is False

    def test_all_products_active(self):
        """Todos os produtos estão ativos."""
        for product in PRODUCTS_CATALOG.values():
            assert product.is_active is True

    def test_weights(self):
        """Pesos corretos."""
        assert PRODUCTS_CATALOG["P13"].weight_kg == 13.0
        assert PRODUCTS_CATALOG["P20"].weight_kg == 20.0
        assert PRODUCTS_CATALOG["P45"].weight_kg == 45.0


class TestGetProduct:
    """Testes para get_product."""

    def test_get_p13(self):
        product = get_product("P13")
        assert product is not None
        assert product.code == "P13"

    def test_get_lowercase(self):
        """Busca case-insensitive."""
        product = get_product("p13")
        assert product is not None
        assert product.code == "P13"

    def test_get_nonexistent(self):
        product = get_product("P99")
        assert product is None


class TestGetActiveProducts:
    """Testes para get_active_products."""

    def test_returns_all_active(self):
        products = get_active_products()
        assert len(products) == 3

    def test_sorted_by_sort_order(self):
        products = get_active_products()
        assert products[0].code == "P13"
        assert products[1].code == "P20"
        assert products[2].code == "P45"


# ═══════════════════════════════════════════════════════════════
# Coverage Areas
# ═══════════════════════════════════════════════════════════════


class TestCoverageAreas:
    """Testes para áreas de cobertura."""

    def test_seven_areas(self):
        """Existem 7 áreas de cobertura."""
        assert len(COVERAGE_AREAS) == 7

    def test_supported_bairros(self):
        """Bairros suportados."""
        expected = [
            "Alto Boqueirão", "Boqueirão", "Ganchinho",
            "Hauer", "Sítio Cercado", "Umbará", "Xaxim",
        ]
        for bairro in expected:
            assert bairro in COVERAGE_AREAS

    def test_boqueirao_free_delivery(self):
        """Boqueirão tem entrega grátis."""
        area = COVERAGE_AREAS["Boqueirão"]
        assert area.delivery_fee == Decimal("0.00")

    def test_umbara_has_delivery_fee(self):
        """Umbará tem taxa de entrega."""
        area = COVERAGE_AREAS["Umbará"]
        assert area.delivery_fee == Decimal("8.00")

    def test_ganchinho_min_order(self):
        """Ganchinho tem valor mínimo."""
        area = COVERAGE_AREAS["Ganchinho"]
        assert area.min_order_value == Decimal("100.00")


class TestGetCoverageArea:
    """Testes para get_coverage_area."""

    def test_find_boqueirao(self):
        area = get_coverage_area("Boqueirão")
        assert area is not None
        assert area.bairro == "Boqueirão"

    def test_case_insensitive(self):
        area = get_coverage_area("boqueirão")
        assert area is not None

    def test_not_found(self):
        area = get_coverage_area("Centro")
        assert area is None


class TestIsAreaCovered:
    """Testes para is_area_covered."""

    def test_covered(self):
        assert is_area_covered("Boqueirão") is True

    def test_not_covered(self):
        assert is_area_covered("Centro") is False


# ═══════════════════════════════════════════════════════════════
# Payment Methods
# ═══════════════════════════════════════════════════════════════


class TestPaymentMethods:
    """Testes para métodos de pagamento."""

    def test_five_payment_methods(self):
        """Existem 5 métodos de pagamento."""
        assert len(PAYMENT_METHODS) == 5

    def test_cash_available_for_all(self):
        """Dinheiro disponível para PF e PJ."""
        assert "pf" in PAYMENT_METHODS["cash"].available_for
        assert "pj" in PAYMENT_METHODS["cash"].available_for

    def test_invoice_only_pj(self):
        """Faturado apenas para PJ."""
        assert PAYMENT_METHODS["invoice"].available_for == ["pj"]

    def test_cash_requires_change(self):
        """Dinheiro requer troco."""
        assert PAYMENT_METHODS["cash"].requires_change is True

    def test_pix_no_change(self):
        """PIX não requer troco."""
        assert PAYMENT_METHODS["pix"].requires_change is False


class TestGetPaymentMethodsForCustomer:
    """Testes para get_payment_methods_for_customer."""

    def test_pf_has_4_methods(self):
        """PF tem 4 métodos (sem faturado)."""
        methods = get_payment_methods_for_customer("PF")
        codes = [m.code for m in methods]
        assert len(methods) == 4
        assert "invoice" not in codes

    def test_pj_has_5_methods(self):
        """PJ tem 5 métodos (incluindo faturado)."""
        methods = get_payment_methods_for_customer("PJ")
        codes = [m.code for m in methods]
        assert len(methods) == 5
        assert "invoice" in codes


# ═══════════════════════════════════════════════════════════════
# Calculate Price
# ═══════════════════════════════════════════════════════════════


class TestCalculatePrice:
    """Testes para calculate_price."""

    def test_p13_exchange_1(self):
        """P13 troca x1 = R$ 110."""
        price = calculate_price("P13", 1, "exchange")
        assert price == Decimal("110.00")

    def test_p13_exchange_2(self):
        """P13 troca x2 = R$ 220."""
        price = calculate_price("P13", 2, "exchange")
        assert price == Decimal("220.00")

    def test_p13_sale_1(self):
        """P13 venda x1 = R$ 110 (site GÁSMASTER)."""
        price = calculate_price("P13", 1, "sale")
        assert price == Decimal("110.00")

    def test_p20_pickup(self):
        """P20 pickup x1 = R$ 210 (preço exchange - site GÁSMASTER)."""
        price = calculate_price("P20", 1, "pickup")
        assert price == Decimal("210.00")

    def test_p45_sale_3(self):
        """P45 venda x3 = R$ 1290 (site GÁSMASTER)."""
        price = calculate_price("P45", 3, "sale")
        assert price == Decimal("1290.00")

    def test_nonexistent_product(self):
        """Produto inexistente retorna None."""
        price = calculate_price("P99", 1, "exchange")
        assert price is None


# ═══════════════════════════════════════════════════════════════
# Business Hours
# ═══════════════════════════════════════════════════════════════


class TestBusinessHours:
    """Testes para horário de funcionamento."""

    def test_weekdays_open(self):
        """Seg-Sex abertos."""
        for day in range(5):
            assert BUSINESS_HOURS[day].is_open is True

    def test_saturday_open(self):
        """Sábado aberto (horário reduzido)."""
        assert BUSINESS_HOURS[5].is_open is True
        assert BUSINESS_HOURS[5].close_time == "12:00"

    def test_sunday_closed(self):
        """Domingo fechado."""
        assert BUSINESS_HOURS[6].is_open is False

    def test_is_business_open_weekday(self):
        assert is_business_open(0, "10:00") is True

    def test_is_business_open_before_opening(self):
        assert is_business_open(0, "07:00") is False

    def test_is_business_open_after_closing(self):
        assert is_business_open(0, "19:00") is False

    def test_is_business_open_sunday(self):
        assert is_business_open(6, "10:00") is False

    def test_can_deliver_now_weekday(self):
        assert can_deliver_now(0, "10:00") is True

    def test_can_deliver_after_cutoff(self):
        assert can_deliver_now(0, "18:00") is False

    def test_can_deliver_saturday(self):
        assert can_deliver_now(5, "10:00") is True

    def test_can_deliver_saturday_after_cutoff(self):
        assert can_deliver_now(5, "12:00") is False


# ═══════════════════════════════════════════════════════════════
# Operation Types
# ═══════════════════════════════════════════════════════════════


class TestOperationTypes:
    """Testes para tipos de operação."""

    def test_three_types(self):
        """Existem 3 tipos de operação."""
        assert len(OPERATION_TYPES) == 3

    def test_exchange_requires_delivery(self):
        assert OPERATION_TYPES["exchange"].requires_delivery is True

    def test_pickup_no_delivery(self):
        assert OPERATION_TYPES["pickup"].requires_delivery is False

    def test_sale_no_empty_bottle(self):
        assert OPERATION_TYPES["sale"].requires_empty_bottle is False

    def test_exchange_requires_empty_bottle(self):
        assert OPERATION_TYPES["exchange"].requires_empty_bottle is True
