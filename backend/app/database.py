"""
Configuração de conexões com banco de dados PostgreSQL e Redis.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional, Union
import uuid

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.models.base import Base


# ==================== SQLAlchemy (PostgreSQL) ====================

# Engine assíncrono
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        # Em debug/dev: desabilitar cache para evitar problemas com migrações
        # Em produção: habilitar cache para melhor performance (~25% throughput)
        "prepared_statement_cache_size": 0 if settings.debug else 256,
        "statement_cache_size": 0 if settings.debug else 1024,
    },
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


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
        self._redis: Optional[aioredis.Redis] = None
        self.instance_id: str = str(uuid.uuid4())[:8]  # ID único para métricas

    async def connect(self) -> None:
        """Estabelece conexão com Redis."""
        self._redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            socket_timeout=settings.redis_socket_timeout,
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

    async def get_conversation_state(self, phone: str) -> Optional[dict]:
        """Obtém estado da conversa de um cliente."""
        import json
        import logging
        logger = logging.getLogger(__name__)

        try:
            if not self._redis:
                logger.error(f"[REDIS] get_conversation_state: Redis não conectado!")
                return None

            key = f"chat:{phone}"
            data = await self._redis.get(key)

            if data:
                parsed = json.loads(data)
                logger.debug(f"[REDIS] GET {key} | state={parsed.get('state', 'N/A')}")
                return parsed
            else:
                logger.debug(f"[REDIS] GET {key} | Não encontrado (None)")
                return None

        except Exception as e:
            logger.error(f"[REDIS] ERRO em get_conversation_state({phone}): {e}", exc_info=True)
            return None

    async def set_conversation_state(
        self,
        phone: str,
        state: dict,
        ttl: Optional[int] = None
    ) -> None:
        """Define estado da conversa de um cliente."""
        import json
        import logging
        logger = logging.getLogger(__name__)

        try:
            if not self._redis:
                logger.error(f"[REDIS] set_conversation_state: Redis não conectado!")
                return

            ttl = ttl or settings.redis_conversation_ttl
            key = f"chat:{phone}"
            json_data = json.dumps(state, ensure_ascii=False)

            await self._redis.set(key, json_data, ex=ttl)
            logger.debug(f"[REDIS] SET {key} | state={state.get('state', 'N/A')} | TTL={ttl}s | size={len(json_data)}b")

        except Exception as e:
            logger.error(f"[REDIS] ERRO em set_conversation_state({phone}): {e}", exc_info=True)

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
    
    # ==================== Distributed Locks ====================

    async def acquire_phone_lock(
        self, phone: str, lock_id: str, ttl: int = 30
    ) -> bool:
        """
        Acquires a distributed lock for a phone number.
        Prevents concurrent message processing for the same conversation.
        Uses SET NX EX for atomicity.

        Returns True if lock acquired, False if contention.
        """
        if not self._redis:
            return True  # fail-open if Redis down
        key = f"lock:phone:{phone}"
        result = await self._redis.set(key, lock_id, nx=True, ex=ttl)
        return bool(result)

    async def release_phone_lock(self, phone: str, lock_id: str) -> bool:
        """
        Releases lock only if we still own it (Lua script for atomicity).
        Prevents releasing a lock acquired by another worker after TTL expiry.
        """
        if not self._redis:
            return True
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        key = f"lock:phone:{phone}"
        result = await self._redis.eval(lua_script, 1, key, lock_id)
        return bool(result)

    # ==================== Deduplicação de mensagens ====================

    # ==================== Redis Streams ====================

    async def add_message_to_stream(
        self, message_data: dict, original_chat_id: Optional[str] = None, trace_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Adiciona mensagem ao Redis Stream para processamento distribuído.
        
        Args:
            message_data: Dados da mensagem (dict serializável)
            original_chat_id: Chat ID original do WAHA (pode ser @lid)
            
        Returns:
            Message ID do stream ou None se falhar
        """
        import json
        import time
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            stream_data = {
                "message": json.dumps(message_data),
                "original_chat_id": original_chat_id or "",
                "timestamp": str(time.time()),
            }
            # Incluir trace_id se fornecido
            if trace_id:
                stream_data["trace_id"] = trace_id
            
            # Usar cliente Redis direto para streams (precisa de bytes)
            import redis.asyncio as redis_streams
            redis_url = settings.redis_url
            stream_client = redis_streams.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False,  # Streams precisam de bytes
            )
            
            message_id = await stream_client.xadd(
                "stream:messages",
                stream_data,
                maxlen=10000,  # Manter apenas últimos 10k mensagens
            )
            
            await stream_client.close()
            
            message_id_str = message_id.decode() if isinstance(message_id, bytes) else message_id
            logger.debug(f"[RedisStream] Mensagem adicionada ao stream: {message_id_str}")
            
            # Métricas
            try:
                from app.metrics import stream_messages_added_total
                stream_messages_added_total.labels(
                    stream="stream:messages",
                    instance_id=getattr(self, 'instance_id', 'unknown')
                ).inc()
            except Exception:
                pass  # Métricas opcionais
            
            return message_id_str
            
        except Exception as e:
            logger.error(f"[RedisStream] Erro ao adicionar mensagem ao stream: {e}")
            return None

    async def check_message_processed(self, message_id: str) -> bool:
        """
        Verifica se uma mensagem já foi processada (deduplicação atômica).

        Usa SET NX EX para atomicamente verificar e marcar como processada.
        Retorna True se a mensagem JÁ FOI processada (duplicada).
        Retorna False se é uma mensagem nova (e marca como processada).
        """
        if not message_id:
            return False
        key = f"msg_dedup:{message_id}"
        was_set = await self._redis.set(key, "1", nx=True, ex=3600)
        return not was_set  # was_set=None significa que a chave já existia

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
