# Planejamento de Integração do Backend (Sem Services, Models e main.py)

## 📋 Resumo Executivo
Integração de toda infraestrutura, configurações, APIs e utilitários do backend, mantendo separado:
- ❌ `app/services/` - Será integrado posteriormente
- ❌ `app/models/` - Será integrado posteriormente  
- ❌ `app/main.py` - Será integrado posteriormente

---

## 🏗️ Estrutura de Integração

### **FASE 1: Configuração e Infraestrutura**

#### 1.1 - Dependências do Projeto
**Arquivo:** `requirements.txt`
**Tarefas:**
- [ ] Copiar `requirements.txt` para raiz do projeto consolidado
- [ ] Avaliar dependências que já existem em `vamos usar/`
- [ ] Mesclar e remover duplicatas
- [ ] Validar compatibilidade de versões

**Dependências Principais:**
- FastAPI 0.109.2 + Uvicorn
- SQLAlchemy 2.0.25 + asyncpg (PostgreSQL)
- Redis 5.0.1 (AsyncIO)
- Pydantic 2.7+
- MinIO 7.2.3
- Integrações: WAHA, Asaas, Ollama, Firebird
- Ferramentas: pytest, pandas, Pillow, opencv

---

#### 1.2 - Configurações Centralizadas
**Arquivo:** `app/config.py`
**Tarefas:**
- [ ] Integrar arquivo `config.py` (114 linhas)
- [ ] Comparar com `vamos usar/config.py`
- [ ] Consolidar todas as variáveis de ambiente
- [ ] Criar arquivo `.env.example` com todas as variáveis necessárias

**Configurações Gerenciadas:**
- Aplicação (debug, environment, secret_key)
- PostgreSQL (database_url, echo)
- Redis (url, TTL)
- Integrações Externas:
  - WAHA (WhatsApp API)
  - Asaas (Pagamentos)
  - Ollama (IA Local)
  - Firebird (Sistema Legado)
  - MinIO (Object Storage)

---

#### 1.3 - Banco de Dados
**Arquivos:** 
- `app/database.py` (188 linhas)
- `alembic/` (configuração de migrations)
- `init_db.sql`

**Tarefas:**
- [ ] Integrar `database.py` com:
  - Engine SQLAlchemy assíncrono
  - AsyncSessionLocal factory
  - Base declarative para modelos
  - Dependency `get_db()` para FastAPI
  - Gerenciamento de conexão Redis
- [ ] Configurar Alembic para migrations automáticas
- [ ] Integrar `init_db.sql` para inicialização
- [ ] Validar pool de conexões (pool_size=10, max_overflow=20)

**Saída Esperada:**
- PostgreSQL configurado com asyncpg
- Redis inicializado
- Migrations prontas

---

### **FASE 2: Core da Aplicação**

#### 2.1 - Core/Business Logic
**Pasta:** `app/core/`
**Arquivos:**
- [ ] `business_rules.py` - Regras de negócio
- [ ] `flow_engine.py` - Motor de fluxos
- [ ] `handlers.py` - Manipuladores de eventos
- [ ] `state_machine.py` - Máquina de estados

**Tarefas:**
- [ ] Analisar dependências com `models/` e `services/`
- [ ] Isolar lógica pura que não depende de services
- [ ] Manter referências às classes que serão importadas depois
- [ ] Documentar pontos de integração

---

#### 2.2 - Schemas (Validação de Dados)
**Pasta:** `app/schemas/`
**Arquivos:**
- [ ] `base.py` - Schema base
- [ ] `customer.py` - Schema de cliente
- [ ] `order.py` - Schema de pedido
- [ ] `product.py` - Schema de produto
- [ ] `payment.py` - Schema de pagamento
- [ ] `webhook.py` - Schema de webhook

**Tarefas:**
- [ ] Integrar todos os schemas Pydantic
- [ ] Remover dependências de modelos se houver (usar forward references)
- [ ] Validar validadores customizados
- [ ] Documentar tipos de dados esperados

---

#### 2.3 - Autenticação
**Arquivo:** `app/auth.py`
**Tarefas:**
- [ ] Integrar autenticação JWT
- [ ] Integrar hashing de senhas (passlib + argon2)
- [ ] Configurar middleware de auth
- [ ] Documentar fluxo de autenticação
- [ ] Validar compatibilidade com RBAC (se houver)

---

### **FASE 3: Integrações Externas**

#### 3.1 - Clientes de API/Serviços
**Pasta:** `app/integrations/`
**Arquivos a Integrar:**

