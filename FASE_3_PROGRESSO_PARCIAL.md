# 🚧 FASE 3 - PROGRESSO PARCIAL (EM ANDAMENTO)

**Data**: 21 de Janeiro de 2026  
**Status**: 🚧 **PARCIALMENTE IMPLEMENTADO** (2/4 componentes)  
**Tempo decorrido**: ~2 horas  
**Tempo estimado restante**: 13-18 horas

---

## ✅ **O QUE JÁ FOI IMPLEMENTADO**

### **1. Redis Pub/Sub para Escala Horizontal** ✅

**Arquivos criados:**
- `backend/app/core/redis_websocket_bridge.py` - Bridge completo
- Modificações em `backend/app/database.py` - Métodos publish/subscribe
- Modificações em `backend/app/api/websocket.py` - Integração no ScalableConnectionManager
- Modificações em `backend/app/main.py` - Startup/shutdown automático

**Funcionalidades:**
- ✅ Comunicação entre múltiplas instâncias via Redis Pub/Sub
- ✅ Eleição automática de instance_id único
- ✅ Listener assíncrono com loop de escuta
- ✅ Publicação e recepção de eventos entre instâncias
- ✅ Handler registrado no ConnectionManager
- ✅ Broadcast automático via Redis para todas as instâncias

**Como funciona:**
```
┌──────────┐      ┌──────────┐      ┌──────────┐
│Backend 1 │      │Backend 2 │      │Backend 3 │
│Instance  │      │Instance  │      │Instance  │
└────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │
     └─────────────┬───┴─────────────────┘
                   │
            ┌──────▼───────┐
            │ Redis Pub/Sub│
            │   Channel    │
            └──────────────┘
```

Quando um evento ocorre em Backend 1:
1. Backend 1 publica no Redis
2. Redis distribui para Backend 1, 2 e 3
3. Cada backend faz broadcast para seus clientes WebSocket locais

---

### **2. Event Batcher (Agrupamento de Eventos)** ✅

**Arquivo criado:**
- `backend/app/core/event_batcher.py` - Batcher completo

**Funcionalidades:**
- ✅ Agrupa eventos por tipo antes de enviar
- ✅ Flush automático a cada 100ms
- ✅ Flush automático quando atinge 50 eventos
- ✅ Estatísticas de batching
- ✅ Start/stop com flush final

**Como funciona:**
```python
# Sem batching: 10 mensagens WebSocket
await ws.send('new_order', order1)
await ws.send('new_order', order2)
# ... 10x

# Com batching: 1 mensagem WebSocket
{
  "new_order_batch": {
    "type": "new_order",
    "count": 10,
    "events": [order1, order2, ..., order10]
  }
}
```

**Benefícios:**
- Redução de 90%+ nas mensagens durante picos
- Cliente processa tudo de uma vez (melhor performance)
- Menos overhead de rede

---

## 🚧 **O QUE FALTA IMPLEMENTAR**

### **3. Sistema de Persistência** (Pendente - 4-6 horas)

**O que implementar:**

#### **3.1 Message Store (Armazenamento)**
- Criar `backend/app/core/message_store.py`
- Armazenar mensagens WebSocket no Redis com TTL
- Key pattern: `ws:history:{user_id}:{timestamp}`
- TTL: 1 hora (configurable)
- Limite: últimas 100 mensagens por usuário

#### **3.2 Message Replay (Reconexão Inteligente)**
- Modificar endpoint WebSocket para aceitar `last_message_id`
- Quando cliente reconectar, enviar mensagens perdidas
- Sequência numérica para garantir ordem

**Benefícios:**
- Cliente não perde mensagens durante desconexões
- Reconexão sem perda de dados
- Experiência contínua mesmo com internet instável

---

### **4. Monitoring & Alertas** (Pendente - 7-10 horas)

**O que implementar:**

