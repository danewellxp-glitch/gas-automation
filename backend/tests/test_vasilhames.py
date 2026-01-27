"""
Testes para Vasilhames e Controle de Comodato.
"""

import pytest
from decimal import Decimal
from httpx import AsyncClient


class TestVasilhamesAPI:
    """Testes da API de Vasilhames (tipos)."""

    @pytest.mark.asyncio
    async def test_list_vasilhames(self, client: AsyncClient):
        """Testa listagem de vasilhames."""
        response = await client.get("/api/vasilhames")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_create_vasilhame(self, client: AsyncClient):
        """Testa criação de vasilhame."""
        data = {
            "codigo": "P13",
            "descricao": "Botijão 13kg",
            "peso_kg": 14.5,
            "valor_caucao": 150.00
        }
        response = await client.post("/api/vasilhames", json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["codigo"] == "P13"
        assert float(result["valor_caucao"]) == 150.00

    @pytest.mark.asyncio
    async def test_create_vasilhame_duplicate(self, client: AsyncClient):
        """Testa criação com código duplicado."""
        data = {
            "codigo": "P45DUP",
            "descricao": "Botijão 45kg",
            "peso_kg": 48.0,
            "valor_caucao": 300.00
        }
        # Primeiro
        await client.post("/api/vasilhames", json=data)
        # Segundo com mesmo código
        response = await client.post("/api/vasilhames", json=data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_vasilhame(self, client: AsyncClient):
        """Testa busca de vasilhame por ID."""
        # Criar
        data = {
            "codigo": "P20GET",
            "descricao": "Botijão 20kg",
            "peso_kg": 22.0,
            "valor_caucao": 200.00
        }
        create_response = await client.post("/api/vasilhames", json=data)
        vasilhame_id = create_response.json()["id"]

        # Buscar
        response = await client.get(f"/api/vasilhames/{vasilhame_id}")
        assert response.status_code == 200
        assert response.json()["codigo"] == "P20GET"

    @pytest.mark.asyncio
    async def test_update_vasilhame(self, client: AsyncClient):
        """Testa atualização de vasilhame."""
        # Criar
        data = {
            "codigo": "P13UPD",
            "descricao": "Original",
            "peso_kg": 14.5,
            "valor_caucao": 100.00
        }
        create_response = await client.post("/api/vasilhames", json=data)
        vasilhame_id = create_response.json()["id"]

        # Atualizar
        update_data = {"valor_caucao": 180.00, "descricao": "Atualizado"}
        response = await client.patch(f"/api/vasilhames/{vasilhame_id}", json=update_data)
        assert response.status_code == 200
        assert float(response.json()["valor_caucao"]) == 180.00
        assert response.json()["descricao"] == "Atualizado"

    @pytest.mark.asyncio
    async def test_delete_vasilhame(self, client: AsyncClient):
        """Testa desativação de vasilhame."""
        # Criar
        data = {
            "codigo": "P13DEL",
            "descricao": "Para deletar",
            "peso_kg": 14.5,
            "valor_caucao": 100.00
        }
        create_response = await client.post("/api/vasilhames", json=data)
        vasilhame_id = create_response.json()["id"]

        # Deletar
        response = await client.delete(f"/api/vasilhames/{vasilhame_id}")
        assert response.status_code == 200

        # Verificar desativado
        get_response = await client.get(f"/api/vasilhames/{vasilhame_id}")
        assert get_response.json()["ativo"] == False


class TestClienteVasilhameAPI:
    """Testes da API de Vasilhames por Cliente."""

    @pytest.mark.asyncio
    async def test_get_vasilhames_cliente_vazio(self, client: AsyncClient, sample_customer_data):
        """Testa busca de vasilhames de cliente sem vasilhames."""
        # Criar cliente
        customer_response = await client.post("/api/customers", json=sample_customer_data)
        customer_id = customer_response.json()["id"]

        # Buscar vasilhames
        response = await client.get(f"/api/vasilhames/cliente/{customer_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_vasilhames"] == 0
        assert data["itens"] == []

    @pytest.mark.asyncio
    async def test_add_vasilhame_cliente(self, client: AsyncClient, sample_customer_data):
        """Testa adicionar vasilhame a cliente."""
        # Criar cliente
        customer_response = await client.post("/api/customers", json=sample_customer_data)
        customer_id = customer_response.json()["id"]

        # Criar vasilhame
        vas_data = {
            "codigo": "P13ADD",
            "descricao": "Botijão teste",
            "peso_kg": 14.5,
            "valor_caucao": 150.00
        }
        vas_response = await client.post("/api/vasilhames", json=vas_data)
        vasilhame_id = vas_response.json()["id"]

        # Adicionar ao cliente
        add_data = {
            "customer_id": customer_id,
            "vasilhame_id": vasilhame_id,
            "quantidade": 2,
            "valor_caucao_pago": 300.00
        }
        response = await client.post("/api/vasilhames/cliente", json=add_data)
        assert response.status_code == 201
        assert response.json()["quantidade"] == 2

    @pytest.mark.asyncio
    async def test_registrar_venda(self, client: AsyncClient, sample_customer_data):
        """Testa registro de venda (cliente novo)."""
        # Criar cliente
        customer_response = await client.post("/api/customers", json=sample_customer_data)
        customer_id = customer_response.json()["id"]

        # Criar vasilhame
        vas_data = {
            "codigo": "P13VENDA",
            "descricao": "Botijão venda",
            "peso_kg": 14.5,
            "valor_caucao": 150.00
        }
        vas_response = await client.post("/api/vasilhames", json=vas_data)
        vasilhame_id = vas_response.json()["id"]

        # Registrar venda
        venda_data = {
            "customer_id": customer_id,
            "vasilhame_id": vasilhame_id,
            "quantidade": 1
        }
        response = await client.post("/api/vasilhames/venda", json=venda_data)
        assert response.status_code == 200
        assert response.json()["quantidade"] == 1
        assert float(response.json()["valor_caucao_pago"]) == 150.00

    @pytest.mark.asyncio
    async def test_registrar_devolucao(self, client: AsyncClient, sample_customer_data):
        """Testa registro de devolução."""
        # Criar cliente
        customer_response = await client.post("/api/customers", json=sample_customer_data)
        customer_id = customer_response.json()["id"]

        # Criar vasilhame
        vas_data = {
            "codigo": "P13DEV",
            "descricao": "Botijão devolução",
            "peso_kg": 14.5,
            "valor_caucao": 100.00
        }
        vas_response = await client.post("/api/vasilhames", json=vas_data)
        vasilhame_id = vas_response.json()["id"]

        # Registrar venda (2 unidades)
        venda_data = {
            "customer_id": customer_id,
            "vasilhame_id": vasilhame_id,
            "quantidade": 2
        }
        await client.post("/api/vasilhames/venda", json=venda_data)

        # Devolver 1
        devolucao_data = {
            "customer_id": customer_id,
            "vasilhame_id": vasilhame_id,
            "quantidade": 1,
            "devolver_caucao": True
        }
        response = await client.post("/api/vasilhames/devolucao", json=devolucao_data)
        assert response.status_code == 200
        assert response.json()["quantidade_devolvida"] == 1
        assert response.json()["quantidade_restante"] == 1
        assert response.json()["valor_caucao_devolvido"] == 100.00

    @pytest.mark.asyncio
    async def test_devolucao_quantidade_insuficiente(self, client: AsyncClient, sample_customer_data):
        """Testa devolução com quantidade maior que disponível."""
        # Criar cliente
        customer_response = await client.post("/api/customers", json=sample_customer_data)
        customer_id = customer_response.json()["id"]

        # Criar vasilhame
        vas_data = {
            "codigo": "P13INSUF",
            "descricao": "Botijão insuficiente",
            "peso_kg": 14.5,
            "valor_caucao": 100.00
        }
        vas_response = await client.post("/api/vasilhames", json=vas_data)
        vasilhame_id = vas_response.json()["id"]

        # Registrar venda (1 unidade)
        venda_data = {
            "customer_id": customer_id,
            "vasilhame_id": vasilhame_id,
            "quantidade": 1
        }
        await client.post("/api/vasilhames/venda", json=venda_data)

        # Tentar devolver 2
        devolucao_data = {
            "customer_id": customer_id,
            "vasilhame_id": vasilhame_id,
            "quantidade": 2,
            "devolver_caucao": True
        }
        response = await client.post("/api/vasilhames/devolucao", json=devolucao_data)
        assert response.status_code == 400


class TestRelatoriosVasilhames:
    """Testes dos relatórios de vasilhames."""

    @pytest.mark.asyncio
    async def test_relatorio_geral(self, client: AsyncClient):
        """Testa relatório geral de vasilhames."""
        response = await client.get("/api/vasilhames/relatorio/geral")
        assert response.status_code == 200
        data = response.json()
        assert "data_geracao" in data
        assert "total_vasilhames_em_comodato" in data
        assert "por_tipo" in data

    @pytest.mark.asyncio
    async def test_relatorio_clientes(self, client: AsyncClient):
        """Testa relatório de clientes com vasilhames."""
        response = await client.get("/api/vasilhames/relatorio/clientes-com-vasilhames")
        assert response.status_code == 200
        data = response.json()
        assert "data_geracao" in data
        assert "total_clientes" in data
        assert "clientes" in data