| Arquivo | Serviço | Status |
|---------|---------|--------|
| `asaas.py` | Gateway de Pagamento | Ativo |
| `firebird.py` | Database Legado | Ativo |
| `minio_client.py` | Object Storage | Ativo |
| `ollama.py` | IA Local | Ativo |
| `waha.py` | WhatsApp HTTP API | Ativo |

**Tarefas por Integração:**
- [ ] Validar credenciais no `config.py`
- [ ] Testar conexão com cada serviço
- [ ] Documentar limites de rate limiting
- [ ] Implementar retry logic e timeout
- [ ] Adicionar logging detalhado

**ASAAS (Pagamentos):**
- [ ] Cliente HTTP assíncrono
- [ ] Métodos: criar cobrança, webhook de pagamento
- [ ] Tratamento de erros específicos

**Firebird:**
- [ ] Conexão assíncrona (fdb)
- [ ] Queries mapeadas
- [ ] Migration path para PostgreSQL

**MinIO:**
- [ ] Upload/Download de arquivos
- [ ] Gerenciamento de buckets
- [ ] Assinatura de URLs

**Ollama:**
- [ ] Client HTTP assíncrono
- [ ] Chamadas de IA local
- [ ] Cache de respostas (Redis)
- [ ] Fallback para embeddings

**WAHA:**
- [ ] Cliente HTTP assíncrono
- [ ] Envio de mensagens
- [ ] Webhook receiver
- [ ] Session management

---

### **FASE 4: APIs/Rotas**

#### 4.1 - Endpoints REST
**Pasta:** `app/api/`
**Arquivos:**

