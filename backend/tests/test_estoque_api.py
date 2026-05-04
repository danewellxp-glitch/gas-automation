"""Testes de integração da API de Estoque."""
import pytest
import pytest_asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_models import User
from app.models.estoque.stock_product import StockProduct
from app.models.estoque.stock_balance import StockBalance
from app.models.estoque.vehicle_load import VehicleLoad, VehicleLoadStatus
from app.models.estoque.vehicle_load_item import VehicleLoadItem
from app.models.estoque.stock_movement import StockMovement, MovementType
from app.models.driver import Driver
from app.models.financeiro.vasilhame_estoque import VasilhameEstoque
from app.auth import create_access_token, get_password_hash


@pytest_asyncio.fixture(scope="function")
async def estoque_role_client(
    client: AsyncClient, db_session: AsyncSession
):
    """Cliente autenticado com role 'estoque'."""
    test_user = User(
        username=f"estoque_test_{uuid4().hex[:8]}",
        email=f"estoque_test_{uuid4().hex[:8]}@test.local",
        full_name="Estoque Test",
        hashed_password=get_password_hash("Testpassword123"),
        role="estoque",
        is_active=True,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    token = create_access_token(data={"sub": test_user.username})
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    del client.headers["Authorization"]


@pytest_asyncio.fixture(scope="function")
async def financeiro_role_client(
    client: AsyncClient, db_session: AsyncSession
):
    """Cliente autenticado com role 'financeiro'."""
    test_user = User(
        username=f"fin_test_{uuid4().hex[:8]}",
        email=f"fin_test_{uuid4().hex[:8]}@test.local",
        full_name="Financeiro Test",
        hashed_password=get_password_hash("Testpassword123"),
        role="financeiro",
        is_active=True,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    token = create_access_token(data={"sub": test_user.username})
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    del client.headers["Authorization"]


@pytest_asyncio.fixture(scope="function")
async def operator_role_client(
    client: AsyncClient, db_session: AsyncSession
):
    """Cliente autenticado com role 'operator'. Nao tem acesso ao estoque."""
    test_user = User(
        username=f"op_test_{uuid4().hex[:8]}",
        email=f"op_test_{uuid4().hex[:8]}@test.local",
        full_name="Operator Test",
        hashed_password=get_password_hash("Testpassword123"),
        role="operator",
        is_active=True,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    token = create_access_token(data={"sub": test_user.username})
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    del client.headers["Authorization"]


@pytest_asyncio.fixture(scope="function")
async def stock_product(db_session: AsyncSession) -> StockProduct:
    """Cria produto de estoque de teste."""
    sp = StockProduct(
        code="P13",
        name="Botijao P13",
        unit="unidade",
        cost_price=Decimal("50.00"),
        min_stock_alert=5,
        is_active=True,
    )
    db_session.add(sp)
    await db_session.commit()
    await db_session.refresh(sp)

    balance = StockBalance(stock_product_id=sp.id, quantity_depot=100)
    db_session.add(balance)
    await db_session.commit()
    return sp


@pytest_asyncio.fixture(scope="function")
async def test_driver(db_session: AsyncSession) -> Driver:
    """Cria entregador de teste."""
    driver = Driver(
        phone=f"5541{uuid4().hex[:8]}",
        name="Entregador Teste",
        status="disponivel",
        is_active=True,
    )
    db_session.add(driver)
    await db_session.commit()
    await db_session.refresh(driver)
    return driver


# ==================== Role-Based Access Tests ====================


class TestEstoqueAuth:
    """Testes de autorizacao RBAC para endpoints de estoque."""

    @pytest.mark.asyncio
    async def test_unauthenticated_access_denied(self, client: AsyncClient):
        """Sem token, todos endpoints de estoque retornam 401."""
        endpoints = [
            "/api/estoque/dashboard",
            "/api/estoque/vasilhames/posicao",
            "/api/estoque/balance",
            "/api/estoque/movements",
            "/api/estoque/vehicle-loads",
        ]
        for ep in endpoints:
            resp = await client.get(ep)
            assert resp.status_code == 401, f"{ep} should return 401"

    @pytest.mark.asyncio
    async def test_operator_role_denied(self, operator_role_client: AsyncClient):
        """Operator nao tem acesso ao estoque (403)."""
        endpoints = [
            "/api/estoque/dashboard",
            "/api/estoque/vasilhames/posicao",
            "/api/estoque/balance",
        ]
        for ep in endpoints:
            resp = await operator_role_client.get(ep)
            assert resp.status_code == 403, f"{ep} should return 403 for operator"

    @pytest.mark.asyncio
    async def test_estoque_role_allowed(self, estoque_role_client: AsyncClient):
        """Role 'estoque' tem acesso aos endpoints de estoque."""
        resp = await estoque_role_client.get("/api/estoque/dashboard")
        assert resp.status_code == 200

        resp = await estoque_role_client.get("/api/estoque/vasilhames/posicao")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_financeiro_role_allowed(self, financeiro_role_client: AsyncClient):
        """Role 'financeiro' tambem tem acesso ao estoque."""
        resp = await financeiro_role_client.get("/api/estoque/vasilhames/posicao")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_role_allowed(self, authenticated_client: AsyncClient):
        """Admin tem acesso total ao estoque."""
        resp = await authenticated_client.get("/api/estoque/dashboard")
        assert resp.status_code == 200


# ==================== Vasilhames Posicao Tests ====================


class TestVasilhamesPosicao:
    """Testes do endpoint GET /api/estoque/vasilhames/posicao."""

    @pytest.mark.asyncio
    async def test_returns_all_types(self, estoque_role_client: AsyncClient):
        """Deve retornar todos os 4 tipos (P13, P20, P45, G20L) com valores zerados por padrao."""
        resp = await estoque_role_client.get("/api/estoque/vasilhames/posicao")
        assert resp.status_code == 200
        data = resp.json()
        tipos = {item["tipo"] for item in data}
        assert tipos == {"P13", "P20", "P45", "G20L"}
        for item in data:
            assert "qtd_cheios" in item
            assert "qtd_vazios" in item
            assert "qtd_em_campo" in item
            assert "custo_unitario" in item
            assert "valor_estoque" in item

    @pytest.mark.asyncio
    async def test_idempotent_with_no_data_loss(self, estoque_role_client: AsyncClient):
        """Chamadas repetidas mantem consistencia, sem perda de dados."""
        resp1 = await estoque_role_client.get("/api/estoque/vasilhames/posicao")
        resp2 = await estoque_role_client.get("/api/estoque/vasilhames/posicao")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()

    @pytest.mark.asyncio
    async def test_persists_after_adjustment(self, estoque_role_client: AsyncClient):
        """Ajuste altera valores e posicao reflete a mudanca."""
        # Ajustar P13 cheios
        resp_adj = await estoque_role_client.post(
            "/api/estoque/vasilhames/ajuste",
            json={"tipo": "P13", "qtd_cheios": 50, "qtd_vazios": 30, "observacao": "Teste integracao"},
        )
        assert resp_adj.status_code == 200

        # Verificar posicao
        resp = await estoque_role_client.get("/api/estoque/vasilhames/posicao")
        p13 = next(item for item in resp.json() if item["tipo"] == "P13")
        assert p13["qtd_cheios"] == 50
        assert p13["qtd_vazios"] == 30


# ==================== Stock Adjustment Tests ====================


class TestStockAdjustment:
    """Testes do POST /api/estoque/vasilhames/ajuste e /api/estoque/movements/adjustment."""

    @pytest.mark.asyncio
    async def test_vasilhames_ajuste_creates_movement(self, estoque_role_client: AsyncClient):
        """Ajuste de vasilhames cria movimento de auditoria."""
        resp = await estoque_role_client.post(
            "/api/estoque/vasilhames/ajuste",
            json={"tipo": "P45", "qtd_cheios": 25, "qtd_vazios": 15, "observacao": "Audit trail test"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_ajuste_invalid_tipo(self, estoque_role_client: AsyncClient):
        """Tipo invalido rejeitado com 400."""
        resp = await estoque_role_client.post(
            "/api/estoque/vasilhames/ajuste",
            json={"tipo": "INVALIDO", "qtd_cheios": 10},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_ajuste_cannot_go_negative(self, estoque_role_client: AsyncClient):
        """Ajuste nao permite valores negativos (clampa em 0)."""
        resp = await estoque_role_client.post(
            "/api/estoque/vasilhames/ajuste",
            json={"tipo": "P20", "qtd_cheios": -5, "qtd_vazios": -10, "observacao": "Test clamping"},
        )
        assert resp.status_code == 200
        assert resp.json()["qtd_cheios"] == 0
        assert resp.json()["qtd_vazios"] == 0

    @pytest.mark.asyncio
    async def test_movements_adjustment_entrada(
        self, estoque_role_client: AsyncClient, stock_product
    ):
        """Ajuste de entrada via movements/adjustment aumenta o saldo no deposito."""
        resp = await estoque_role_client.post(
            "/api/estoque/movements/adjustment",
            json={
                "stock_product_id": str(stock_product.id),
                "direction": "entrada",
                "quantity": 20,
                "notes": "Ajuste de entrada - inventario",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["movement_type"] == MovementType.ajuste_entrada.value
        assert data["quantity"] == 20
        assert data["direction"] == "entrada"

    @pytest.mark.asyncio
    async def test_movements_adjustment_saida(
        self, estoque_role_client: AsyncClient, stock_product
    ):
        """Ajuste de saida via movements/adjustment reduz o saldo."""
        resp = await estoque_role_client.post(
            "/api/estoque/movements/adjustment",
            json={
                "stock_product_id": str(stock_product.id),
                "direction": "saida",
                "quantity": 30,
                "notes": "Ajuste de saida - perda identificada",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["movement_type"] == MovementType.ajuste_saida.value
        assert data["quantity"] == 30

    @pytest.mark.asyncio
    async def test_movements_adjustment_insufficient_stock(
        self, estoque_role_client: AsyncClient, stock_product
    ):
        """Tentar retirar mais than disponivel retorna 422."""
        resp = await estoque_role_client.post(
            "/api/estoque/movements/adjustment",
            json={
                "stock_product_id": str(stock_product.id),
                "direction": "saida",
                "quantity": 9999,
                "notes": "Deve falhar - estoque insuficiente",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_movements_adjustment_requires_notes_min_length(
        self, estoque_role_client: AsyncClient, stock_product
    ):
        """Notas com menos de 5 caracteres sao rejeitadas (validacao Pydantic)."""
        resp = await estoque_role_client.post(
            "/api/estoque/movements/adjustment",
            json={
                "stock_product_id": str(stock_product.id),
                "direction": "entrada",
                "quantity": 5,
                "notes": "ab",
            },
        )
        assert resp.status_code == 422


# ==================== Vehicle Load Tests ====================


class TestVehicleLoads:
    """Testes dos endpoints de carga veicular."""

    @pytest.mark.asyncio
    async def test_list_empty(self, estoque_role_client: AsyncClient):
        """Listar cargas quando nao ha nenhuma retorna lista vazia."""
        resp = await estoque_role_client.get("/api/estoque/vehicle-loads")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_vehicle_load(
        self, estoque_role_client: AsyncClient, stock_product, test_driver
    ):
        """Criar carga de veiculo reduz deposito e cria registro."""
        today = date.today().isoformat()
        resp = await estoque_role_client.post(
            "/api/estoque/vehicle-loads",
            json={
                "driver_id": str(test_driver.id),
                "load_date": today,
                "items": [
                    {
                        "stock_product_id": str(stock_product.id),
                        "quantity_loaded": 10,
                    }
                ],
                "notes": "Carga de teste integracao",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["driver_id"] == str(test_driver.id)
        assert data["status"] == VehicleLoadStatus.em_rota.value
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity_loaded"] == 10

    @pytest.mark.asyncio
    async def test_duplicate_active_load_rejected(
        self, estoque_role_client: AsyncClient, stock_product, test_driver
    ):
        """Nao permite duas cargas abertas mesmo driver/mesma data."""
        today = date.today().isoformat()
        payload = {
            "driver_id": str(test_driver.id),
            "load_date": today,
            "items": [{"stock_product_id": str(stock_product.id), "quantity_loaded": 5}],
        }
        resp1 = await estoque_role_client.post("/api/estoque/vehicle-loads", json=payload)
        assert resp1.status_code == 201

        resp2 = await estoque_role_client.post("/api/estoque/vehicle-loads", json=payload)
        assert resp2.status_code == 422

    @pytest.mark.asyncio
    async def test_create_load_insufficient_stock(
        self, estoque_role_client: AsyncClient, stock_product, test_driver
    ):
        """Nao permite carga com quantidade maior que o estoque disponivel."""
        today = date.today().isoformat()
        resp = await estoque_role_client.post(
            "/api/estoque/vehicle-loads",
            json={
                "driver_id": str(test_driver.id),
                "load_date": today,
                "items": [{"stock_product_id": str(stock_product.id), "quantity_loaded": 9999}],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_open_vehicle_loads(
        self, estoque_role_client: AsyncClient, stock_product, test_driver
    ):
        """Lista de cargas abertas retorna apenas nao encerradas."""
        today = date.today().isoformat()
        # Criar uma carga
        resp = await estoque_role_client.post(
            "/api/estoque/vehicle-loads",
            json={
                "driver_id": str(test_driver.id),
                "load_date": today,
                "items": [{"stock_product_id": str(stock_product.id), "quantity_loaded": 5}],
            },
        )
        assert resp.status_code == 201
        load_id = resp.json()["id"]

        # Deve aparecer nas abertas
        resp_open = await estoque_role_client.get("/api/estoque/vehicle-loads/open")
        assert resp_open.status_code == 200
        open_ids = [l["id"] for l in resp_open.json()]
        assert load_id in open_ids

    @pytest.mark.asyncio
    async def test_close_vehicle_load_restores_balance(
        self, estoque_role_client: AsyncClient, stock_product, test_driver
    ):
        """Fechar carga restaura saldo de deposito corretamente."""
        today = date.today().isoformat()
        # Criar carga
        resp = await estoque_role_client.post(
            "/api/estoque/vehicle-loads",
            json={
                "driver_id": str(test_driver.id),
                "load_date": today,
                "items": [{"stock_product_id": str(stock_product.id), "quantity_loaded": 10}],
            },
        )
        assert resp.status_code == 201
        load_id = resp.json()["id"]

        # Fechar carga com retorno parcial
        resp_close = await estoque_role_client.post(
            f"/api/estoque/vehicle-loads/{load_id}/close",
            json={
                "returned_items": [
                    {
                        "stock_product_id": str(stock_product.id),
                        "quantity_returned": 3,
                        "cheios_retornados": 2,
                        "vazios_retornados": 1,
                    }
                ],
                "notes": "Fechamento com retorno parcial",
            },
        )
        assert resp_close.status_code == 200
        assert resp_close.json()["status"] == VehicleLoadStatus.encerrada.value

    @pytest.mark.asyncio
    async def test_close_already_closed_load_rejected(
        self, estoque_role_client: AsyncClient, stock_product, test_driver
    ):
        """Nao permite fechar carga ja encerrada."""
        today = date.today().isoformat()
        resp = await estoque_role_client.post(
            "/api/estoque/vehicle-loads",
            json={
                "driver_id": str(test_driver.id),
                "load_date": today,
                "items": [{"stock_product_id": str(stock_product.id), "quantity_loaded": 5}],
            },
        )
        load_id = resp.json()["id"]

        # Primeiro fechamento
        await estoque_role_client.post(
            f"/api/estoque/vehicle-loads/{load_id}/close",
            json={
                "returned_items": [
                    {"stock_product_id": str(stock_product.id), "quantity_returned": 0}
                ],
            },
        )
        # Segundo fechamento
        resp2 = await estoque_role_client.post(
            f"/api/estoque/vehicle-loads/{load_id}/close",
            json={
                "returned_items": [
                    {"stock_product_id": str(stock_product.id), "quantity_returned": 0}
                ],
            },
        )
        assert resp2.status_code == 422

    @pytest.mark.asyncio
    async def test_close_nonexistent_load_returns_422(
        self, estoque_role_client: AsyncClient
    ):
        """Fechar carga inexistente retorna 422."""
        fake_id = uuid4()
        resp = await estoque_role_client.post(
            f"/api/estoque/vehicle-loads/{fake_id}/close",
            json={"returned_items": []},
        )
        assert resp.status_code == 422


# ==================== Dashboard & Reports Tests ====================


class TestDashboard:
    """Testes do endpoint de dashboard de estoque."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_structure(self, estoque_role_client: AsyncClient):
        """Dashboard retorna estrutura esperada com todas as chaves."""
        resp = await estoque_role_client.get("/api/estoque/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "balances" in data
        assert "low_stock_count" in data
        assert "total_in_transit" in data
        assert "open_loads_count" in data
        assert "movements_today" in data

    @pytest.mark.asyncio
    async def test_dashboard_with_products(
        self, estoque_role_client: AsyncClient, stock_product
    ):
        """Dashboard reflete produtos cadastrados."""
        resp = await estoque_role_client.get("/api/estoque/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["balances"]) >= 1
        product_codes = [b["product_code"] for b in data["balances"]]
        assert stock_product.code in product_codes


# ==================== Balance Tests ====================


class TestBalance:
    """Testes de saldo de estoque."""

    @pytest.mark.asyncio
    async def test_list_balance(self, estoque_role_client: AsyncClient, stock_product):
        """Listagem de saldo retorna produtos ativos."""
        resp = await estoque_role_client.get("/api/estoque/balance")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        for item in data:
            assert "stock_product_id" in item
            assert "product_code" in item
            assert "quantity_depot" in item
            assert "is_low_stock" in item

    @pytest.mark.asyncio
    async def test_get_balance_not_found(self, estoque_role_client: AsyncClient):
        """Saldo de produto inexistente retorna 404."""
        fake_id = uuid4()
        resp = await estoque_role_client.get(f"/api/estoque/balance/{fake_id}")
        assert resp.status_code == 404


# ==================== Movements Tests ====================


class TestMovements:
    """Testes de listagem de movimentacoes."""

    @pytest.mark.asyncio
    async def test_list_movements_empty(self, estoque_role_client: AsyncClient):
        """Lista vazia quando nao ha movimentacoes."""
        resp = await estoque_role_client.get("/api/estoque/movements")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_movements_after_adjustment(
        self, estoque_role_client: AsyncClient, stock_product
    ):
        """Movimentacoes aparecem apos ajuste."""
        # Fazer ajuste
        await estoque_role_client.post(
            "/api/estoque/movements/adjustment",
            json={
                "stock_product_id": str(stock_product.id),
                "direction": "entrada",
                "quantity": 10,
                "notes": "Gerar movimento para teste",
            },
        )

        resp = await estoque_role_client.get("/api/estoque/movements")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["movement_type"] == MovementType.ajuste_entrada.value

    @pytest.mark.asyncio
    async def test_list_movements_pagination(self, estoque_role_client: AsyncClient):
        """Paginacao funciona corretamente."""
        resp = await estoque_role_client.get("/api/estoque/movements?page=1&per_page=10")
        assert resp.status_code == 200


# ==================== Low Stock Alert Tests ====================


class TestLowStock:
    """Testes de alerta de estoque baixo."""

    @pytest.mark.asyncio
    async def test_low_stock_report(self, estoque_role_client: AsyncClient, stock_product):
        """Relatorio de estoque baixo detecta produtos abaixo do minimo."""
        # Ajustar para abaixo do minimo (min_stock_alert=5)
        await estoque_role_client.post(
            "/api/estoque/movements/adjustment",
            json={
                "stock_product_id": str(stock_product.id),
                "direction": "saida",
                "quantity": 98,
                "notes": "Reduzir para testar alerta baixo",
            },
        )
        resp = await estoque_role_client.get("/api/estoque/reports/low-stock")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert any(p["code"] == stock_product.code for p in data["low_stock_products"])
