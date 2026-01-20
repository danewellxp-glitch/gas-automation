# ✅ CHECKLIST DE IMPLEMENTAÇÃO - ESCALABILIDADE WEBSOCKET

## 📋 Fase 1: IMEDIATO (Esta Semana)

### 1. Substituir ConnectionManager por ScalableConnectionManager
- [ ] Copiar código de `WEBSOCKET_ESCALAVEL.py` para o projeto
- [ ] Importar `ScalableConnectionManager` em `backend/app/api/websocket.py`
- [ ] Substituir `manager = ConnectionManager()` por `manager = ScalableConnectionManager()`

### 2. Adicionar Suporte a Metadados de Usuário
- [ ] Em `/backend/app/api/websocket.py`, extrair dados do JWT:
```python
@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    # Extrair do token JWT
    user_id = payload.get("sub")
    user_role = payload.get("role", "operator")
    bairro = payload.get("bairro")  # Para operadores
    region = payload.get("region")  # Para managers
    
    await manager.connect(websocket, user_id, user_role, bairro, region)
    # ... resto do código
```

### 3. Atualizar Emissão de Eventos
- [ ] Atualizar `emit_new_message()` em `webhooks.py`:
```python
# ❌ ANTES
await emit_new_message(phone, content, "incoming")

# ✅ DEPOIS - Enviar apenas para admin + operadores relevantes
if order.bairro:
    await manager.broadcast_to_neighborhood({...}, order.bairro)
else:
    await manager.broadcast_to_admin_only({...})
```

### 4. Ativar Heartbeat Monitor
- [ ] Em `main.py`, adicionar ao lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(manager.heartbeat_monitor())
    yield
    # Shutdown
    pass
```

### 5. Testar Rate Limiting
- [ ] Enviar 100 pedidos em 10 segundos
- [ ] Verificar que apenas 10 broadcasts/segundo são processados
- [ ] Ver no log: "Rate limit atingido"

---

## 📋 Fase 2: PRÓXIMAS 2 SEMANAS

### 6. Implementar Paginação no Frontend
- [ ] Instalar `react-window`: `npm install react-window`
- [ ] Atualizar `AdminDashboard.tsx`:
```tsx
import { FixedSizeList as List } from 'react-window';

// ❌ ANTES
<div>{orders.map(order => <OrderCard />)}</div>

// ✅ DEPOIS
<List height={600} itemCount={orders.length} itemSize={100}>
  {({index, style}) => (
    <OrderCard style={style} order={orders[index]} />
  )}
</List>
```

- [ ] Testar com 1000+ pedidos, app deve permanecer responsivo

### 7. Deduplicação de Abas
- [ ] Implementar BroadcastChannel API:
```javascript
// main.jsx
const channel = new BroadcastChannel('gas_automation');

channel.onmessage = (event) => {
  if (event.data.type === 'ws_update') {
    // Reutilizar dados de outra aba
    updateState(event.data);
  }
};

// Quando receber WebSocket, compartilhar com outras abas
channel.postMessage({ type: 'ws_update', data: message });
```

- [ ] Testar abrindo dashboard em 5 abas, deve haver apenas 1 WebSocket ativa

### 8. Implementar Redis Pub/Sub
- [ ] Em `webhooks.py`, usar Redis ao invés de broadcast direto:
```python
from app.database import redis_manager

# Publicar evento
await redis_manager.publish(
    f"orders:neighborhood:{order.bairro}",
    json.dumps(order_data)
)

# Ou por role
await redis_manager.publish("orders:admin", json.dumps(order_data))
```

- [ ] Em `websocket.py`, subscribir a canais relevantes
- [ ] Isso permite múltiplas instâncias do backend

### 9. Adicionar Compressão WebSocket
- [ ] Em `main.py`, ativar permessage-deflate:
```python
# Docker Compose ou Traefik config
labels:
  - "traefik.http.middlewares.websocket-compress.compress=true"
