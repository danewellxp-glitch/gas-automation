"""
Flow Engine Factory - Inicialização do Flow Engine V2
Cria e configura instâncias do Flow Engine V2.

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md
"""

import logging
from typing import Optional
import redis.asyncio as redis

from app.core.flow_engine_v2 import FlowEngineV2
from app.core.handler_registry import get_handler_registry
from app.core.context_manager import ContextManager
from app.core.metrics_collector import get_metrics_collector
from app.core.flow_config import FEATURE_FLAGS, ROLLOUT_PERCENTAGE
from app.config import settings

logger = logging.getLogger(__name__)


class FlowEngineFactory:
    """
    Factory para criar instâncias do Flow Engine V2.
    
    Gerencia:
    - Criação de instâncias
    - Configuração de dependências
    - Rollout gradual
    - Feature flags
    """
    
    _instance: Optional[FlowEngineV2] = None
    _redis_client: Optional[redis.Redis] = None
    
    @classmethod
    async def create_flow_engine(cls) -> FlowEngineV2:
        """
        Cria e configura uma instância do Flow Engine V2.
        
        Returns:
            FlowEngineV2 configurado
        """
        logger.info("Criando Flow Engine V2...")
        
        # 1. Criar cliente Redis
        redis_client = await cls._create_redis_client()
        
        # 2. Criar Context Manager
        context_manager = ContextManager(redis_client=redis_client)
        
        # 3. Criar Handler Registry
        handler_registry = get_handler_registry()
        
        # 4. Criar Metrics Collector
        metrics_collector = get_metrics_collector()
        
        # 5. Criar Flow Engine
        flow_engine = FlowEngineV2(
            handler_registry=handler_registry,
            context_manager=context_manager,
            metrics_collector=metrics_collector,
        )
        
        logger.info("Flow Engine V2 criado com sucesso")
        
        return flow_engine
    
    @classmethod
    async def get_flow_engine(cls) -> FlowEngineV2:
        """
        Obtém instância singleton do Flow Engine V2.
        
        Returns:
            FlowEngineV2
        """
        if cls._instance is None:
            cls._instance = await cls.create_flow_engine()
        
        return cls._instance
    
    @classmethod
    async def _create_redis_client(cls) -> Optional[redis.Redis]:
        """
        Cria cliente Redis para cache de contextos.
        
        Returns:
            Cliente Redis ou None se não configurado
        """
        if cls._redis_client is not None:
            return cls._redis_client
        
        try:
            redis_url = getattr(settings, "redis_url", None) or getattr(settings, "REDIS_URL", None)
            
            if not redis_url:
                logger.warning("Redis não configurado, contextos não serão persistidos")
                return None
            
            client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            
            # Testar conexão
            await client.ping()
            
            cls._redis_client = client
            logger.info("Cliente Redis conectado")
            
            return client
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao Redis: {e}", exc_info=True)
            return None
    
    @classmethod
    async def close(cls):
        """Fecha conexões e libera recursos."""
        if cls._redis_client:
            await cls._redis_client.close()
            logger.info("Cliente Redis fechado")
    
    @classmethod
    def is_v2_enabled_for_user(cls, phone: str) -> bool:
        """
        Verifica se Flow Engine V2 está habilitado para um usuário.
        
        Implementa rollout gradual baseado em:
        - Feature flag global
        - Percentual de rollout
        - Hash do telefone
        
        Args:
            phone: Número de telefone
        
        Returns:
            True se V2 habilitado para este usuário
        """
        # Feature flag desabilitado
        if not FEATURE_FLAGS.get("flow_engine_v2_enabled", False):
            return False
        
        # Rollout 100%
        if ROLLOUT_PERCENTAGE >= 100:
            return True
        
        # Rollout 0%
        if ROLLOUT_PERCENTAGE <= 0:
            return False
        
        # Rollout gradual baseado em hash do telefone
        phone_hash = hash(phone) % 100
        
        return phone_hash < ROLLOUT_PERCENTAGE
    
    @classmethod
    def get_engine_version(cls, phone: str) -> str:
        """
        Retorna versão do engine para um usuário.
        
        Args:
            phone: Número de telefone
        
        Returns:
            "v2" ou "v1"
        """
        return "v2" if cls.is_v2_enabled_for_user(phone) else "v1"


# Funções de conveniência
async def get_flow_engine_v2() -> FlowEngineV2:
    """
    Obtém instância do Flow Engine V2.
    
    Returns:
        FlowEngineV2
    """
    return await FlowEngineFactory.get_flow_engine()


def is_v2_enabled(phone: str) -> bool:
    """
    Verifica se V2 está habilitado para um telefone.
    
    Args:
        phone: Número de telefone
    
    Returns:
        True se V2 habilitado
    """
    return FlowEngineFactory.is_v2_enabled_for_user(phone)


async def process_message_v2(phone: str, message: str) -> list:
    """
    Processa mensagem com Flow Engine V2.
    
    Args:
        phone: Número de telefone
        message: Texto da mensagem
    
    Returns:
        Lista de respostas
    """
    engine = await get_flow_engine_v2()
    return await engine.process_message(phone, message)
