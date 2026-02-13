"""
Métricas Prometheus customizadas para WebSocket e sistema.

Coleta métricas de:
- Conexões WebSocket ativas
- Mensagens enviadas/recebidas
- Latência de broadcasts
- Redis Pub/Sub
- Event batching
- Erros e problemas

Métricas são expostas no endpoint /metrics para coleta pelo Prometheus.
"""

import logging
import time
from functools import wraps
from typing import Callable

from prometheus_client import Counter, Gauge, Histogram, Info

logger = logging.getLogger(__name__)

# ==================== Métricas WebSocket ====================

# Conexões ativas
websocket_connections_total = Gauge(
    'websocket_connections_total',
    'Total de conexões WebSocket ativas',
    ['role', 'instance_id']
)

websocket_users_total = Gauge(
    'websocket_users_total',
    'Total de usuários únicos conectados',
    ['instance_id']
)

# Mensagens
websocket_messages_sent_total = Counter(
    'websocket_messages_sent_total',
    'Total de mensagens WebSocket enviadas',
    ['type', 'instance_id']
)

websocket_messages_received_total = Counter(
    'websocket_messages_received_total',
    'Total de mensagens WebSocket recebidas',
    ['type', 'instance_id']
)

websocket_messages_stored_total = Counter(
    'websocket_messages_stored_total',
    'Total de mensagens armazenadas no MessageStore',
    ['instance_id']
)

