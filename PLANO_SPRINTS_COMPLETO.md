# PLANO DE SPRINTS - SISTEMA DE AUTOMAÇÃO DE GÁS

**Data:** 21 de Janeiro de 2026
**Versão:** 1.0.0
**Pontuação Atual:** 6.5/10
**Codebase:** ~22.1K linhas (13.2K backend + 8.9K frontend)

---

## RESUMO EXECUTIVO

| Severidade | Backend | Frontend | Infra | Total |
|------------|---------|----------|-------|-------|
| 🔴 CRÍTICA | 15 | 10 | 5 | **30** |
| 🟠 ALTA | 25 | 15 | 8 | **48** |
| 🟡 MÉDIA | 20 | 20 | 5 | **45** |
| **Total** | **60** | **45** | **18** | **123** |

---

# SPRINT 1: SEGURANÇA CRÍTICA (1 semana)

## Objetivo: Corrigir vulnerabilidades de segurança críticas

### 1.1 Autenticação Faltante 🔴
| Arquivo | Linha | Problema | Ação |
|---------|-------|----------|------|
| `backend/app/api/orders.py` | 186-189 | POST sem auth | Adicionar `Depends(get_current_user)` |
| `backend/app/api/orders.py` | 385-414 | DELETE sem auth | Adicionar `Depends(get_current_user)` |
| `backend/app/api/customers.py` | GET/POST | Endpoints expostos | Adicionar autenticação |

### 1.2 Remover Debug Prints 🔴
| Arquivo | Linhas | Problema |
|---------|--------|----------|
| `backend/app/api/webhooks.py` | 42-46 | `print()` com dados sensíveis |
| `backend/app/integrations/ollama.py` | vários | `print()` em produção |
| `backend/app/services/image_processor.py` | vários | `print()` expondo dados |

**Ação:** Converter todos para `logger.info()` ou `logger.debug()`

### 1.3 Corrigir Bare Excepts 🔴
| Arquivo | Linha | Problema |
|---------|-------|----------|
| `backend/app/api/websocket.py` | 336 | `except: pass` silencioso |
| `backend/app/services/image_processor.py` | 167, 175 | `except:` sem logging |

**Ação:** Adicionar logging estruturado e tratamento específico

### 1.4 Secrets e Configuração 🔴
| Arquivo | Problema | Ação |
|---------|----------|------|
| `docker-compose.yml` | SECRET_KEY padrão inseguro | Gerar chave forte |
| `docker-compose.yml` | MinIO credenciais padrão | Gerar senhas fortes |
| `.env` | Pode estar commitado | Criar `.env.example` |

### 1.5 URLs Hardcoded no Frontend 🔴
| Arquivo | Linha | Problema |
|---------|-------|----------|
| `frontend/src/components/operator/CreateOrderPanel.jsx` | 45, 121 | IP hardcoded |
| `frontend/src/components/operator/PendingOrdersPanel.jsx` | 23 | IP hardcoded |
| `frontend/src/services/api.js` | 4 | Fallback com IP |

**Ação:** Usar `import.meta.env.VITE_API_URL` em todos

### 1.6 Limpeza de Código Morto 🟠
| Arquivo/Pasta | Ação |
|---------------|------|
| `backend/eric_files/` | DELETAR (código antigo) |
| `frontend/src/pages/operator/OperatorDashboard.old.jsx` | DELETAR |
| `frontend/src/pages/operator/OperatorDashboard.tsx` | DELETAR (duplicado) |
| `frontend/src/pages/admin/AdminDashboard.tsx` | DELETAR (duplicado) |
| `backend/create_tables.py` | DELETAR (usar Alembic) |
| `backend/create_user.py` | DELETAR (usar Alembic) |

### Entregáveis Sprint 1:
- [ ] Todos endpoints com autenticação
- [ ] Zero `print()` no código
- [ ] Zero bare excepts
- [ ] Secrets fortes gerados
- [ ] `.env.example` criado
- [ ] URLs centralizadas
- [ ] Código morto removido

**Estimativa:** 8-12 horas

---

# SPRINT 2: QUALIDADE DE CÓDIGO (1 semana)

## Objetivo: Melhorar qualidade e manutenibilidade

### 2.1 Backend - Correções de Lógica 🟠

| Arquivo | Linha | Problema | Solução |
|---------|-------|----------|---------|
| `backend/app/models/order.py` | 196-208 | `func.now()` usado errado | Usar `datetime.utcnow()` |
| `backend/app/services/order_service.py` | 21-35 | Status inexistentes | Usar status válidos: PENDING, PAID, PREPARING, DISPATCHED, DELIVERED, CANCELLED |
| `backend/app/models/customer.py` | 74-79 | `default=dict` (mutable) | Usar `default=None` |
| `backend/app/main.py` | 355-410 | Estatísticas fake | Usar dados reais do banco |

