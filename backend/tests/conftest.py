"""
Configuração de testes pytest.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from sqlmodel import SQLModel

from app.main import app
from app.models.base import Base
from app.database import get_db, redis_manager
from app.config import settings

# Importar modelos para registrar nas metadatas (sem sobrescrever `app`)
from app.models import auth_models as _auth_models  # noqa: F401
from app.models import order as _order, delivery as _delivery  # noqa: F401
from app.models import driver as _driver, customer as _customer  # noqa: F401
from app.models import product as _product, conversation_snapshot as _snapshot  # noqa: F401

# Mesclar tabelas SQLModel na metadata do Base (uma vez, em import time)
# Necessário para resolver cross-FK: orders.approved_by → users.id
for _tname, _table in list(SQLModel.metadata.tables.items()):
    if _tname not in Base.metadata.tables:
        _table.to_metadata(Base.metadata)


def _derive_test_database_url(url: str) -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    base, sep, tail = url.rpartition("/")
    if sep and tail and "?" not in tail:
        if tail.endswith("_test"):
            return url
        return f"{base}/{tail}_test"
    return url


TEST_DATABASE_URL = _derive_test_database_url(os.getenv("DATABASE_URL") or settings.database_url)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

_POSTGRES_CHECKED = False
_POSTGRES_AVAILABLE = False
_POSTGRES_SKIP_REASON = ""

_REDIS_CHECKED = False
_REDIS_AVAILABLE = False
_REDIS_SKIP_REASON = ""

_TABLES_CREATED = False


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def _ensure_tables():
    global _POSTGRES_CHECKED, _POSTGRES_AVAILABLE, _POSTGRES_SKIP_REASON, _TABLES_CREATED

    if _POSTGRES_CHECKED and not _POSTGRES_AVAILABLE:
        pytest.skip(_POSTGRES_SKIP_REASON)

    if not _POSTGRES_CHECKED:
        try:
            async with test_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            _POSTGRES_AVAILABLE = True
        except Exception as e:
            _POSTGRES_AVAILABLE = False
            _POSTGRES_SKIP_REASON = (
                f"PostgreSQL não disponível para testes ({TEST_DATABASE_URL}). "
                f"Erro: {type(e).__name__}: {e}"
            )
            _POSTGRES_CHECKED = True
            pytest.skip(_POSTGRES_SKIP_REASON)
        finally:
            _POSTGRES_CHECKED = True

    if not _TABLES_CREATED:
        async with test_engine.begin() as conn:
            await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1000;"))
            await conn.run_sync(Base.metadata.create_all)
        _TABLES_CREATED = True


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Sessão de banco de dados para teste."""
    await _ensure_tables()

    async with TestSessionLocal() as session:
        yield session
        # Limpar dados após cada teste (truncate todas as tabelas)
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
        await session.commit()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cria cliente HTTP de teste."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    global _REDIS_CHECKED, _REDIS_AVAILABLE, _REDIS_SKIP_REASON
    if _REDIS_CHECKED and not _REDIS_AVAILABLE:
        pytest.skip(_REDIS_SKIP_REASON)

    if not _REDIS_CHECKED:
        try:
            await redis_manager.connect()
            _REDIS_AVAILABLE = True
        except Exception as e:
            _REDIS_AVAILABLE = False
            _REDIS_SKIP_REASON = (
                f"Redis não disponível para testes ({settings.redis_url}). "
                f"Erro: {type(e).__name__}: {e}"
            )
            _REDIS_CHECKED = True
            pytest.skip(_REDIS_SKIP_REASON)
        finally:
            _REDIS_CHECKED = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_customer_data():
    import uuid
    unique_phone = f"5541{str(uuid.uuid4().int)[:9]}"
    return {
        "phone": unique_phone,
        "name": "Cliente Teste",
        "email": f"teste_{unique_phone}@example.com",
    }


@pytest.fixture
def sample_product_data():
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
    return {
        "customer_id": None,
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

    test_user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("Testpassword123"),
        role="admin",
        is_active=True,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    access_token = create_access_token(
        data={"sub": test_user.username},
        expires_delta=timedelta(minutes=30)
    )

    client.headers["Authorization"] = f"Bearer {access_token}"
    yield client

    if "Authorization" in client.headers:
        del client.headers["Authorization"]


@pytest.fixture
def sample_order_items():
    return [
        {"product_code": "P13", "quantity": 2},
        {"product_code": "P20", "quantity": 1},
    ]