#### **4.1 Métricas Prometheus**
- Instalar `prometheus-fastapi-instrumentator`
- Adicionar métricas customizadas:
  - `websocket_connections_total` - Total de conexões ativas
  - `websocket_messages_sent_total` - Contador de mensagens enviadas
  - `websocket_messages_received_total` - Contador recebidas
  - `websocket_broadcast_duration_seconds` - Latência de broadcast
  - `redis_pubsub_messages_total` - Mensagens via Redis
  - `event_batcher_batch_size` - Tamanho médio de batches
  - `websocket_errors_total` - Contador de erros

#### **4.2 Endpoint de Métricas**
- Criar `GET /metrics` para Prometheus coletar
- Expor estatísticas do ConnectionManager
- Expor estatísticas do EventBatcher
- Expor estatísticas do Redis Bridge

#### **4.3 Dashboard Grafana**
- Criar dashboard JSON em `grafana/dashboards/websocket.json`
- Painéis:
  - Conexões ativas por instância
  - Taxa de mensagens por segundo
  - Latência de broadcasts
  - Taxa de erros
  - Tamanho de batches
  - Uso de memória
  
#### **4.4 Sistema de Alertas**
- Configurar Alertmanager
- Alertas:
  - Conexões > 100 por instância (warning)
  - Conexões > 200 por instância (critical)
  - Taxa de erro > 5% (warning)
  - Taxa de erro > 10% (critical)
  - Latência > 500ms (warning)
  - Latência > 1000ms (critical)
  
---

## 📊 **IMPACTO ESPERADO (FASE 3 COMPLETA)**

| Métrica | Atual (Fase 1+2) | Com Fase 3 | Melhoria |
|---------|------------------|------------|----------|
| **Instâncias backend** | 1 | Múltiplas | Escala horizontal |
| **Mensagens (picos)** | 100/s | 10/s | 90% menos |
| **Latência** | 20ms | 5-10ms | 50-75% melhor |
| **Perda de mensagens** | Possível em desconexões | Zero | 100% confiável |
| **Visibilidade** | Logs básicos | Métricas + Alertas | Observabilidade completa |
| **Capacidade** | 9.000/semana | 50.000+/semana | 5x mais |

---

## 🔧 **COMO CONTINUAR A IMPLEMENTAÇÃO**

### **Passo 1: Integrar Event Batcher no WebSocket**

Modificar `backend/app/api/websocket.py`:

```python
from app.core.event_batcher import EventBatcher

class ScalableConnectionManager:
    def __init__(self, ...):
        # ... existing code ...
        
        # Event Batcher (FASE 3)
        self.event_batcher = EventBatcher(
            flush_callback=self._batch_flush_callback,
            flush_interval_ms=100,
            max_batch_size=50
        )
    
    async def _batch_flush_callback(self, batched_events: dict):
        """Callback quando batch está pronto para enviar."""
        for event_type, data in batched_events.items():
            await self._broadcast_local(data, filter_fn=None)
    
    async def broadcast_batched(self, event_type: str, data: dict):
        """Adiciona evento ao batcher ao invés de enviar imediatamente."""
        await self.event_batcher.add_event(event_type, data)
```

Modificar startup em `backend/app/main.py`:

```python
# Iniciar Event Batcher
await ws_manager.event_batcher.start()
print("✅ Event Batcher iniciado")
```

---

### **Passo 2: Implementar Persistência**

Criar `backend/app/core/message_store.py`:

```python
class MessageStore:
    def __init__(self, redis_client, ttl=3600, max_messages=100):
        self.redis = redis_client
        self.ttl = ttl
        self.max_messages = max_messages
    
    async def store_message(self, user_id: str, message: dict):
        """Armazena mensagem no Redis."""
        key = f"ws:history:{user_id}"
        message_json = json.dumps(message)
        
        # Adicionar à lista
        await self.redis.lpush(key, message_json)
        
        # Manter apenas últimas N mensagens
        await self.redis.ltrim(key, 0, self.max_messages - 1)
        
        # Definir TTL
        await self.redis.expire(key, self.ttl)
    
    async def get_messages_since(self, user_id: str, since_id: int = 0):
        """Recupera mensagens desde um ID específico."""
        key = f"ws:history:{user_id}"
        messages = await self.redis.lrange(key, 0, -1)
        
        # Filtrar e retornar
        return [json.loads(m) for m in messages if ...]
```

