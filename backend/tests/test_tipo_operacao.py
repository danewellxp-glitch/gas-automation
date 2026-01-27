"""
Testes para Tipos de Operação (TROCA/VENDA/RETIRA).
"""

import pytest
from httpx import AsyncClient


class TestTipoOperacaoOrders:
    """Testes de tipo de operação em pedidos."""

    @pytest.mark.asyncio
    async def test_create_order_tipo_troca(self, authenticated_client: AsyncClient, sample_customer_data):
        """Testa criação de pedido com tipo TROCA."""
        # Criar cliente
        customer_response = await authenticated_client.post("/api/customers", json=sample_customer_data)
        assert customer_response.status_code in [200, 201]
        customer_id = customer_response.json()["id"]

        # Criar produto
        import uuid
        product_data = {
            "code": f"P{str(uuid.uuid4())[:3].upper()}",
            "name": "Botijão Teste Troca",
            "price": 110.00,
            "weight_kg": 13.0
        }
        product_response = await authenticated_client.post("/api/products", json=product_data)
        assert product_response.status_code in [200, 201]
        product_code = product_response.json()["code"]

        # Criar pedido com tipo TROCA
        order_data = {
            "customer_id": customer_id,
            "items": [{"product_code": product_code, "quantity": 1}],
            "payment_method": "pix",
            "tipo_operacao": "troca",
            "delivery_address": {
                "street": "Rua Teste",
                "number": "123",
                "bairro": "Centro",
                "city": "Curitiba",
                "state": "PR"
            }
        }
        response = await authenticated_client.post("/api/orders", json=order_data)
        assert response.status_code == 201
        data = response.json()
        assert data["tipo_operacao"] == "troca"

    @pytest.mark.asyncio
    async def test_create_order_tipo_venda(self, authenticated_client: AsyncClient, sample_customer_data):
        """Testa criação de pedido com tipo VENDA."""
        # Criar cliente
        customer_response = await authenticated_client.post("/api/customers", json=sample_customer_data)
        customer_id = customer_response.json()["id"]

        # Criar produto
        import uuid
        product_data = {
            "code": f"V{str(uuid.uuid4())[:3].upper()}",
            "name": "Botijão Teste Venda",
            "price": 110.00,
            "weight_kg": 13.0
        }
        product_response = await authenticated_client.post("/api/products", json=product_data)
        product_code = product_response.json()["code"]

        # Criar pedido com tipo VENDA
        order_data = {
            "customer_id": customer_id,
            "items": [{"product_code": product_code, "quantity": 1}],
            "payment_method": "dinheiro",
            "tipo_operacao": "venda",
            "delivery_address": {
                "street": "Rua Teste",
                "number": "456",
                "bairro": "Centro",
                "city": "Curitiba",
                "state": "PR"
            }
        }
        response = await authenticated_client.post("/api/orders", json=order_data)
        assert response.status_code == 201
        data = response.json()
        assert data["tipo_operacao"] == "venda"

    @pytest.mark.asyncio
    async def test_create_order_tipo_retira(self, authenticated_client: AsyncClient, sample_customer_data):
        """Testa criação de pedido com tipo RETIRA."""
        # Criar cliente
        customer_response = await authenticated_client.post("/api/customers", json=sample_customer_data)
        customer_id = customer_response.json()["id"]

        # Criar produto
        import uuid
        product_data = {
            "code": f"R{str(uuid.uuid4())[:3].upper()}",
            "name": "Botijão Teste Retira",
            "price": 110.00,
            "weight_kg": 13.0
        }
        product_response = await authenticated_client.post("/api/products", json=product_data)
        product_code = product_response.json()["code"]

        # Criar pedido com tipo RETIRA
        order_data = {
            "customer_id": customer_id,
            "items": [{"product_code": product_code, "quantity": 2}],
            "payment_method": "pix",
            "tipo_operacao": "retira",
            "delivery_address": {
                "street": "Rua Teste",
                "number": "789",
                "bairro": "Centro",
                "city": "Curitiba",
                "state": "PR"
            }
        }
        response = await authenticated_client.post("/api/orders", json=order_data)
        assert response.status_code == 201
        data = response.json()
        assert data["tipo_operacao"] == "retira"

    @pytest.mark.asyncio
    async def test_create_order_tipo_default(self, authenticated_client: AsyncClient, sample_customer_data):
        """Testa criação de pedido sem tipo (deve usar TROCA como default)."""
        # Criar cliente
        customer_response = await authenticated_client.post("/api/customers", json=sample_customer_data)
        customer_id = customer_response.json()["id"]

        # Criar produto
        import uuid
        product_data = {
            "code": f"D{str(uuid.uuid4())[:3].upper()}",
            "name": "Botijão Teste Default",
            "price": 110.00,
            "weight_kg": 13.0
        }
        product_response = await authenticated_client.post("/api/products", json=product_data)
        product_code = product_response.json()["code"]

        # Criar pedido SEM tipo_operacao
        order_data = {
            "customer_id": customer_id,
            "items": [{"product_code": product_code, "quantity": 1}],
            "payment_method": "pix",
            # tipo_operacao não informado
            "delivery_address": {
                "street": "Rua Teste",
                "number": "000",
                "bairro": "Centro",
                "city": "Curitiba",
                "state": "PR"
            }
        }
        response = await authenticated_client.post("/api/orders", json=order_data)
        assert response.status_code == 201
        data = response.json()
        # Default deve ser "troca"
        assert data["tipo_operacao"] == "troca"

    @pytest.mark.asyncio
    async def test_get_order_with_tipo_operacao(self, authenticated_client: AsyncClient, sample_customer_data):
        """Testa que tipo_operacao aparece na resposta do pedido."""
        # Criar cliente
        customer_response = await authenticated_client.post("/api/customers", json=sample_customer_data)
        customer_id = customer_response.json()["id"]

        # Criar produto
        import uuid
        product_data = {
            "code": f"G{str(uuid.uuid4())[:3].upper()}",
            "name": "Botijão Teste Get",
            "price": 110.00,
            "weight_kg": 13.0
        }
        product_response = await authenticated_client.post("/api/products", json=product_data)
        product_code = product_response.json()["code"]

        # Criar pedido
        order_data = {
            "customer_id": customer_id,
            "items": [{"product_code": product_code, "quantity": 1}],
            "payment_method": "pix",
            "tipo_operacao": "venda",
            "delivery_address": {
                "street": "Rua Teste",
                "number": "111",
                "bairro": "Centro",
                "city": "Curitiba",
                "state": "PR"
            }
        }
        create_response = await authenticated_client.post("/api/orders", json=order_data)
        order_id = create_response.json()["id"]

        # Buscar pedido
        response = await authenticated_client.get(f"/api/orders/{order_id}")
        assert response.status_code == 200
        data = response.json()
        assert "tipo_operacao" in data
        assert data["tipo_operacao"] == "venda"


class TestTipoOperacaoEnum:
    """Testes do enum TipoOperacao."""

    @pytest.mark.asyncio
    async def test_enum_values(self):
        """Testa valores do enum TipoOperacao."""
        from app.models.order import TipoOperacao

        assert TipoOperacao.TROCA.value == "troca"
        assert TipoOperacao.VENDA.value == "venda"
        assert TipoOperacao.RETIRA.value == "retira"

    @pytest.mark.asyncio
    async def test_enum_is_string(self):
        """Testa que TipoOperacao herda de str."""
        from app.models.order import TipoOperacao

        assert isinstance(TipoOperacao.TROCA, str)
        assert TipoOperacao.TROCA == "troca"
