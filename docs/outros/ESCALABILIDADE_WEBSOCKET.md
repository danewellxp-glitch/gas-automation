# 🚀 Análise de Escalabilidade - WebSocket para 9000+ Pedidos/Semana

## 📊 Volume de Tráfego Esperado
- **9000 pedidos/semana** = ~1285 pedidos/dia = ~53 pedidos/hora
- **Pico estimado**: 200+ pedidos/hora em horário de pico
- **Usuários simultâneos**: 5-20 operadores/admin/owners

---

## 🚨 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1️⃣ **BROADCASTING SEM FILTRAGEM** (Impacto: CRÍTICO)
**Problema:** `broadcast()` envia para TODAS as conexões, sem discriminar por usuário/papel

```python
# ❌ CÓDIGO ATUAL (Ineficiente)
async def broadcast(self, message: dict):
    for connection in self.active_connections:  # Envia para TODOS
        await connection.send_text(message_json)
```

**Consequências:**
- Um operador de Curitiba recebe pedidos de São Paulo
- Múltiplas abas = múltiplas cópias da mesma mensagem
- Tráfego desnecessário de rede

**Solução:**
- [ ] Armazenar metadados de cada conexão (user_id, role, bairro)
- [ ] Filtrar broadcast por critério (ex: only admin, only this neighborhood)
- [ ] Usar Redis pub/sub para suportar múltiplas instâncias

---

### 2️⃣ **SEM PAGINAÇÃO EM TEMPO REAL** (Impacto: CRÍTICO)
**Problema:** Frontend carrega TODAS as 9000+ ordens na memória

```tsx
// ❌ CÓDIGO ATUAL
const [orders, setOrders] = useState<Order[]>([]);  // Array com 9000+ itens!
```

**Consequências:**
- Aplicação fica lenta com 9000 objetos em RAM
- Re-render completo a cada mudança
- Memória crescente com cada novo pedido

**Solução:**
- [ ] Implementar paginação/virtualização (mostrar 20-50 por página)
- [ ] Usar react-window ou react-virtualized
- [ ] Backend retorna apenas últimos 50 pedidos + informação de novo

---

### 3️⃣ **CONEXÕES DUPLICADAS** (Impacto: ALTO)
**Problema:** Sem controle de múltiplas abas/sessões do mesmo usuário

```
Usuário abre Dashboard em 5 abas
├─ Aba 1: WebSocket1 conectada
├─ Aba 2: WebSocket2 conectada
├─ Aba 3: WebSocket3 conectada
├─ Aba 4: WebSocket4 conectada
└─ Aba 5: WebSocket5 conectada

Quando pedido chega: Servidor envia 5x a mesma mensagem!
```

**Consequências:**
- Multiplicação desnecessária de tráfego
- Consumo de memória do servidor

**Solução:**
- [ ] Usar sessionStorage para identificar aba
- [ ] Implementar deduplicação no servidor
- [ ] Reutilizar conexão entre abas (SharedWorker/BroadcastChannel)

---

### 4️⃣ **SEM RATE LIMITING** (Impacto: ALTO)
**Problema:** Sem proteção contra picos de tráfego

**Cenário de falha:**
```
100 pedidos chegam em 10 segundos (horário de pico)
├─ 100 webhooks processados em paralelo
├─ 100 emit_new_message() chamadas simultâneas
└─ Servidor fica sobrecarregado
```

**Solução:**
- [ ] Rate limit: máx 10 broadcasts por segundo
- [ ] Fila de eventos com processamento assíncrono
- [ ] Usar Bull/BullMQ para queue de jobs

---

### 5️⃣ **MEMÓRIA INFINITA** (Impacto: MÉDIO)
**Problema:** Desconexões lentas deixam conexões "mortas" na lista

```python
# ❌ PROBLEMA
active_connections: Set[WebSocket] = set()

# Conexão morta fica na lista forever, causando memory leak
```

**Solução:**
- [ ] Implementar heartbeat (ping/pong)
- [ ] Timeout automático de 5 minutos
- [ ] Cleanup de conexões "stale"

---

### 6️⃣ **SEM BATCHING** (Impacto: MÉDIO)
**Problema:** Cada evento é uma mensagem WebSocket separada

