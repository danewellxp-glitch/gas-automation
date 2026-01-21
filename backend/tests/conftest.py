"""
Configuração de testes pytest.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.database import Base, get_db, redis_manager
from app.config import settings


# Usar mesmo banco (em produção usaria banco de teste separado)
TEST_DATABASE_URL = settings.database_url

# Engine de teste
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Cria event loop para testes assíncronos."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Cria sessão de banco de dados para teste."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cria cliente HTTP de teste."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Conectar Redis para testes
    await redis_manager.connect()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await redis_manager.disconnect()
    app.dependency_overrides.clear()


@pytest.fixture
def sample_customer_data():
    """Dados de exemplo para cliente."""
    import uuid
    unique_phone = f"5541{str(uuid.uuid4().int)[:9]}"
    return {
        "phone": unique_phone,
        "name": "Cliente Teste",
        "email": f"teste_{unique_phone}@example.com",
    }


@pytest.fixture
def sample_product_data():
    """Dados de exemplo para produto."""
    import uuid
    return {
        "code": f"TEST{str(uuid.uuid4())[:4].upper()}",
        "name": "Botijão Teste",
        "price": 110.00,
        "weight_kg": 13.0,
        "description": "Botijão de teste",
    }


@pytest.fixture
def sample_order_data():
    """Dados de exemplo para pedido."""
    return {
        "customer_id": None,  # Será preenchido no teste
        "status": "pending",
        "total_amount": 220.00,
        "payment_method": "pix",
        "delivery_address": {
            "street": "Rua Teste",
            "number": "123",
            "neighborhood": "Centro",
            "city": "Curitiba",
        },
    }


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(client: AsyncClient, db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP autenticado para testes que requerem login."""
    from app.auth import create_access_token, get_password_hash
    from app.models.auth_models import User
    from datetime import timedelta

    # Criar usuário de teste
    test_user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        role="admin",
        is_active=True,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    # Criar token JWT
    access_token = create_access_token(
        data={"sub": test_user.username},
        expires_delta=timedelta(minutes=30)
    )

    # Adicionar header de autenticação ao cliente
    client.headers["Authorization"] = f"Bearer {access_token}"

    yield client

    # Limpar header após teste
    if "Authorization" in client.headers:
        del client.headers["Authorization"]


@pytest.fixture
def sample_order_items():
    """Items de exemplo para pedido."""
    return [
        {"product_code": "P13", "quantity": 2},
        {"product_code": "P20", "quantity": 1},
    ]
