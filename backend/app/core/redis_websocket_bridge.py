"""
Redis WebSocket Bridge - Comunicação entre múltiplas instâncias do backend.

Permite escala horizontal: múltiplas instâncias do backend podem se comunicar
via Redis Pub/Sub, possibilitando uso de load balancer.

Arquitetura:
┌────────────┐       ┌────────────┐       ┌────────────┐
│ Backend 1  │       │ Backend 2  │       │ Backend 3  │
│ (instance) │       │ (instance) │       │ (instance) │
└─────┬──────┘       └─────┬──────┘       └─────┬──────┘
      │                    │                    │
      │    Redis Pub/Sub   │                    │
      └────────┬───────────┴────────────────────┘
               │
          ┌────▼─────┐
          │  Redis   │
          │ Channel  │
          └──────────┘

Quando um evento ocorre em uma instância, ele é publicado no Redis.
Todas as instâncias (incluindo a que publicou) recebem e fazem broadcast
apenas para seus clientes WebSocket conectados.
"""

import asyncio
import json
import logging
from typing import Optional, Callable
from datetime import datetime, timezone
import uuid

from app.database import redis_manager

logger = logging.getLogger(__name__)


class RedisWebSocketBridge:
    """
    Ponte entre Redis Pub/Sub e WebSocket para escala horizontal.
    """
    
    # Canal Redis para eventos WebSocket
    CHANNEL_NAME = "websocket:events"
    
    def __init__(self):
        self.instance_id = str(uuid.uuid4())[:8]  # ID único desta instância
        self.is_listening = False
        self.listener_task = None
        self.message_handlers = []
        
        logger.info(f"🔗 RedisWebSocketBridge inicializado (instance_id={self.instance_id})")
    
    async def start(self):
        """Inicia o listener do Redis Pub/Sub."""
        if self.is_listening:
            logger.warning("Redis listener já está rodando")
            return
        
        self.is_listening = True
        self.listener_task = asyncio.create_task(self._listen_loop())
        logger.info(f"✅ Redis WebSocket Bridge iniciado (instance={self.instance_id})")
    
    async def stop(self):
        """Para o listener do Redis Pub/Sub."""
        self.is_listening = False
        
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"🔌 Redis WebSocket Bridge parado (instance={self.instance_id})")
    
    def register_handler(self, handler: Callable):
        """
        Registra um handler para processar mensagens recebidas do Redis.
        
        Handler deve ser async function(event_type, data, source_instance_id)
        """
        self.message_handlers.append(handler)
    
    async def publish_event(self, event_type: str, data: dict):
        """
        Publica um evento no Redis para todas as instâncias.
        
        Args:
            event_type: Tipo do evento (ex: 'new_order', 'order_update')
            data: Dados do evento (será serializado para JSON)
        """
        try:
            message = {
                "instance_id": self.instance_id,
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            message_json = json.dumps(message, default=str)
            
            # Publicar no canal Redis
            await redis_manager.publish(self.CHANNEL_NAME, message_json)
            
            logger.debug(
                f"📤 Evento publicado: {event_type} "
                f"(instance={self.instance_id}, size={len(message_json)} bytes)"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao publicar evento no Redis: {e}")
    
    async def _listen_loop(self):
        """Loop principal que escuta mensagens do Redis."""
        logger.info(f"👂 Iniciando listener Redis (instance={self.instance_id})")
        
        try:
            # Criar subscriber
            pubsub = await redis_manager.subscribe(self.CHANNEL_NAME)
            
            if not pubsub:
                logger.error("❌ Falha ao criar subscriber Redis")
                return
            
            logger.info(f"✅ Subscribed to channel: {self.CHANNEL_NAME}")
            
            # Loop de escuta
            while self.is_listening:
                try:
                    # Aguardar mensagem (com timeout para permitir shutdown graceful)
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=1.0
                    )
                    
                    if message and message['type'] == 'message':
                        await self._process_message(message['data'])
                
                except asyncio.TimeoutError:
                    # Timeout normal, continuar loop
                    continue
                except Exception as e:
                    logger.error(f"❌ Erro no loop de escuta Redis: {e}")
                    await asyncio.sleep(1)  # Evitar loop rápido em caso de erro
            
        except Exception as e:
            logger.error(f"❌ Erro fatal no listener Redis: {e}")
        finally:
            logger.info(f"🔌 Listener Redis finalizado (instance={self.instance_id})")
    
    async def _process_message(self, message_data):
        """Processa uma mensagem recebida do Redis."""
        try:
            # Deserializar mensagem
            if isinstance(message_data, bytes):
                message_data = message_data.decode('utf-8')
            
            message = json.loads(message_data)
            
            source_instance = message.get("instance_id")
            event_type = message.get("event_type")
            data = message.get("data")
            
            # Log apenas se for de outra instância (reduz ruído)
            if source_instance != self.instance_id:
                logger.debug(
                    f"📥 Evento recebido de outra instância: {event_type} "
                    f"(from={source_instance[:8]})"
                )
            
            # Chamar todos os handlers registrados
            for handler in self.message_handlers:
                try:
                    await handler(event_type, data, source_instance)
                except Exception as e:
                    logger.error(f"❌ Erro no handler de mensagem: {e}")
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao decodificar mensagem Redis: {e}")
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem Redis: {e}")
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do bridge."""
        return {
            "instance_id": self.instance_id,
            "is_listening": self.is_listening,
            "num_handlers": len(self.message_handlers),
            "channel": self.CHANNEL_NAME,
        }


# Instância global
redis_ws_bridge = RedisWebSocketBridge()