# Broadcast
websocket_broadcast_duration_seconds = Histogram(
    'websocket_broadcast_duration_seconds',
    'Tempo de duração de broadcasts WebSocket',
    ['filter_type', 'instance_id'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

websocket_broadcast_recipients = Histogram(
    'websocket_broadcast_recipients',
    'Número de destinatários por broadcast',
    ['filter_type', 'instance_id'],
    buckets=[1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
)

# Erros
websocket_errors_total = Counter(
    'websocket_errors_total',
    'Total de erros WebSocket',
    ['error_type', 'instance_id']
)

websocket_disconnects_total = Counter(
    'websocket_disconnects_total',
    'Total de desconexões WebSocket',
    ['reason', 'instance_id']
)

# Heartbeat
websocket_dead_connections_cleaned = Counter(
    'websocket_dead_connections_cleaned',
    'Conexões mortas limpas pelo heartbeat monitor',
    ['instance_id']
)

# ==================== Métricas Redis Streams ====================

stream_messages_added_total = Counter(
    'stream_messages_added_total',
    'Total de mensagens adicionadas ao Redis Stream',
    ['stream', 'instance_id']
)

stream_messages_processed_total = Counter(
    'stream_messages_processed_total',
    'Total de mensagens processadas do Redis Stream',
    ['status', 'consumer', 'instance_id']
)

stream_messages_dlq_total = Counter(
    'stream_messages_dlq_total',
    'Total de mensagens movidas para Dead Letter Queue',
    ['instance_id']
)

stream_processing_duration_seconds = Histogram(
    'stream_processing_duration_seconds',
    'Tempo de processamento de mensagens do stream',
    ['consumer', 'instance_id'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

stream_lag = Gauge(
    'stream_lag',
    'Número de mensagens pendentes no stream',
    ['stream', 'consumer_group', 'instance_id']
)

stream_retry_count = Histogram(
    'stream_retry_count',
    'Número de tentativas antes de processar mensagem com sucesso',
    ['consumer', 'instance_id'],
    buckets=[1, 2, 3, 5, 10]
)

stream_consumer_running = Gauge(
    'stream_consumer_running',
    'Status do Stream Consumer (1 = rodando, 0 = parado)',
    ['consumer', 'instance_id']
)

# ==================== Métricas Redis Pub/Sub ====================

redis_pubsub_messages_published = Counter(
    'redis_pubsub_messages_published',
    'Mensagens publicadas no Redis Pub/Sub',
    ['channel', 'instance_id']
)

redis_pubsub_messages_received = Counter(
    'redis_pubsub_messages_received',
    'Mensagens recebidas do Redis Pub/Sub',
    ['channel', 'from_instance', 'instance_id']
)

# ==================== Métricas Event Batcher ====================

event_batcher_events_received = Counter(
    'event_batcher_events_received',
    'Eventos adicionados ao batcher',
    ['event_type', 'instance_id']
)

event_batcher_batches_sent = Counter(
    'event_batcher_batches_sent',
    'Batches enviados pelo batcher',
    ['instance_id']
)

event_batcher_batch_size = Histogram(
    'event_batcher_batch_size',
    'Tamanho dos batches enviados',
    ['instance_id'],
    buckets=[1, 2, 5, 10, 20, 30, 40, 50, 75, 100, 150, 200]
)

event_batcher_buffer_size = Gauge(
    'event_batcher_buffer_size',
    'Tamanho atual do buffer do batcher',
    ['instance_id']
)

# ==================== Métricas Message Store ====================

message_store_messages_stored = Counter(
    'message_store_messages_stored',
    'Mensagens armazenadas no MessageStore',
    ['user_id', 'instance_id']
)

message_store_replay_requests = Counter(
    'message_store_replay_requests',
    'Requisições de replay de mensagens',
    ['instance_id']
)

message_store_replay_messages_sent = Histogram(
    'message_store_replay_messages_sent',
    'Número de mensagens enviadas em replay',
    ['instance_id'],
    buckets=[0, 1, 5, 10, 20, 50, 100, 200]
)

# ==================== Métricas de Sistema ====================

system_info = Info(
    'gas_automation_system',
    'Informações sobre o sistema Gas Automation'
)

system_uptime_seconds = Gauge(
    'system_uptime_seconds',
    'Tempo de atividade do sistema em segundos',
    ['instance_id']
)

# ==================== Decoradores para Instrumentação ====================

def track_websocket_broadcast(filter_type: str = "all"):
    """
    Decorator para rastrear duração e destinatários de broadcasts.
    
    Uso:
        @track_websocket_broadcast(filter_type="role")
        async def broadcast_to_role(self, ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Executar função
            result = await func(*args, **kwargs)
            
            # Registrar duração
            duration = time.time() - start_time
            instance_id = getattr(args[0], 'instance_id', 'unknown') if args else 'unknown'
            
            websocket_broadcast_duration_seconds.labels(
                filter_type=filter_type,
                instance_id=instance_id
            ).observe(duration)
            
            return result
        return wrapper
    return decorator


def track_redis_publish():
    """
    Decorator para rastrear publicações no Redis.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Obter instance_id se disponível
            instance_id = getattr(args[0], 'instance_id', 'unknown') if args else 'unknown'
            channel = args[1] if len(args) > 1 else 'unknown'
            
            redis_pubsub_messages_published.labels(
                channel=channel,
                instance_id=instance_id
            ).inc()
            
            return result
        return wrapper
    return decorator


# ==================== Funções Helper ====================

def update_websocket_metrics(manager, instance_id: str = "unknown"):
    """
    Atualiza métricas de WebSocket baseado no estado atual do ConnectionManager.
    
    Deve ser chamado periodicamente (ex: a cada 30s).
    """
    try:
        # Total de conexões
        total_connections = sum(len(conns) for conns in manager.connections.values())
        websocket_connections_total.labels(role='all', instance_id=instance_id).set(total_connections)
        
        # Total de usuários únicos
        websocket_users_total.labels(instance_id=instance_id).set(len(manager.connections))
        
        # Conexões por role
        role_counts = {}
        for user_conns in manager.connections.values():
            for metadata in user_conns:
                role = metadata.user_role.value
                role_counts[role] = role_counts.get(role, 0) + 1
        
        for role, count in role_counts.items():
            websocket_connections_total.labels(role=role, instance_id=instance_id).set(count)
    
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar métricas WebSocket: {e}")


def update_event_batcher_metrics(batcher, instance_id: str = "unknown"):
    """
    Atualiza métricas de Event Batcher.
    
    Deve ser chamado periodicamente (ex: a cada 30s).
    """
    try:
        stats = batcher.get_stats()
        
        # Buffer size atual
        event_batcher_buffer_size.labels(instance_id=instance_id).set(stats.get('buffer_size', 0))
        
        # Nota: Contadores já são atualizados em tempo real pelo batcher
    
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar métricas Event Batcher: {e}")


def update_redis_bridge_metrics(bridge, instance_id: str = "unknown"):
    """
    Atualiza métricas de Redis Bridge.
    
    Deve ser chamado periodicamente (ex: a cada 30s).
    """
    try:
        stats = bridge.get_stats()
        # Métricas já são atualizadas em tempo real
        pass
    
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar métricas Redis Bridge: {e}")


def init_system_info(version: str = "1.0.0", environment: str = "production"):
    """
    Inicializa informações do sistema.
    """
    system_info.info({
        'version': version,
        'environment': environment,
        'service': 'gas-automation-backend',
    })


# ==================== Logger de Métricas ====================

logger.info("📊 Métricas Prometheus customizadas inicializadas")
