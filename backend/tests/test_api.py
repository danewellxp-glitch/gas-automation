"""
Testes de integração das APIs.
"""

import pytest
from httpx import AsyncClient


class TestAuthAPI:
    """Testes da API de autenticação."""

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Testa login com credenciais inválidas."""
        response = await client.post(
            "/api/auth/token",
            data={"username": "invalid", "password": "invalid"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Testa acesso a endpoint protegido sem token."""
        response = await client.post("/api/orders", json={})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, client: AsyncClient):
        """Testa acesso a endpoint protegido com token inválido."""
        client.headers["Authorization"] = "Bearer invalid_token"
        response = await client.post("/api/orders", json={})
        assert response.status_code == 401
        del client.headers["Authorization"]

    @pytest.mark.asyncio
    async def test_get_current_user(self, authenticated_client: AsyncClient):
        """Testa obtenção do usuário atual."""
        response = await authenticated_client.get("/api/auth/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"


class TestHealthEndpoints:
    """Testes dos endpoints de saúde."""

    @pytest.mark.asyncio
    async def test_root(self, client: AsyncClient):
        """Testa endpoint raiz."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        """Testa endpoint de saúde."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "services" in data


class TestProductsAPI:
    """Testes da API de produtos."""

    @pytest.mark.asyncio
    async def test_list_products(self, client: AsyncClient):
        """Testa listagem de produtos."""
        response = await client.get("/api/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_product(self, client: AsyncClient, sample_product_data):
        """Testa criação de produto."""
        response = await client.post("/api/products", json=sample_product_data)
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["code"] == sample_product_data["code"]
        assert data["name"] == sample_product_data["name"]

    @pytest.mark.asyncio
    async def test_get_product(self, client: AsyncClient, sample_product_data):
        """Testa obtenção de produto específico."""
        # Criar produto
        create_response = await client.post("/api/products", json=sample_product_data)
        assert create_response.status_code in [200, 201]
        product_id = create_response.json()["id"]

        # Buscar produto
        response = await client.get(f"/api/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product_id


class TestCustomersAPI:
    """Testes da API de clientes."""

    @pytest.mark.asyncio
    async def test_list_customers(self, client: AsyncClient):
        """Testa listagem de clientes."""
        response = await client.get("/api/customers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_customer(self, client: AsyncClient, sample_customer_data):
        """Testa criação de cliente."""
        response = await client.post("/api/customers", json=sample_customer_data)
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["phone"] == sample_customer_data["phone"]
        assert data["name"] == sample_customer_data["name"]


class TestOrdersAPI:
    """Testes da API de pedidos."""

    @pytest.mark.asyncio
    async def test_list_orders(self, client: AsyncClient):
        """Testa listagem de pedidos."""
        response = await client.get("/api/orders")
        assert response.status_code == 200
        data = response.json()
        # Resposta paginada
        assert "items" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_order_requires_auth(self, client: AsyncClient):
        """Testa que criar pedido requer autenticação."""
        response = await client.post("/api/orders", json={})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_order_with_auth(self, authenticated_client: AsyncClient, sample_customer_data):
        """Testa criação de pedido com autenticação."""
        # Primeiro criar cliente
        customer_response = await authenticated_client.post("/api/customers", json=sample_customer_data)
        assert customer_response.status_code in [200, 201]
        customer = customer_response.json()

        # Criar pedido
        order_data = {
            "customer_id": customer["id"],
            "items": [{"product_code": "P13", "quantity": 1}],
            "payment_method": "pix",
            "delivery_address": {
                "street": "Rua Teste",
                "number": "123",
                "bairro": "Centro",
                "city": "Curitiba",
                "state": "PR"
            }
        }
        response = await authenticated_client.post("/api/orders", json=order_data)
        # Pode falhar se produto P13 não existir, mas não deve ser 401
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_delete_order_requires_auth(self, client: AsyncClient):
        """Testa que deletar pedido requer autenticação."""
        import uuid
        response = await client.delete(f"/api/orders/{uuid.uuid4()}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_pending_orders(self, client: AsyncClient):
        """Testa listagem de pedidos pendentes."""
        response = await client.get("/api/orders/pending")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_today_orders(self, client: AsyncClient):
        """Testa listagem de pedidos do dia."""
        response = await client.get("/api/orders/today")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestWebhooksAPI:
    """Testes da API de webhooks."""

    @pytest.mark.asyncio
    async def test_webhooks_health(self, client: AsyncClient):
        """Testa saúde dos webhooks."""
        response = await client.get("/webhooks/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_waha_webhook_invalid_event(self, client: AsyncClient):
        """Testa webhook WAHA com evento desconhecido."""
        payload = {
            "event": "unknown_event",
            "session": "default",
            "payload": {}
        }
        response = await client.post("/webhooks/waha", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_waha_webhook_own_message(self, client: AsyncClient):
        """Testa webhook WAHA ignorando mensagem própria."""
        payload = {
            "event": "message",
            "session": "default",
            "payload": {
                "fromMe": True,
                "from": "5541999999999@c.us",
                "body": "teste"
            }
        }
        response = await client.post("/webhooks/waha", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "own_message"


class TestFlowTestAPI:
    """Testes da API de teste do flow."""

    @pytest.mark.asyncio
    async def test_list_flow_states(self, client: AsyncClient):
        """Testa listagem de estados do flow."""
        response = await client.get("/api/test/flow-states")
        assert response.status_code == 200
        data = response.json()
        assert "states" in data
        assert "start" in data["states"]
        assert "awaiting_product" in data["states"]

    @pytest.mark.asyncio
    async def test_simulate_message(self, client: AsyncClient):
        """Testa simulação de mensagem."""
        payload = {
            "phone": "5541888888888",
            "message": "oi"
        }
        response = await client.post("/api/test/simulate-message", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "responses" in data
        assert len(data["responses"]) > 0

    @pytest.mark.asyncio
    async def test_get_context(self, client: AsyncClient):
        """Testa obtenção de contexto."""
        # Primeiro simular uma mensagem para criar contexto
        await client.post("/api/test/simulate-message", json={
            "phone": "5541777777777",
            "message": "menu"
        })

        # Buscar contexto
        response = await client.get("/api/test/context/5541777777777")
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "5541777777777"
        assert "context" in data

    @pytest.mark.asyncio
    async def test_reset_context(self, client: AsyncClient):
        """Testa reset de contexto."""
        response = await client.delete("/api/test/context/5541666666666")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