---

### **Passo 3: Adicionar Métricas Prometheus**

Instalar dependência:
```bash
pip install prometheus-fastapi-instrumentator
```

Adicionar em `backend/app/main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

# Após criar app
Instrumentator().instrument(app).expose(app)
```

Criar métricas customizadas:

```python
from prometheus_client import Counter, Gauge, Histogram

# Métricas WebSocket
ws_connections = Gauge('websocket_connections', 'Total WebSocket connections')
ws_messages_sent = Counter('websocket_messages_sent_total', 'Messages sent')
ws_broadcast_duration = Histogram('websocket_broadcast_seconds', 'Broadcast latency')
```

---

### **Passo 4: Criar Dashboard Grafana**

Criar `grafana/dashboards/websocket.json` com painéis para:
- Conexões ativas
- Taxa de mensagens
- Latência
- Taxa de erro
- Estatísticas de batching

---

### **Passo 5: Configurar Alertas**

Criar `prometheus/alerts.yml`:

```yaml
groups:
  - name: websocket
    rules:
      - alert: HighWebSocketConnections
        expr: websocket_connections > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Muitas conexões WebSocket"
```

---

## 📝 **CHECKLIST DE IMPLEMENTAÇÃO**

### **Redis Pub/Sub** ✅
- [x] Criar RedisWebSocketBridge
- [x] Adicionar métodos Pub/Sub no RedisManager
- [x] Integrar no ScalableConnectionManager
- [x] Iniciar/parar no startup/shutdown
- [ ] Testar com múltiplas instâncias

### **Event Batcher** ✅
- [x] Criar EventBatcher
- [ ] Integrar no WebSocket broadcast
- [ ] Iniciar/parar no startup/shutdown
- [ ] Testar agrupamento de eventos

### **Persistência** ⏳
- [ ] Criar MessageStore
- [ ] Integrar no WebSocket
- [ ] Implementar replay de mensagens
- [ ] Adicionar sequence IDs
- [ ] Testar reconexão

### **Monitoring** ⏳
- [ ] Instalar Prometheus instrumentator
- [ ] Adicionar métricas customizadas
- [ ] Criar endpoint /metrics
- [ ] Criar dashboard Grafana
- [ ] Configurar alertas
- [ ] Testar coleta de métricas

---

## 🚀 **PRÓXIMOS PASSOS RECOMENDADOS**

1. **Integrar Event Batcher** (30min-1h)
   - Modificar broadcast para usar batcher
   - Testar com múltiplos eventos

2. **Implementar Persistência** (4-6h)
   - Message Store
   - Replay de mensagens
   - Testes de reconexão

3. **Adicionar Monitoring** (7-10h)
   - Métricas Prometheus
   - Dashboard Grafana
   - Sistema de alertas

4. **Testes Finais** (2-3h)
   - Stress test com 10.000+ eventos
   - Teste de múltiplas instâncias
   - Teste de reconexão
   - Verificar alertas

---

## 📊 **RESUMO DO STATUS**

**Implementado:**
- ✅ Redis Pub/Sub (escala horizontal)
- ✅ Event Batcher (código criado)

**Pendente:**
- ⏳ Integração do Event Batcher
- ⏳ Sistema de Persistência
- ⏳ Monitoring & Alertas
- ⏳ Testes completos

**Tempo restante estimado:** 13-18 horas

**Progresso:** ~15% da Fase 3 completa

---

**Última atualização:** 21 de Janeiro de 2026
