"""
Configuração de conexões com banco de dados PostgreSQL e Redis.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, List

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ==================== SQLAlchemy (PostgreSQL) ====================

# Engine assíncrono
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Base para modelos
class Base(DeclarativeBase):
    """Classe base para todos os modelos SQLAlchemy."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para obter sessão do banco de dados.
    Uso: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Inicializa o banco de dados criando todas as tabelas.
    Usar apenas em desenvolvimento. Em produção, use Alembic.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Fecha conexões com o banco de dados."""
    await engine.dispose()


# ==================== Redis ====================

class RedisManager:
    """Gerenciador de conexão Redis."""

    def __init__(self):
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Estabelece conexão com Redis."""
        self._redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        """Fecha conexão com Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    @property
    def client(self) -> aioredis.Redis:
        """Retorna cliente Redis."""
        if not self._redis:
            raise RuntimeError("Redis não conectado. Chame connect() primeiro.")
        return self._redis

    # Métodos de conveniência para estado de conversa

    async def get_conversation_state(self, phone: str) -> dict | None:
        """Obtém estado da conversa de um cliente."""
        import json
        data = await self._redis.get(f"chat:{phone}")
        if data:
            return json.loads(data)
        return None

    async def set_conversation_state(
        self,
        phone: str,
        state: dict,
        ttl: int | None = None
    ) -> None:
        """Define estado da conversa de um cliente."""
        import json
        ttl = ttl or settings.redis_conversation_ttl
        await self._redis.set(
            f"chat:{phone}",
            json.dumps(state, ensure_ascii=False),
            ex=ttl
        )

    async def delete_conversation_state(self, phone: str) -> None:
        """Remove estado da conversa de um cliente."""
        await self._redis.delete(f"chat:{phone}")

    async def set_order_lock(self, order_id: str, ttl: int = 300) -> bool:
        """
        Define lock para evitar processamento duplicado de pedido.
        Retorna True se conseguiu o lock, False se já existe.
        """
        return await self._redis.set(
            f"order_lock:{order_id}",
            "processing",
            nx=True,
            ex=ttl
        )

    async def release_order_lock(self, order_id: str) -> None:
        """Remove lock de pedido."""
        await self._redis.delete(f"order_lock:{order_id}")

    async def increment_rate_limit(self, phone: str, window: int = 60) -> int:
        """
        Incrementa contador de rate limit.
        Retorna o número atual de requisições na janela.
        """
        key = f"rate:{phone}:{window}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, window)
        return count
    
    # ==================== Pub/Sub para WebSocket ====================
    
    async def publish(self, channel: str, message: str) -> int:
        """
        Publica mensagem em um canal Redis.
        Retorna o número de subscribers que receberam a mensagem.
        """
        if not self._redis:
            raise RuntimeError("Redis não conectado")
        return await self._redis.publish(channel, message)
    
    async def subscribe(self, channel: str):
        """
        Cria um subscriber para um canal Redis.
        Retorna um objeto PubSub que pode ser usado para receber mensagens.
        """
        if not self._redis:
            raise RuntimeError("Redis não conectado")
        
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


# Instância global do gerenciador Redis
redis_manager = RedisManager()


async def get_redis() -> aioredis.Redis:
    """
    Dependency para obter cliente Redis.
    Uso: redis: aioredis.Redis = Depends(get_redis)
    """
    return redis_manager.client


# ==================== Context Manager para Lifespan ====================

@asynccontextmanager
async def db_lifespan():
    """
    Context manager para gerenciar ciclo de vida das conexões.
    Usar no lifespan do FastAPI.
    """
    # Startup
    await redis_manager.connect()
    yield
    # Shutdown
    await redis_manager.disconnect()
    await close_db()
