"""
Testes de Integração: Preços por Modalidade + Pedidos.
Verifica que o preço correto é aplicado no pedido baseado no tipo do cliente.
"""

import pytest
from decimal import Decimal
from datetime import date
from httpx import AsyncClient


class TestPrecoNoPedido:
    """Testes de integração de preços no pedido."""

    @pytest.mark.asyncio
    async def test_pedido_cliente_sem_tipo_usa_preco_varejo(
        self, authenticated_client: AsyncClient, sample_customer_data
    ):
        """
        Cliente sem tipo_preco_id deve usar preço padrão (varejo).
        """
        import uuid

        # Criar produto com preço 100
        product_data = {
            "code": f"INT{str(uuid.uuid4())[:3].upper()}",
            "name": "Produto Integração",
            "price": 100.00,
            "weight_kg": 13.0
        }
        product_response = await authenticated_client.post("/api/products", json=product_data)
        assert product_response.status_code in [200, 201]
        product_code = product_response.json()["code"]

        # Criar cliente SEM tipo_preco_id
        customer_response = await authenticated_client.post("/api/customers", json=sample_customer_data)
        assert customer_response.status_code in [200, 201]
        customer_id = customer_response.json()["id"]

        # Criar pedido
        order_data = {
            "customer_id": customer_id,
            "items": [{"product_code": product_code, "quantity": 2}],
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

        # Total deve ser 200 (100 * 2)
        assert float(data["total_amount"]) == 200.00

        # Verificar item
        assert len(data["items"]) == 1
        assert float(data["items"][0]["unit_price"]) == 100.00
        assert float(data["items"][0]["subtotal"]) == 200.00

    @pytest.mark.asyncio
    async def test_pedido_cliente_com_tipo_atacado(
        self, authenticated_client: AsyncClient
    ):
        """
        Cliente com tipo_preco atacado deve receber desconto.
        """
        import uuid

        # Criar tipo de preço atacado com 10% desconto
        tipo_data = {
            "codigo": f"atacado_{uuid.uuid4().hex[:6]}",
            "descricao": "Atacado Teste",
            "percentual_desconto": 10.0
        }
        tipo_response = await authenticated_client.post("/api/tipos-preco", json=tipo_data)
        assert tipo_response.status_code == 201
        tipo_id = tipo_response.json()["id"]

        # Criar cliente COM tipo_preco_id
        unique_phone = f"5541{str(uuid.uuid4().int)[:9]}"
        customer_data = {
            "phone": unique_phone,
            "name": "Cliente Atacado",
            "tipo_preco_id": tipo_id
        }
        customer_response = await authenticated_client.post("/api/customers", json=customer_data)
        assert customer_response.status_code in [200, 201]
        customer_id = customer_response.json()["id"]

        # Criar produto com preço 100
        product_data = {
            "code": f"ATA{str(uuid.uuid4())[:3].upper()}",
            "name": "Produto Atacado",
            "price": 100.00,
            "weight_kg": 13.0
        }
        product_response = await authenticated_client.post("/api/products", json=product_data)
        product_code = product_response.json()["code"]

        # Criar pedido
        order_data = {
            "customer_id": customer_id,
            "items": [{"product_code": product_code, "quantity": 1}],
            "payment_method": "pix",
            "delivery_address": {
                "street": "Rua Atacado",
                "number": "100",
                "bairro": "Centro",
                "city": "Curitiba",
                "state": "PR"
            }
        }
        response = await authenticated_client.post("/api/orders", json=order_data)
        assert response.status_code == 201
        data = response.json()

        # Total deve ser 90 (100 - 10%)
        assert float(data["total_amount"]) == 90.00
        assert float(data["items"][0]["unit_price"]) == 90.00

    @pytest.mark.asyncio
    async def test_pedido_cliente_com_preco_especifico(
        self, authenticated_client: AsyncClient
    ):
        """
        Cliente com preço específico cadastrado deve usar esse preço.
        """
        import uuid

        # Criar tipo de preço com 5% desconto padrão
        tipo_data = {
            "codigo": f"especifico_{uuid.uuid4().hex[:6]}",
            "descricao": "Preço Específico Teste",
            "percentual_desconto": 5.0
        }
        tipo_response = await authenticated_client.post("/api/tipos-preco", json=tipo_data)
        tipo_id = tipo_response.json()["id"]

        # Criar produto com preço 100
        product_data = {
            "code": f"ESP{str(uuid.uuid4())[:3].upper()}",
            "name": "Produto Específico",
            "price": 100.00,
            "weight_kg": 13.0
        }
        product_response = await authenticated_client.post("/api/products", json=product_data)
        produto_id = product_response.json()["id"]
        product_code = product_response.json()["code"]

        # Criar preço específico de 75 (menor que desconto padrão de 95)
        preco_data = {
            "produto_id": produto_id,
            "tipo_preco_id": tipo_id,
            "preco": 75.00,
            "vigencia_inicio": date.today().isoformat()
        }
        await authenticated_client.post("/api/tipos-preco/produtos/precos", json=preco_data)

        # Criar cliente COM tipo_preco_id
        unique_phone = f"5541{str(uuid.uuid4().int)[:9]}"
        customer_data = {
            "phone": unique_phone,
            "name": "Cliente Específico",
            "tipo_preco_id": tipo_id
        }
        customer_response = await authenticated_client.post("/api/customers", json=customer_data)
        customer_id = customer_response.json()["id"]

        # Criar pedido
        order_data = {
            "customer_id": customer_id,
            "items": [{"product_code": product_code, "quantity": 2}],
            "payment_method": "dinheiro",
            "delivery_address": {
                "street": "Rua Específica",
                "number": "75",
                "bairro": "Centro",
                "city": "Curitiba",
                "state": "PR"
            }
        }
        response = await authenticated_client.post("/api/orders", json=order_data)
        assert response.status_code == 201
        data = response.json()

        # Total deve ser 150 (75 * 2), não 190 (95 * 2)
        assert float(data["total_amount"]) == 150.00
        assert float(data["items"][0]["unit_price"]) == 75.00

    @pytest.mark.asyncio
    async def test_pedido_multiplos_itens_mesmo_preco(
        self, authenticated_client: AsyncClient
    ):
        """
        Pedido com múltiplos itens deve aplicar mesmo tipo de preço.
        """
        import uuid

        # Criar tipo com 20% desconto
        tipo_data = {
            "codigo": f"multi_{uuid.uuid4().hex[:6]}",
            "descricao": "Multi Items",
            "percentual_desconto": 20.0
        }
        tipo_response = await authenticated_client.post("/api/tipos-preco", json=tipo_data)
        tipo_id = tipo_response.json()["id"]

        # Criar 2 produtos
        products = []
        for i in range(2):
            product_data = {
                "code": f"M{i}{str(uuid.uuid4())[:2].upper()}",
                "name": f"Produto Multi {i}",
                "price": 100.00,
                "weight_kg": 13.0
            }
            product_response = await authenticated_client.post("/api/products", json=product_data)
            products.append(product_response.json()["code"])

        # Criar cliente com tipo
        unique_phone = f"5541{str(uuid.uuid4().int)[:9]}"
        customer_data = {
            "phone": unique_phone,
            "name": "Cliente Multi",
            "tipo_preco_id": tipo_id
        }
        customer_response = await authenticated_client.post("/api/customers", json=customer_data)
        customer_id = customer_response.json()["id"]

        # Criar pedido com 2 produtos
        order_data = {
            "customer_id": customer_id,
            "items": [
                {"product_code": products[0], "quantity": 1},
                {"product_code": products[1], "quantity": 2}
            ],
            "payment_method": "pix",
            "delivery_address": {
                "street": "Rua Multi",
                "number": "200",
                "bairro": "Centro",
                "city": "Curitiba",
                "state": "PR"
            }
        }
        response = await authenticated_client.post("/api/orders", json=order_data)
        assert response.status_code == 201
        data = response.json()

        # Total: 80 (1 * 80) + 160 (2 * 80) = 240
        assert float(data["total_amount"]) == 240.00

        # Cada item deve ter preço unitário de 80
        for item in data["items"]:
            assert float(item["unit_price"]) == 80.00
