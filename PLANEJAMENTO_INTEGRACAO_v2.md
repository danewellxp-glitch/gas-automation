# Planejamento de Integração v2 - Backend Consolidado

**Data:** 21/01/2026
**Status:** Revisado e Atualizado

---

## Resumo Executivo

Analisados os arquivos legados (`main_eric.py`, `vamos usar/`) e o backend modular (`backend/`).

**Descoberta Principal:** O backend modular (`backend/`) **JA ESTA 85% COMPLETO**. O planejamento anterior estava desatualizado.

---

## Estado Atual dos Componentes

### Backend Modular (EXISTENTE E FUNCIONAL)
| Componente | Arquivos | Linhas | Status |
|------------|----------|--------|--------|
| Config | `app/config.py` | 173 | OK |
| Database | `app/database.py` | 211 | OK - Async PostgreSQL + Redis |
| Models | `app/models/` (12 arquivos) | ~450 | OK |
| Schemas | `app/schemas/` (8 arquivos) | ~300 | OK |
| Services | `app/services/` (11 arquivos) | ~750 | OK |
| APIs | `app/api/` (12 rotas) | ~800 | OK |
| Integrations | `app/integrations/` (5 arquivos) | ~400 | OK |
| Core | `app/core/` (7 arquivos) | ~600 | OK |
| Tests | `tests/` (4 arquivos) | ~300 | OK |
| Main | `app/main.py` | 1070 | OK |

### Arquivos Legados (REFERENCIA)
| Arquivo | Linhas | Funcionalidades Uteis |
|---------|--------|----------------------|
| `main_eric.py` | ~2200 | Chatbot analytics, WAHA completo, Admin CRUD |
| `vamos usar/main.py` | ~3200 | Templates HTML, Conversation flow |
| `vamos usar/enhanced_chatbot_service.py` | 572 | Multi-tier fallback (Claude/Ollama/Rasa) |
| `vamos usar/models.py` | 77 | BotInteraction, BotContext |

---

## Funcionalidades a Integrar do Legado

### PRIORIDADE ALTA - Faltam no Backend Modular

#### 1. Chatbot Analytics (`/chatbot/analytics`)
```
Origem: main_eric.py:1417-1467
- Total de interacoes
- Taxa de escalation
- Distribuicao por tipo de bot (Claude/Ollama/Fallback)
- Razoes de escalation
- Interacoes ultimas 24h
```

#### 2. Chatbot Status (`/chatbot/status`)
```
Origem: main_eric.py:1320-1389
- Status Claude API (online/offline)
- Status Rasa (online/offline)
- Status Ollama (online/offline)
- Features disponiveis
```

#### 3. Chatbot Context Management
```
Origem: main_eric.py:1391-1415
- POST /chatbot/clear-context/{phone_number}
- POST /chatbot/cleanup-contexts
```

#### 4. Admin User Management Completo
```
Origem: main_eric.py:679-859
- GET /admin/users
- POST /admin/users
- PUT /admin/users/{user_id}
- DELETE /admin/users/{user_id} (desativa)
- POST /admin/users/{user_id}/reset-password
```

#### 5. Audit Logs
```
Origem: main_eric.py:861-871
- GET /admin/audit-logs
- Registro de acoes administrativas
```

#### 6. WAHA Session Management Completo
```
Origem: main_eric.py:2024-2081
- GET /api/waha/status
- POST /api/waha/start-session
- POST /api/waha/stop-session
- GET /api/waha/qrcode
- POST /api/waha/logout
- POST /api/waha/send-message
```

#### 7. Conversation Management
```
Origem: main_eric.py:972-1108
- POST /conversations/{id}/reply
- POST /conversations/{id}/end
- POST /conversations/{id}/status
- POST /conversations/{id}/assign
```

#### 8. Dashboard Statistics Completo
```
Origem: main_eric.py:1592-1693
- Mensagens por tipo (customer/agent/bot)
- Bot services breakdown (Claude/Ollama/Fallback)
- Conversas ultimos 7 dias
- Conversas recentes
```

### PRIORIDADE MEDIA - Ja Existe Parcialmente

#### 9. BotInteraction Model
```
Origem: vamos usar/models.py:49-60
Status: Verificar se existe em app/models/
Campos: phone_number, customer_name, user_message, bot_response,
        bot_type, escalated, escalation_reason, response_time_ms
```

#### 10. Test Bot Endpoint
```
Origem: main_eric.py:1147-1285
- POST /test-bot - Testar chatbot sem WhatsApp
- Util para desenvolvimento
```

### PRIORIDADE BAIXA - Nice to Have

#### 11. Refresh Token
```
Origem: main_eric.py:650-664
- POST /refresh-token
- Renovacao automatica de tokens
```

#### 12. Agent Status
```
Origem: main_eric.py:949-970
- GET /agents/status
- Quantidade de conversas pendentes por agente
```

---

## Plano de Execucao

### FASE 1: Validacao do Backend Atual (IMEDIATO)
**Objetivo:** Garantir que o backend modular funciona

