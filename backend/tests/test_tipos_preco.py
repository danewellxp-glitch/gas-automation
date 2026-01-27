"""
Testes para Tipos de Preço e Preços por Modalidade.
"""

import pytest
from decimal import Decimal
from datetime import date
from httpx import AsyncClient


class TestTiposPrecoAPI:
    """Testes da API de Tipos de Preço."""

    @pytest.mark.asyncio
    async def test_list_tipos_preco(self, client: AsyncClient):
        """Testa listagem de tipos de preço."""
        response = await client.get("/api/tipos-preco")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_tipo_preco(self, client: AsyncClient):
        """Testa criação de tipo de preço."""
        tipo_data = {
            "codigo": "teste_tipo",
            "descricao": "Tipo de Teste",
            "percentual_desconto": 10.0
        }
        response = await client.post("/api/tipos-preco", json=tipo_data)
        assert response.status_code == 201
        data = response.json()
        assert data["codigo"] == "teste_tipo"
        assert data["descricao"] == "Tipo de Teste"
        assert float(data["percentual_desconto"]) == 10.0

    @pytest.mark.asyncio
    async def test_create_tipo_preco_duplicate(self, client: AsyncClient):
        """Testa criação de tipo de preço com código duplicado."""
        tipo_data = {
            "codigo": "duplicado",
            "descricao": "Primeiro",
            "percentual_desconto": 5.0
        }
        # Primeira criação
        response1 = await client.post("/api/tipos-preco", json=tipo_data)
        assert response1.status_code == 201

        # Segunda criação com mesmo código
        tipo_data["descricao"] = "Segundo"
        response2 = await client.post("/api/tipos-preco", json=tipo_data)
        assert response2.status_code == 400

    @pytest.mark.asyncio
    async def test_get_tipo_preco_by_id(self, client: AsyncClient):
        """Testa busca de tipo de preço por ID."""
        # Criar tipo
        tipo_data = {
            "codigo": "busca_id",
            "descricao": "Busca por ID",
            "percentual_desconto": 0
        }
        create_response = await client.post("/api/tipos-preco", json=tipo_data)
        assert create_response.status_code == 201
        tipo_id = create_response.json()["id"]

        # Buscar
        response = await client.get(f"/api/tipos-preco/{tipo_id}")
        assert response.status_code == 200
        assert response.json()["codigo"] == "busca_id"

    @pytest.mark.asyncio
    async def test_get_tipo_preco_by_codigo(self, client: AsyncClient):
        """Testa busca de tipo de preço por código."""
        # Criar tipo
        tipo_data = {
            "codigo": "busca_codigo",
            "descricao": "Busca por Código",
            "percentual_desconto": 0
        }
        await client.post("/api/tipos-preco", json=tipo_data)

        # Buscar
        response = await client.get("/api/tipos-preco/codigo/busca_codigo")
        assert response.status_code == 200
        assert response.json()["descricao"] == "Busca por Código"

    @pytest.mark.asyncio
    async def test_update_tipo_preco(self, client: AsyncClient):
        """Testa atualização de tipo de preço."""
        # Criar tipo
        tipo_data = {
            "codigo": "update_test",
            "descricao": "Original",
            "percentual_desconto": 5.0
        }
        create_response = await client.post("/api/tipos-preco", json=tipo_data)
        tipo_id = create_response.json()["id"]

        # Atualizar
        update_data = {
            "descricao": "Atualizado",
            "percentual_desconto": 15.0
        }
        response = await client.patch(f"/api/tipos-preco/{tipo_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["descricao"] == "Atualizado"
        assert float(response.json()["percentual_desconto"]) == 15.0

    @pytest.mark.asyncio
    async def test_delete_tipo_preco(self, client: AsyncClient):
        """Testa desativação de tipo de preço."""
        # Criar tipo
        tipo_data = {
            "codigo": "delete_test",
            "descricao": "Para Deletar",
            "percentual_desconto": 0
        }
        create_response = await client.post("/api/tipos-preco", json=tipo_data)
        tipo_id = create_response.json()["id"]

        # Deletar (soft delete)
        response = await client.delete(f"/api/tipos-preco/{tipo_id}")
        assert response.status_code == 200

        # Verificar que foi desativado
        get_response = await client.get(f"/api/tipos-preco/{tipo_id}")
        assert get_response.json()["ativo"] == False

    @pytest.mark.asyncio
    async def test_get_tipo_preco_not_found(self, client: AsyncClient):
        """Testa busca de tipo de preço inexistente."""
        import uuid
        response = await client.get(f"/api/tipos-preco/{uuid.uuid4()}")
        assert response.status_code == 404


class TestProdutoPrecoAPI:
    """Testes da API de Preços por Produto."""

    @pytest.mark.asyncio
    async def test_list_produto_precos(self, client: AsyncClient):
        """Testa listagem de preços de produtos."""
        response = await client.get("/api/tipos-preco/produtos/precos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_produto_preco(self, client: AsyncClient, sample_product_data):
        """Testa criação de preço específico para produto."""
        # Criar produto
        product_response = await client.post("/api/products", json=sample_product_data)
        assert product_response.status_code in [200, 201]
        produto_id = product_response.json()["id"]

        # Criar tipo de preço
        tipo_data = {
            "codigo": "preco_prod_test",
            "descricao": "Teste Preço Produto",
            "percentual_desconto": 10.0
        }
        tipo_response = await client.post("/api/tipos-preco", json=tipo_data)
        tipo_id = tipo_response.json()["id"]

        # Criar preço específico
        preco_data = {
            "produto_id": produto_id,
            "tipo_preco_id": tipo_id,
            "preco": 95.00,
            "vigencia_inicio": date.today().isoformat()
        }
        response = await client.post("/api/tipos-preco/produtos/precos", json=preco_data)
        assert response.status_code == 201
        assert float(response.json()["preco"]) == 95.00

    @pytest.mark.asyncio
    async def test_buscar_preco_produto_sem_tipo(self, client: AsyncClient, sample_product_data):
        """Testa busca de preço quando cliente não tem tipo (usa varejo)."""
        # Criar produto
        product_response = await client.post("/api/products", json=sample_product_data)
        produto_id = product_response.json()["id"]
        preco_padrao = product_response.json()["price"]

        # Buscar preço (sem tipo específico = varejo)
        response = await client.get(f"/api/tipos-preco/buscar-preco/{produto_id}?tipo_preco_codigo=varejo")
        assert response.status_code == 200
        data = response.json()
        assert data["tipo_preco"] == "varejo"
        # Preço deve ser igual ao padrão (0% desconto)
        assert float(data["preco"]) == float(preco_padrao)

    @pytest.mark.asyncio
    async def test_buscar_preco_produto_com_desconto(self, client: AsyncClient, sample_product_data):
        """Testa busca de preço com desconto padrão do tipo."""
        # Criar produto com preço 100
        sample_product_data["price"] = 100.00
        product_response = await client.post("/api/products", json=sample_product_data)
        produto_id = product_response.json()["id"]

        # Criar tipo com 20% desconto
        tipo_data = {
            "codigo": "desconto_20",
            "descricao": "20% Desconto",
            "percentual_desconto": 20.0
        }
        await client.post("/api/tipos-preco", json=tipo_data)

        # Buscar preço
        response = await client.get(f"/api/tipos-preco/buscar-preco/{produto_id}?tipo_preco_codigo=desconto_20")
        assert response.status_code == 200
        data = response.json()
        # Preço deve ser 80 (100 - 20%)
        assert float(data["preco"]) == 80.00
        assert data["fonte"] == "desconto_padrao"

    @pytest.mark.asyncio
    async def test_buscar_preco_produto_especifico(self, client: AsyncClient, sample_product_data):
        """Testa busca de preço específico cadastrado."""
        # Criar produto
        sample_product_data["price"] = 100.00
        product_response = await client.post("/api/products", json=sample_product_data)
        produto_id = product_response.json()["id"]

        # Criar tipo
        tipo_data = {
            "codigo": "preco_especifico",
            "descricao": "Preço Específico",
            "percentual_desconto": 10.0
        }
        tipo_response = await client.post("/api/tipos-preco", json=tipo_data)
        tipo_id = tipo_response.json()["id"]

        # Criar preço específico (75, diferente do desconto padrão que seria 90)
        preco_data = {
            "produto_id": produto_id,
            "tipo_preco_id": tipo_id,
            "preco": 75.00,
            "vigencia_inicio": date.today().isoformat()
        }
        await client.post("/api/tipos-preco/produtos/precos", json=preco_data)

        # Buscar preço
        response = await client.get(f"/api/tipos-preco/buscar-preco/{produto_id}?tipo_preco_codigo=preco_especifico")
        assert response.status_code == 200
        data = response.json()
        # Deve usar preço específico (75), não o desconto padrão (90)
        assert float(data["preco"]) == 75.00
        assert data["fonte"] == "preco_especifico"

    @pytest.mark.asyncio
    async def test_update_produto_preco(self, client: AsyncClient, sample_product_data):
        """Testa atualização de preço de produto."""
        # Criar produto
        product_response = await client.post("/api/products", json=sample_product_data)
        produto_id = product_response.json()["id"]

        # Criar tipo
        tipo_data = {
            "codigo": "update_preco",
            "descricao": "Update Preço",
            "percentual_desconto": 0
        }
        tipo_response = await client.post("/api/tipos-preco", json=tipo_data)
        tipo_id = tipo_response.json()["id"]

        # Criar preço
        preco_data = {
            "produto_id": produto_id,
            "tipo_preco_id": tipo_id,
            "preco": 100.00,
            "vigencia_inicio": date.today().isoformat()
        }
        create_response = await client.post("/api/tipos-preco/produtos/precos", json=preco_data)
        preco_id = create_response.json()["id"]

        # Atualizar
        update_data = {"preco": 85.00}
        response = await client.patch(f"/api/tipos-preco/produtos/precos/{preco_id}", json=update_data)
        assert response.status_code == 200
        assert float(response.json()["preco"]) == 85.00

    @pytest.mark.asyncio
    async def test_delete_produto_preco(self, client: AsyncClient, sample_product_data):
        """Testa remoção de preço de produto."""
        # Criar produto
        product_response = await client.post("/api/products", json=sample_product_data)
        produto_id = product_response.json()["id"]

        # Criar tipo
        tipo_data = {
            "codigo": "delete_preco",
            "descricao": "Delete Preço",
            "percentual_desconto": 0
        }
        tipo_response = await client.post("/api/tipos-preco", json=tipo_data)
        tipo_id = tipo_response.json()["id"]

        # Criar preço
        preco_data = {
            "produto_id": produto_id,
            "tipo_preco_id": tipo_id,
            "preco": 100.00,
            "vigencia_inicio": date.today().isoformat()
        }
        create_response = await client.post("/api/tipos-preco/produtos/precos", json=preco_data)
        preco_id = create_response.json()["id"]

        # Deletar
        response = await client.delete(f"/api/tipos-preco/produtos/precos/{preco_id}")
        assert response.status_code == 200

        # Verificar que foi removido
        list_response = await client.get(f"/api/tipos-preco/produtos/precos?produto_id={produto_id}&tipo_preco_id={tipo_id}")
        assert len(list_response.json()) == 0
