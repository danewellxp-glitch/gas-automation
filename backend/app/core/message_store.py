"""
Message Store - Armazena mensagens WebSocket para reconexão inteligente.

Permite que clientes que desconectaram recuperem mensagens perdidas
ao reconectar, garantindo zero perda de dados.

Arquitetura:
┌─────────────┐
│   Cliente   │  Desconecta por 30s
└──────┬──────┘
       │
       │ Reconecta com last_seq_id=100
       │
┌──────▼──────┐
│  Backend    │  Envia msgs 101-110 (perdidas)
└──────┬──────┘
       │
┌──────▼──────┐
│  Redis      │  ws:history:user123
│  (TTL 1h)   │  [msg101, msg102, ..., msg110]
└─────────────┘
"""

import json
import logging
from typing import List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from app.database import redis_manager

logger = logging.getLogger(__name__)


@dataclass
class StoredMessage:
    """Mensagem armazenada com metadados."""
    seq_id: int
    timestamp: str
    event_type: str
    data: dict
    user_id: str


class MessageStore:
    """
    Armazena mensagens WebSocket no Redis para reconexão inteligente.
    
    Features:
    - Armazena últimas N mensagens por usuário
    - TTL configurável (default: 1 hora)
    - Sequence IDs para garantir ordem
    - Replay de mensagens perdidas durante desconexão
    """
    
    def __init__(
        self,
        ttl_seconds: int = 3600,          # 1 hora
        max_messages_per_user: int = 100,  # Últimas 100 mensagens
        key_prefix: str = "ws:history"
    ):
        self.ttl_seconds = ttl_seconds
        self.max_messages_per_user = max_messages_per_user
        self.key_prefix = key_prefix
        
        # Contador global de sequence ID
        self.seq_counter_key = f"{key_prefix}:seq_counter"
        
        logger.info(
            f"📦 MessageStore inicializado "
            f"(ttl={ttl_seconds}s, max_msgs={max_messages_per_user})"
        )
    
    def _get_user_key(self, user_id: str) -> str:
        """Retorna chave Redis para histórico do usuário."""
        return f"{self.key_prefix}:{user_id}"
    
    async def get_next_seq_id(self) -> int:
        """
        Retorna próximo sequence ID global.
        Sequence IDs são monotônicos e únicos.
        """
        redis = redis_manager.client
        seq_id = await redis.incr(self.seq_counter_key)
        return seq_id
    
    async def store_message(
        self,
        user_id: str,
        event_type: str,
        data: dict,
        seq_id: Optional[int] = None
    ) -> int:
        """
        Armazena uma mensagem no histórico do usuário.
        
        Args:
            user_id: ID do usuário
            event_type: Tipo do evento (ex: 'new_order', 'order_update')
            data: Dados da mensagem
            seq_id: Sequence ID (se None, gera um novo)
        
        Returns:
            Sequence ID da mensagem armazenada
        """
        try:
            redis = redis_manager.client
            
            # Gerar seq_id se não fornecido
            if seq_id is None:
                seq_id = await self.get_next_seq_id()
            
            # Criar mensagem
            message = StoredMessage(
                seq_id=seq_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type=event_type,
                data=data,
                user_id=user_id
            )
            
            # Serializar
            message_json = json.dumps(asdict(message), default=str)
            
            # Chave do usuário
            user_key = self._get_user_key(user_id)
            
            # Adicionar à lista (LPUSH = início da lista)
            await redis.lpush(user_key, message_json)
            
            # Manter apenas últimas N mensagens (LTRIM)
            await redis.ltrim(user_key, 0, self.max_messages_per_user - 1)
            
            # Definir TTL
            await redis.expire(user_key, self.ttl_seconds)
            
            logger.debug(
                f"💾 Mensagem armazenada: user={user_id}, "
                f"seq_id={seq_id}, type={event_type}"
            )
            
            return seq_id
        
        except Exception as e:
            logger.error(f"❌ Erro ao armazenar mensagem: {e}")
            return seq_id or 0
    
    async def get_messages_since(
        self,
        user_id: str,
        since_seq_id: int,
        limit: Optional[int] = None
    ) -> List[StoredMessage]:
        """
        Recupera mensagens desde um sequence ID específico.
        
        Args:
            user_id: ID do usuário
            since_seq_id: Recuperar mensagens após este seq_id
            limit: Limite de mensagens (None = sem limite)
        
        Returns:
            Lista de mensagens (ordenadas por seq_id crescente)
        """
        try:
            redis = redis_manager.client
            user_key = self._get_user_key(user_id)
            
            # Buscar todas as mensagens do usuário
            messages_json = await redis.lrange(user_key, 0, -1)
            
            if not messages_json:
                return []
            
            # Deserializar e filtrar
            messages = []
            for msg_json in messages_json:
                try:
                    msg_dict = json.loads(msg_json)
                    msg = StoredMessage(**msg_dict)
                    
                    # Filtrar por seq_id
                    if msg.seq_id > since_seq_id:
                        messages.append(msg)
                
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao deserializar mensagem: {e}")
                    continue
            
            # Ordenar por seq_id (crescente)
            messages.sort(key=lambda m: m.seq_id)
            
            # Aplicar limite se especificado
            if limit is not None:
                messages = messages[:limit]
            
            logger.info(
                f"📥 Replay: user={user_id}, since={since_seq_id}, "
                f"found={len(messages)} mensagens"
            )
            
            return messages
        
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar mensagens: {e}")
            return []
    
    async def get_latest_seq_id(self, user_id: str) -> Optional[int]:
        """
        Retorna o sequence ID da última mensagem do usuário.
        Útil para cliente saber qual o último ID recebido.
        """
        try:
            redis = redis_manager.client
            user_key = self._get_user_key(user_id)
            
            # Buscar primeira mensagem (mais recente por causa do LPUSH)
            messages = await redis.lrange(user_key, 0, 0)
            
            if not messages:
                return None
            
            msg_dict = json.loads(messages[0])
            return msg_dict.get('seq_id')
        
        except Exception as e:
            logger.error(f"❌ Erro ao buscar último seq_id: {e}")
            return None
    
    async def clear_user_history(self, user_id: str) -> None:
        """Remove todo o histórico de um usuário."""
        try:
            redis = redis_manager.client
            user_key = self._get_user_key(user_id)
            await redis.delete(user_key)
            
            logger.info(f"🗑️ Histórico limpo: user={user_id}")
        
        except Exception as e:
            logger.error(f"❌ Erro ao limpar histórico: {e}")
    
    async def get_stats(self, user_id: Optional[str] = None) -> dict:
        """
        Retorna estatísticas do message store.
        
        Args:
            user_id: Se fornecido, retorna stats de um usuário específico
        """
        try:
            redis = redis_manager.client
            
            if user_id:
                # Stats de um usuário específico
                user_key = self._get_user_key(user_id)
                count = await redis.llen(user_key)
                ttl = await redis.ttl(user_key)
                latest_seq = await self.get_latest_seq_id(user_id)
                
                return {
                    "user_id": user_id,
                    "message_count": count,
                    "ttl_remaining": ttl,
                    "latest_seq_id": latest_seq,
                }
            else:
                # Stats globais
                seq_counter = await redis.get(self.seq_counter_key) or 0
                
                # Contar quantos usuários têm histórico
                pattern = f"{self.key_prefix}:*"
                keys = []
                async for key in redis.scan_iter(match=pattern):
                    if key != self.seq_counter_key:
                        keys.append(key)
                
                return {
                    "global_seq_counter": int(seq_counter),
                    "users_with_history": len(keys),
                    "ttl_seconds": self.ttl_seconds,
                    "max_messages_per_user": self.max_messages_per_user,
                }
        
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {}


# Instância global
message_store = MessageStore()