| # | Tarefa | Comando |
|---|--------|---------|
| 1 | Verificar imports | `cd backend && python -c "from app.main import app"` |
| 2 | Verificar testes | `cd backend && pytest tests/ -v` |
| 3 | Verificar migrations | `cd backend && alembic current` |
| 4 | Iniciar servidor | `cd backend && uvicorn app.main:app --reload` |

### FASE 2: Integracao de Funcionalidades Prioritarias
**Tempo Estimado:** 2-3 dias

#### 2.1 - Chatbot Endpoints (api/chatbot.py)
```python
# Adicionar em app/api/chatbot.py:
- GET /status - Status dos servicos de IA
- GET /analytics - Metricas do chatbot
- POST /clear-context/{phone} - Limpar contexto
- POST /cleanup-contexts - Limpeza em massa
```

#### 2.2 - Admin Endpoints (api/users.py)
```python
# Adicionar/completar em app/api/users.py:
- GET /admin/users - Listar usuarios
- POST /admin/users - Criar usuario
- PUT /admin/users/{id} - Atualizar
- DELETE /admin/users/{id} - Desativar
- POST /admin/users/{id}/reset-password
- GET /admin/audit-logs
```

#### 2.3 - WAHA Management (api/webhooks.py ou novo arquivo)
```python
# Adicionar em app/api/waha.py:
- GET /waha/status
- POST /waha/start-session
- POST /waha/stop-session
- GET /waha/qrcode
- POST /waha/logout
```

### FASE 3: Models e Services Complementares
**Tempo Estimado:** 1-2 dias

#### 3.1 - BotInteraction Model
```python
# Verificar/criar app/models/bot_interaction.py
class BotInteraction(Base):
    phone_number: str
    customer_name: Optional[str]
    user_message: str
    bot_response: str
    bot_type: str  # claude, ollama, rasa, fallback
    escalated: bool = False
    escalation_reason: Optional[str]
    response_time_ms: Optional[int]
    timestamp: datetime
```

#### 3.2 - AuditLog Model
```python
# Verificar/criar em app/models/auth_models.py
class AuditLog(Base):
    action: str
    user_id: Optional[int]
    conversation_id: Optional[int]
    details: Optional[str]
    timestamp: datetime
```

### FASE 4: Dashboard e Reports
**Tempo Estimado:** 1 dia

- Verificar `/api/stats` - Ja existe em main.py:357
- Verificar `/api/reports/financial` - Ja existe em main.py:495
- Adicionar breakdown por bot service
- Adicionar conversas por periodo

### FASE 5: Testes e Documentacao
**Tempo Estimado:** 1 dia

- Rodar suite de testes completa
- Documentar endpoints novos
- Atualizar OpenAPI/Swagger

---

## Matriz de Migracao

| Funcionalidade | Legado | Backend Modular | Acao |
|----------------|--------|-----------------|------|
| Auth JWT | main_eric.py | app/auth.py | OK |
| Users CRUD | main_eric.py | app/api/users.py | COMPLETAR |
| Conversations | main_eric.py | app/api/chats.py | VERIFICAR |
| Products | main_eric.py | app/api/products.py | OK |
| Orders | main_eric.py | app/api/orders.py | OK |
| Drivers | main_eric.py | app/api/drivers.py | OK |
| Customers | main_eric.py | app/api/customers.py | OK |
| WebSocket | main_eric.py | app/api/websocket.py | OK (melhorado) |
| Chatbot | main_eric.py | app/api/chatbot.py | COMPLETAR |
| WAHA | main_eric.py | app/integrations/waha.py | COMPLETAR API |
| Reports | main_eric.py | app/main.py | OK |
| Metrics | - | app/metrics.py | OK (novo) |

---

## Arquivos Legados a Descartar

Apos integracao, estes arquivos podem ser arquivados:

```
/vamos usar/main.py          -> Monolitico, substituido
/vamos usar/models.py        -> Integrado em app/models/
/vamos usar/auth.py          -> Integrado em app/auth.py
/vamos usar/config.py        -> Integrado em app/config.py
/main_eric.py                -> Referencia historica apenas
```

---

## Checklist de Validacao Final

### Pre-Integracao
- [ ] Backend modular inicia sem erros
- [ ] Conexao PostgreSQL funciona
- [ ] Conexao Redis funciona
- [ ] Testes passam

### Pos-Integracao
- [ ] Todos endpoints do legado mapeados
- [ ] Chatbot multi-tier funcionando
- [ ] WAHA conectado e enviando mensagens
- [ ] Dashboard mostrando dados reais
- [ ] Admin pode criar/editar usuarios
- [ ] Audit logs sendo registrados
- [ ] Prometheus coletando metricas

---

## Conclusao

O backend modular ja esta **muito mais avancado** que o documento anterior sugeria.
As principais lacunas sao:

1. **Chatbot analytics/status endpoints** (ALTA)
2. **Admin user management completo** (ALTA)
3. **WAHA session management API** (ALTA)
4. **Conversation management endpoints** (MEDIA)

A integracao pode ser feita em **3-5 dias** focando apenas no que falta.

**RECOMENDACAO:** Comecar pela validacao (FASE 1) para confirmar o estado atual.