| Arquivo | Recurso | Endpoints |
|---------|---------|-----------|
| `auth.py` | Autenticação | POST /auth/login, /auth/register |
| `users.py` | Usuários | GET/POST/PUT/DELETE /users |
| `customers.py` | Clientes | GET/POST/PUT/DELETE /customers |
| `products.py` | Produtos | GET/POST/PUT/DELETE /products |
| `orders.py` | Pedidos | GET/POST/PUT/DELETE /orders |
| `chats.py` | Conversas | GET/POST /chats |
| `chatbot.py` | Chatbot | POST /chatbot/message |
| `images.py` | Imagens | POST /images/upload, /images/analyze |
| `webhooks.py` | Webhooks | POST /webhooks/* |
| `websocket.py` | WebSocket | WS /ws |
| `test_flow.py` | Testes | GET /test/* |

**Tarefas:**
- [ ] Integrar cada rota mantendo dependências
- [ ] Validar imports (especialmente models e services)
- [ ] Isolar mocks necessários para services ausentes
- [ ] Documentar contratos de API
- [ ] Adicionar tipos de retorno

**Pontos de Atenção:**
- `websocket.py` - Pode ter dependências de services
- `chatbot.py` - Usa Ollama integration
- `webhooks.py` - Recebe eventos de integrações
- `images.py` - Usa MinIO e OCR

---

### **FASE 5: Utilitários e Helpers**

#### 5.1 - Métricas e Monitoring
**Arquivo:** `app/metrics.py`
**Tarefas:**
- [ ] Integrar sistema de métricas
- [ ] Configurar exportação para Prometheus
- [ ] Definir KPIs: requisições, erros, latência
- [ ] Adicionar instrumentação

#### 5.2 - Workers/Tarefas Assíncronas
**Pasta:** `app/workers/`
**Status:** Estrutura vazia, pronta para expansão
**Tarefas:**
- [ ] Preparar para celery/RQ
- [ ] Documentar padrão de workers

---

### **FASE 6: Testes**

#### 6.1 - Suite de Testes
**Pasta:** `tests/`
**Arquivos:**
- [ ] `conftest.py` - Fixtures compartilhadas
- [ ] `test_api.py` - Testes de API
- [ ] `test_flow_engine.py` - Testes de lógica
- [ ] `test_load.py` - Testes de carga
- [ ] `test_integrations/` - Testes de integrações

**Tarefas:**
- [ ] Manter testes atualizados com código
- [ ] Preparar testes para CI/CD
- [ ] Documentar como rodar testes localmente

**Comando:**
```bash
pytest --asyncio-mode=auto
```

---

### **FASE 7: Banco de Dados & Migrations**

#### 7.1 - Setup Inicial
**Arquivos:**
- `alembic.ini` - Configuração Alembic
- `alembic/env.py` - Ambiente de migration
- `init_db.sql` - Script de inicialização
- `alembic/versions/` - Histórico de migrations

**Tarefas:**
- [ ] Importar configuração Alembic existente
- [ ] Manter histórico de migrations
- [ ] Documentar processo de migration

**Comandos:**
```bash
# Criar nova migration
alembic revision --autogenerate -m "descrição"

# Aplicar migrations
alembic upgrade head
```

---

### **FASE 8: Utilitários & Scripts**

#### 8.1 - Scripts de Inicialização
**Arquivos Root:**
- [ ] `create_tables.py` - Criação de tabelas
- [ ] `create_test_user.py` - Usuário de teste
- [ ] `create_test_user_direct.py` - Alternativa direta
- [ ] `create_user.py` - Criação genérica

**Tarefas:**
- [ ] Integrar ou consolidar scripts
- [ ] Criar CLI unificada
- [ ] Documentar uso

#### 8.2 - Dockerfile & Composição
**Arquivos:**
- [ ] `Dockerfile` - Image Docker backend
- [ ] `docker-compose.yml` - Orquestração (já na raiz)

**Tarefas:**
- [ ] Validar Dockerfile
- [ ] Atualizar docker-compose.yml se necessário
- [ ] Documentar variáveis de ambiente

---

### **FASE 9: Arquivos Legados**

#### 9.1 - Eric Files (Referência)
**Pasta:** `eric_files/`
**Status:** Manter como referência
**Arquivos:**
- Modelos antigos
- Serviços antigos
- Autenticação anterior

**Tarefas:**
- [ ] Documentar quais foram migrados
- [ ] Quais foram descontinuados
- [ ] Paths de migração

---

## 📊 Matriz de Dependências

```
config.py ←── settings globais
    ↓
database.py ←── conexões (PostgreSQL + Redis)
    ↓
├─→ app/core/ ←── business logic
├─→ app/integrations/ ←── externos
├─→ app/schemas/ ←── validação
├─→ app/auth.py ←── autenticação
└─→ app/api/ ←── rotas REST + WebSocket
    │
    └─→ app/services/ [FASE 2] ← lógica de domínio
        └─→ app/models/ [FASE 2] ← entidades
```

---

## 🎯 Ordem de Integração Recomendada

### ✅ Pronto para Integrar Agora:
1. **requirements.txt** - Dependências
2. **config.py** - Configurações
3. **database.py** - Conexões DB
4. **alembic/** - Migrations
5. **app/schemas/** - Validação
6. **app/auth.py** - Autenticação
7. **app/integrations/** - Clientes externos
8. **app/core/** - Lógica central
9. **app/metrics.py** - Monitoramento

### 🔄 Próximas Fases:
10. **app/api/** - Endpoints (com mocks para services)
11. **tests/** - Suite de testes
12. **app/models/** - [FASE 2]
13. **app/services/** - [FASE 2]
14. **app/main.py** - [FASE 2]

---

## 📦 Checklist de Integração

### Infrastructure & Config
- [ ] `requirements.txt` consolidado
- [ ] `config.py` ativo e testado
- [ ] Variáveis de ambiente documentadas
- [ ] `.env.example` criado

### Database Layer
- [ ] PostgreSQL conectando
- [ ] Redis ativo
- [ ] Alembic funcionando
- [ ] Migrations aplicadas

### Core Modules
- [ ] `app/core/` sem erros
- [ ] `app/schemas/` validando
- [ ] `app/auth.py` funcionando
- [ ] `app/integrations/` testado

### APIs
- [ ] Rotas documentadas
- [ ] Endpoints funcionando
- [ ] WebSocket pronto
- [ ] Erros tratados

### Quality
- [ ] Testes passando
- [ ] Linter sem warnings
- [ ] Docker buildável
- [ ] Deploy pronto

---

## 📝 Saídas Esperadas

### Documentação
- [ ] API OpenAPI/Swagger
- [ ] Guia de configuração
- [ ] Guia de deployment
- [ ] Arquitetura visual

### Artefatos
- [ ] `requirements.txt` final
- [ ] `.env.example` completo
- [ ] `Dockerfile` validado
- [ ] `docker-compose.yml` atualizado

### Código
- [ ] Integração completa
- [ ] Sem dependências circulares
- [ ] Testes verdes
- [ ] Pronto para main.py

---

## 🚀 Métricas de Sucesso

✅ Todo código integrado sem erros de import  
✅ Todos os testes passando  
✅ Banco de dados rodando  
✅ Integrações externas testadas  
✅ Documentação completa  
✅ Pronto para próxima fase (services + models)

---

## 📞 Próximos Passos

1. Confirmar ordem de integração
2. Iniciar **FASE 1** (Config & Infrastructure)
3. Validar cada fase antes de prosseguir
4. Documentar problemas encontrados
5. Ajustar conforme necessário