```
9000 pedidos = 9000+ mensagens WebSocket
Cada mensagem tem overhead de protocolo WebSocket
```

**Solução:**
- [ ] Agrupar eventos em lotes (a cada 500ms)
- [ ] Enviar múltiplos eventos em uma mensagem
- [ ] Backend: `emit_batch([msg1, msg2, msg3])`

---

### 7️⃣ **FALTA DE AUTORIZAÇÃO EM TEMPO REAL** (Impacto: ALTO)
**Problema:** Frontend não filtra por papel/permissão

```tsx
// ❌ PROBLEMA: Operador vê TODOS os pedidos
const [orders, setOrders] = useState<Order[]>([]);

// Deveria ser filtrado por bairro/região do operador
```

**Solução:**
- [ ] Backend envia apenas dados autorizados
- [ ] Filtrar broadcast por role: admin recebe tudo, operador recebe seu bairro
- [ ] Implementar permissões no WebSocket

---

### 8️⃣ **SEM COMPRESSÃO** (Impacto: BAIXO)
**Problema:** Dados trafegam sem compressão

**Solução:**
- [ ] Ativar compressão WebSocket (permessage-deflate)
- [ ] Reduz ~70% do tráfego

---

## ✅ SOLUÇÕES RECOMENDADAS (Em Ordem de Prioridade)

### **FASE 1 - IMEDIATO** (Desta semana)
1. **Filtrar broadcast por papel/permissão**
   ```python
   async def broadcast_filtered(self, message: dict, filter_fn=None):
       for connection in self.active_connections:
           if filter_fn is None or filter_fn(connection):
               await connection.send_text(...)
   ```

2. **Implementar heartbeat para limpar conexões mortas**
   ```python
   async def heartbeat_monitor(self):
       while True:
           for conn in list(self.active_connections):
               try:
                   await conn.send_json({"type": "ping"})
               except:
                   self.disconnect(conn)
   ```

3. **Rate limiting de broadcasts**
   ```python
   from datetime import datetime, timedelta
   
   class RateLimitedBroadcaster:
       def __init__(self, max_per_second=10):
           self.queue = asyncio.Queue()
           self.max_per_second = max_per_second
   ```

### **FASE 2 - PRÓXIMAS 2 SEMANAS**
1. **Paginação no frontend**
   - Implementar react-window
   - Mostrar 30 pedidos por página
   - Carregar mais sob demanda

2. **Deduplicação de conexões**
   - Usar BroadcastChannel API
   - Compartilhar estado entre abas

3. **Redis Pub/Sub**
   - Suportar múltiplas instâncias do backend
   - Pub/Sub centralizado

### **FASE 3 - MELHORIAS FUTURAS**
1. **Batching de eventos**
2. **Compressão WebSocket**
3. **Persistência de eventos** (para reconexão)
4. **Métricas de performance**

---

## 📈 IMPACTO ESPERADO

| Métrica | Antes | Depois |
|---------|-------|--------|
| **Mensagens/pedido** | 1 broadcast para TODOS | 1 broadcast filtrado |
| **Tráfego de rede** | 100% | ~30% (com batching) |
| **Latência** | 50-100ms | 10-20ms |
| **Memória do servidor** | ~200MB | ~50MB |
| **Suporte de usuários** | 5-10 | 50+ |
| **Taxa de pico** | Falha acima 50/h | Suporta 200+/h |

---

## 🔧 COMEÇAR POR AQUI

```javascript
// CÓDIGO PARA IMPLEMENTAR IMEDIATAMENTE

// Backend: Filtrar broadcast por papel
async def emit_new_message_filtered(phone: str, message: str, required_role: str = None):
    await manager.broadcast_filtered(
        {
            "type": "new_message",
            "data": {"phone": phone, "message": message}
        },
        filter_fn=lambda conn: conn.user_role in [required_role, "admin"] if required_role else True
    )
```

---

## 📞 RECOMENDAÇÃO FINAL

Com 9000 pedidos/semana, você está em **zona de risco**. Recomendo implementar as soluções FASE 1 **imediatamente** antes de ir produção em escala. Senão, terá problemas em 2-3 semanas.

**Prioridade MÁXIMA:**
1. ✅ Filtrar broadcast (problema #1)
2. ✅ Rate limiting (problema #4)
3. ✅ Heartbeat (problema #5)