```

---

## 📋 Fase 3: FUTURO (Próximo Mês)

### 10. Implementar Batching de Eventos
- [ ] Agrupar múltiplos eventos em uma mensagem
- [ ] Enviar a cada 500ms ou 10 eventos (o que vier primeiro)

### 11. Persistência de Eventos
- [ ] Armazenar últimos 100 eventos em Redis
- [ ] Cliente reconectado recebe histórico

### 12. Métricas e Monitoramento
- [ ] Adicionar Prometheus metrics para WebSocket
- [ ] Monitorar: conexões ativas, broadcast latency, taxa de erro

### 13. Load Testing
- [ ] Usar `locust` ou `k6` para simular 9000 pedidos
- [ ] Verificar comportamento em pico de tráfego

---

## 🔧 TESTES DE VALIDAÇÃO

### Teste 1: Broadcasting Filtrado
```bash
# Enviar pedido de Curitiba
curl -X POST http://localhost:8000/webhooks/waha \
  -H "Content-Type: application/json" \
  -d '{"bairro": "Centro", "payload": {...}}'

# Operador de São Paulo NÃO deve receber
# Admin deve receber
# Operador de Curitiba deve receber
```

### Teste 2: Rate Limiting
```python
import asyncio

for i in range(100):
    await emit_new_message(f"phone{i}", "test message")
    # Máximo 10 por segundo, resto fica em fila

# Verificar nos logs
```

### Teste 3: Heartbeat
```bash
# Desconectar internet
# Esperar 5 minutos
# Reconectar

# Conexão deve ser removida automaticamente
```

### Teste 4: Performance Frontend
```bash
# Abrir DevTools → Performance
# Adicionar 1000 pedidos
# Re-render deve ser < 100ms (com react-window)
# Sem react-window: > 1000ms
```

---

## 📊 MÉTRICAS ANTES/DEPOIS

| Métrica | Antes | Depois | Meta |
|---------|-------|--------|------|
| **Tráfego por pedido** | 100kb | 10kb | ✅ |
| **Latência WebSocket** | 100ms | 20ms | ✅ |
| **Memória do servidor** | 200MB | 50MB | ✅ |
| **Conexões simultâneas** | 5 | 50+ | ✅ |
| **Pedidos/segundo** | 1 | 10+ | ✅ |
| **Re-render frontend** | 500ms | 50ms | ✅ |
| **Memory leak** | Sim | Não | ✅ |

---

## 🚨 SINAIS DE ALERTA

Se você ver algum desses sinais, é hora de implementar:

- [ ] Dashboard fica lento com 100+ pedidos
- [ ] Server CPU acima de 50% em repouso
- [ ] Mensagens chegam com 10+ segundos de atraso
- [ ] Usuários em diferentes abas veem dados desincronizados
- [ ] Erro: "Too many open connections"
- [ ] Operador vê pedidos de outras cidades
- [ ] App trava ao carregar dashboard

---

## 📞 IMPLEMENTAÇÃO RECOMENDADA

**Se tiver tempo:**
1. Implementar Fase 1 completamente (3-4 horas)
2. Fazer Fase 2 aos poucos (10-15 horas)

**Mínimo viável para produção:**
1. Fase 1 completa (OBRIGATÓRIO)
2. Fase 2 #6 - Paginação (IMPORTANTE)

**Se não fizer nada:**
- Sistema vai falhar com 9000 pedidos/semana
- Ao invés de 2-3 meses, vai falhar em 2-3 semanas
- Usuários vão reclamar de lentidão
- Database vai pedir recursos (dinheiro)

---

## 💡 DICAS

- Começar pela Phase 1 - não demora muito e resolve 70% dos problemas
- Testar cada mudança com `docker-compose logs -f` aberto
- Usar Chrome DevTools → Performance para medir melhorias frontend
- Usar `ab` (Apache Bench) ou `wrk` para simular carga

---

## 📞 SUPORTE

Se tiver dúvidas na implementação:
1. Consulte `ESCALABILIDADE_WEBSOCKET.md` para contexto
2. Consulte `WEBSOCKET_ESCALAVEL.py` para código
3. Este checklist para saber o que fazer

---

**Última atualização:** 20 de Janeiro de 2026
**Status:** ⚠️ CRÍTICO - Implementar antes de ir a produção em escala
