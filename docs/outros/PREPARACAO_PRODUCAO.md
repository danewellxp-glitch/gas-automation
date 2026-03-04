# 🚀 Preparação para Produção - Remoção de Dados Fake

## 📋 Análise Completa - Dados Fake/Mock Identificados

### 🔴 **CRÍTICO - Remover Imediatamente**

#### 1. **Backend - Estimativas Fake em Estatísticas**
**Arquivo:** `backend/app/main.py`
- **Linha 429:** `total_messages = total_conversations * 5` ❌ ESTIMATIVA FAKE
- **Linha 434:** `messages_today = total_messages // 30` ❌ ESTIMATIVA FAKE
- **Ação:** Buscar mensagens reais da tabela `message`

#### 2. **Backend - Endpoints de Teste Sem Autenticação**
**Arquivo:** `backend/app/api/chatbot.py`
- **Linha 58-80:** `/api/chatbot/test` ❌ SEM AUTENTICAÇÃO
- **Ação:** Remover ou proteger com autenticação

**Arquivo:** `backend/app/api/test_flow.py`
- **Endpoints:** `/simulate-message`, `/context/{phone}`, `/flow-states`
- **Ação:** Remover ou mover para ambiente de desenvolvimento apenas

#### 3. **Frontend - Função de Teste**
**Arquivo:** `frontend/src/services/api.js`
- **Linha 213-216:** `createTestConversation` ❌ FUNÇÃO DE TESTE
- **Ação:** Remover

#### 4. **Backend - Dados Default de Produtos**
**Arquivo:** `backend/app/models/product.py`
- **Linha 98-123:** `DEFAULT_PRODUCTS` ❌ DADOS HARDCODED
- **Ação:** Remover - produtos devem vir apenas do Firebird

#### 5. **Inventory Service - Dados Mock**
**Arquivo:** `backend/services/inventory-service/app/api/inventory.py`
- **Linha 113-156:** `PRODUCTS_DB` ❌ DADOS EM MEMÓRIA
- **Ação:** Migrar para PostgreSQL ou remover se não usado

---

### 🟡 **MÉDIO - Verificar e Ajustar**

#### 6. **Frontend - URLs Hardcoded**
**Arquivo:** `frontend/src/components/operator/OperatorDashboardOverview.jsx`
- **Linha 25-30:** URLs hardcoded `http://192.168.10.167:8000`
- **Ação:** Usar variável de ambiente ou api.js

#### 7. **Frontend - URLs Hardcoded**
**Arquivo:** `frontend/src/components/admin/DashboardOverview.jsx`
- **Linha 25-33:** URLs hardcoded `http://192.168.10.167:8000`
- **Ação:** Usar variável de ambiente ou api.js

---

## ✅ Plano de Ação

### Fase 1: Remover Dados Fake do Backend
- [ ] Corrigir estimativas de mensagens em `main.py`
- [ ] Remover/proteger endpoints de teste
- [ ] Remover DEFAULT_PRODUCTS
- [ ] Verificar inventory-service

### Fase 2: Remover Dados Fake do Frontend
- [ ] Remover `createTestConversation`
- [ ] Corrigir URLs hardcoded
- [ ] Verificar todos os componentes

### Fase 3: Garantir Dados Reais
- [ ] Verificar que produtos vêm do Firebird
- [ ] Verificar que clientes vêm do Firebird/PostgreSQL
- [ ] Verificar que pedidos vêm do PostgreSQL
- [ ] Testar todos os dashboards

### Fase 4: Testes Finais
- [ ] Testar Dashboard Operador
- [ ] Testar Dashboard Admin
- [ ] Testar Dashboard Owner
- [ ] Testar Dashboard Driver

---

## 🎯 Objetivo Final

**Todos os dados devem vir de:**
- ✅ **Firebird (Gerente.fdb)** - Produtos, Clientes, Estoque, Rotas, Veículos
- ✅ **PostgreSQL** - Pedidos, Usuários, Conversas, Mensagens, Entregas
- ❌ **NENHUM dado fake, mock ou hardcoded**