### 2.2 Backend - Validações 🟠

| Arquivo | Problema | Solução |
|---------|----------|---------|
| `backend/app/models/order.py` | `delivery_address` sem validação | Adicionar Pydantic validator |
| `backend/app/api/orders.py` | Filtro bairro case-sensitive | Validar contra lista |
| `backend/app/auth.py` | Usuário desativado pode acessar | Verificar `is_active` |

### 2.3 Frontend - Error Handling 🟠

| Arquivo | Problema | Solução |
|---------|----------|---------|
| `CreateOrderPanel.jsx` | Validação silenciosa | Mostrar mensagens visuais |
| `PendingOrdersPanel.jsx` | Usa `alert()` nativo | Usar Toast/Notification |
| `Login.jsx` | Apenas `console.error` | Mostrar erro na UI |
| Todos os componentes | ~50 `console.log` | Criar logger util |

### 2.4 Frontend - Centralização 🟠

| Problema | Solução |
|----------|---------|
| Fetch direto em componentes | Usar `services/api.js` |
| Estados dispersos (10+ useState) | Usar `useReducer` |
| Sem loading states em botões | Adicionar `disabled={processing}` |

### 2.5 Docker/Infra 🟠

| Arquivo | Linha | Problema | Solução |
|---------|-------|----------|---------|
| `docker-compose.yml` | 159 | `--reload` em produção | Remover flag |
| `docker-compose.yml` | 268 | `npm run dev` em produção | Build estático + nginx |
| `docker-compose.yml` | 215 | CORS `*` headers | Whitelist específica |

### Entregáveis Sprint 2:
- [ ] Lógica de status corrigida
- [ ] Validações implementadas
- [ ] Error handling consistente
- [ ] Console.log removidos
- [ ] API calls centralizadas
- [ ] Docker otimizado para produção

**Estimativa:** 12-16 horas

---

# SPRINT 3: TESTES E DOCUMENTAÇÃO (2 semanas)

## Objetivo: Aumentar cobertura de testes para 60%+

### 3.1 Testes Backend Críticos 🟠

```
✗ Order creation com items
✗ Order status transitions (validar transições inválidas)
✗ Customer CRUD completo
✗ Payment workflow
✗ WebSocket connections
✗ Flow engine (11 estados)
✗ WAHA webhook parsing
✗ Asaas webhook handling
```

### 3.2 Testes Frontend 🟠

```
✗ Login flow (sucesso/erro)
✗ CreateOrderPanel (busca CEP, customer, produtos)
✗ PendingOrdersPanel (approve/reject)
✗ OperatorDashboard (estados)
✗ WebSocket listeners
✗ API error handling
```

### 3.3 Documentação 🟡

| Documento | Status | Ação |
|-----------|--------|------|
| README.md | Básico | Expandir com setup completo |
| SETUP_DEV.md | Não existe | Criar guia de desenvolvimento |
| DEPLOYMENT.md | Não existe | Criar guia de deploy |
| ARCHITECTURE.md | Não existe | Documentar arquitetura |
| API.md | Swagger auto | Documentar fluxos de negócio |
| CONTRIBUTING.md | Não existe | Criar guia de contribuição |

### Entregáveis Sprint 3:
- [ ] Coverage backend > 60%
- [ ] Coverage frontend > 40%
- [ ] Documentação completa
- [ ] CI/CD com testes automáticos

**Estimativa:** 40 horas

---

# SPRINT 4: TYPESCRIPT E PERFORMANCE (2 semanas)

## Objetivo: Migrar frontend para TypeScript e otimizar performance

### 4.1 Migração TypeScript 🟡

| Etapa | Arquivos | Estimativa |
|-------|----------|------------|
| Setup tsconfig.json | 1 | 1h |
| Migrar services/ | 3 | 3h |
| Migrar hooks/ | 4 | 4h |
| Migrar components/ | ~20 | 15h |
| Migrar pages/ | ~12 | 8h |

### 4.2 Otimizações Frontend 🟡

| Problema | Solução |
|----------|---------|
| Sem code splitting | Lazy loading de rotas |
| Sem cache de API | Implementar React Query |
| Sem memoization | React.memo, useMemo, useCallback |
| Bundle grande | Tree shaking, compression |

### 4.3 Otimizações Backend 🟡

| Problema | Solução |
|----------|---------|
| N+1 queries | `selectinload` seletivo |
| Uvicorn single worker | Gunicorn com workers |
| Sem circuit breaker | Implementar para integrações |

### Entregáveis Sprint 4:
- [ ] Frontend 100% TypeScript
- [ ] React Query implementado
- [ ] Lazy loading de rotas
- [ ] Performance score > 80 (Lighthouse)
- [ ] Backend com múltiplos workers

