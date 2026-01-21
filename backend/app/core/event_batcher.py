"""
Event Batcher - Agrupa múltiplos eventos WebSocket em batches.

Reduz drasticamente o número de mensagens WebSocket enviadas quando
há muitos eventos acontecendo simultaneamente.

Exemplo:
    Sem batching:  10 pedidos = 10 mensagens WebSocket
    Com batching:  10 pedidos = 1 mensagem com array de 10 pedidos

Benefícios:
- Redução de 90%+ nas mensagens WebSocket em picos
- Menos overhead de rede
- Melhor performance do cliente (processa tudo de uma vez)
"""

import asyncio
import logging
from typing import Dict, List, Callable
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventBatcher:
    """
    Agrupa eventos por tipo antes de enviar.
    
    Funcionamento:
    1. Eventos são adicionados ao buffer
    2. Após `flush_interval_ms`, todos os eventos são agrupados e enviados
    3. Se `max_batch_size` for atingido, flush automático
    """
    
    def __init__(
        self,
        flush_callback: Callable,
        flush_interval_ms: int = 100,
        max_batch_size: int = 50
    ):
        """
        Args:
            flush_callback: async function(batched_events) que será chamada com os eventos agrupados
            flush_interval_ms: Intervalo em ms para fazer flush automático (default: 100ms)
            max_batch_size: Número máximo de eventos por batch antes de flush automático
        """
        self.flush_callback = flush_callback
        self.flush_interval = flush_interval_ms / 1000.0  # Converter para segundos
        self.max_batch_size = max_batch_size
        
        # Buffer de eventos por tipo
        # {event_type: [event1, event2, ...]}
        self.buffer: Dict[str, List[dict]] = defaultdict(list)
        
        # Task de flush periódico
        self.flush_task = None
        self.is_running = False
        
        # Estatísticas
        self.stats = {
            "events_received": 0,
            "events_sent": 0,
            "batches_sent": 0,
            "avg_batch_size": 0.0,
        }
    
    async def start(self):
        """Inicia o batcher."""
        if self.is_running:
            logger.warning("EventBatcher já está rodando")
            return
        
        self.is_running = True
        self.flush_task = asyncio.create_task(self._flush_loop())
        logger.info(
            f"📦 EventBatcher iniciado "
            f"(interval={self.flush_interval*1000:.0f}ms, max_size={self.max_batch_size})"
        )
    
    async def stop(self):
        """Para o batcher e faz flush final."""
        self.is_running = False
        
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush final de eventos pendentes
        await self.flush()
        
        logger.info("📦 EventBatcher parado")
    
    async def add_event(self, event_type: str, event_data: dict):
        """
        Adiciona um evento ao buffer.
        
        Args:
            event_type: Tipo do evento (ex: 'new_order', 'order_update')
            event_data: Dados do evento
        """
        self.buffer[event_type].append(event_data)
        self.stats["events_received"] += 1
        
        # Flush automático se batch está cheio
        total_events = sum(len(events) for events in self.buffer.values())
        if total_events >= self.max_batch_size:
            await self.flush()
    
    async def flush(self):
        """
        Faz flush de todos os eventos no buffer.
        Agrupa eventos do mesmo tipo em arrays.
        """
        if not self.buffer:
            return
        
        # Criar batches
        batched_events = {}
        total_events = 0
        
        for event_type, events in self.buffer.items():
            if not events:
                continue
            
            # Se houver apenas 1 evento, enviar normalmente
            # Se houver múltiplos, enviar como array
            if len(events) == 1:
                batched_events[event_type] = events[0]
            else:
                batched_events[f"{event_type}_batch"] = {
                    "type": event_type,
                    "count": len(events),
                    "events": events,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            
            total_events += len(events)
        
        # Limpar buffer
        self.buffer.clear()
        
        # Enviar batches via callback
        if batched_events:
            try:
                await self.flush_callback(batched_events)
                
                # Atualizar estatísticas
                self.stats["events_sent"] += total_events
                self.stats["batches_sent"] += 1
                self.stats["avg_batch_size"] = (
                    self.stats["events_sent"] / self.stats["batches_sent"]
                )
                
                logger.debug(
                    f"📤 Batch enviado: {total_events} eventos "
                    f"({len(batched_events)} tipos únicos)"
                )
            
            except Exception as e:
                logger.error(f"❌ Erro ao fazer flush de batch: {e}")
    
    async def _flush_loop(self):
        """Loop que faz flush periódico."""
        try:
            while self.is_running:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"❌ Erro no loop de flush: {e}")
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do batcher."""
        return {
            **self.stats,
            "buffer_size": sum(len(events) for events in self.buffer.values()),
            "buffer_types": len(self.buffer),
        }


# Exemplo de uso:
"""
async def on_batch_ready(batched_events):
    # Enviar via WebSocket
    for event_type, data in batched_events.items():
        await websocket_manager.broadcast(data)

batcher = EventBatcher(
    flush_callback=on_batch_ready,
    flush_interval_ms=100,  # Flush a cada 100ms
    max_batch_size=50       # Ou quando tiver 50 eventos
)

await batcher.start()

# Adicionar eventos
await batcher.add_event('new_order', order_data)
await batcher.add_event('new_order', order_data2)
await batcher.add_event('order_update', update_data)

# Após 100ms (ou 50 eventos), todos serão enviados agrupados:
# {
#   'new_order_batch': {
#     'type': 'new_order',
#     'count': 2,
#     'events': [order_data, order_data2]
#   },
#   'order_update': update_data  # Apenas 1, então não agrupa
# }
"""