**Estimativa:** 30 horas

---

# SPRINT 5: FUNCIONALIDADES INCOMPLETAS (2 semanas)

## Objetivo: Implementar TODOs e funcionalidades faltantes

### 5.1 TODOs em handlers.py 🟠

| Linha | TODO | Prioridade |
|-------|------|------------|
| 229 | Cancelar pedido no banco | ALTA |
| 511 | Gerar QR Code Pix via Asaas | ALTA |
| 640 | Verificar pagamento via Asaas | ALTA |
| 677 | Cancelar pedido | MÉDIA |
| 820 | Buscar pedidos recentes do cliente | MÉDIA |
| 844 | Notificar operador via WebSocket | ALTA |

### 5.2 TODOs em drivers.py 🟠

| Linha | TODO | Prioridade |
|-------|------|------------|
| 184 | Filtrar por bairro do driver | MÉDIA |
| 487-488 | Notificar operador + log evento | ALTA |

### 5.3 TODOs em websocket.py 🟡

| Linha | TODO | Prioridade |
|-------|------|------------|
| 419 | Campos bairro/region no User | MÉDIA |

### 5.4 Integrações Pendentes 🟡

| Integração | Status | Ação |
|------------|--------|------|
| Asaas PIX | Parcial | Completar geração QR |
| Asaas Webhook | Parcial | Implementar retry |
| MinIO | Configurado | Implementar upload |
| Firebird | Configurado | Testar conexão |

### Entregáveis Sprint 5:
- [ ] Todos TODOs implementados
- [ ] PIX funcionando end-to-end
- [ ] MinIO upload funcionando
- [ ] Firebird testado (se necessário)

**Estimativa:** 25 horas

---

# SPRINT 6: INFRAESTRUTURA E DEPLOY (1 semana)

## Objetivo: Preparar para produção

### 6.1 HTTPS e Segurança 🟠

| Tarefa | Ferramenta |
|--------|------------|
| Certificado SSL | Let's Encrypt + Traefik |
| CSRF Protection | FastAPI middleware |
| Rate limiting real | nginx ou Traefik |
| Headers de segurança | Helmet equivalent |

### 6.2 Monitoramento 🟡

| Tarefa | Ferramenta |
|--------|------------|
| Log aggregation | Loki ou ELK |
| Alertas | Grafana alerts |
| APM | Sentry ou similar |
| Health checks | Prometheus |

### 6.3 Backup e Recovery 🟡

| Tarefa | Ferramenta |
|--------|------------|
| Backup PostgreSQL | pg_dump automático |
| Backup Redis | RDB snapshots |
| Disaster recovery | Documentar processo |

### Entregáveis Sprint 6:
- [ ] HTTPS funcionando
- [ ] Monitoramento completo
- [ ] Backups automáticos
- [ ] Runbook de operações

**Estimativa:** 15 horas

---

# CRONOGRAMA RESUMIDO

| Sprint | Foco | Duração | Horas Est. |
|--------|------|---------|------------|
| **1** | Segurança Crítica | 1 semana | 8-12h |
| **2** | Qualidade de Código | 1 semana | 12-16h |
| **3** | Testes e Documentação | 2 semanas | 40h |
| **4** | TypeScript e Performance | 2 semanas | 30h |
| **5** | Funcionalidades Incompletas | 2 semanas | 25h |
| **6** | Infraestrutura e Deploy | 1 semana | 15h |

**Total:** ~9 semanas / ~130-140 horas

---

# CHECKLIST RÁPIDO (< 1 hora)

## Fazer AGORA:
- [ ] Deletar `backend/eric_files/`
- [ ] Deletar `*.old.jsx` e `*.tsx` duplicados
- [ ] Remover `--reload` do docker-compose
- [ ] Adicionar auth em POST/DELETE orders
- [ ] Gerar SECRET_KEY forte

## Fazer HOJE:
- [ ] Converter `print()` para `logger`
- [ ] Corrigir bare excepts
- [ ] Centralizar URLs no frontend
- [ ] Criar `.env.example`
- [ ] Remover `console.log` do frontend

---

# MÉTRICAS DE SUCESSO

| Métrica | Atual | Meta Sprint 3 | Meta Final |
|---------|-------|---------------|------------|
| Test Coverage Backend | 15% | 60% | 80% |
| Test Coverage Frontend | 0% | 40% | 70% |
| Vulnerabilidades Críticas | 15 | 0 | 0 |
| Vulnerabilidades Altas | 25 | 5 | 0 |
| Lighthouse Performance | ? | 70 | 90 |
| Pontuação Geral | 6.5/10 | 7.5/10 | 9/10 |

---

**Documento gerado em:** 21/01/2026
**Próxima revisão:** Após Sprint 1
