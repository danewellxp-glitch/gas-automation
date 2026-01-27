# 📋 Plano de Migração: TSX → JSX com Funcionalidades Completas

## 🎯 Objetivo
Integrar todas as funcionalidades dos arquivos TSX originais nos JSX atuais, mantendo a autenticação implementada.

---

## 📊 Status Atual

### OperatorDashboard
**TSX (Completo):** 1440 linhas
- ✅ WebSocket com reconexão automática
- ✅ Gerenciamento de conversas (minhas + todas)
- ✅ Chat com mensagens em tempo real
- ✅ Carregamento de pedidos
- ✅ Interações do bot
- ✅ Notificações (som + navegador + toast)
- ✅ Encerramento de conversas
- ✅ Filtros de conversa

**JSX (Básico):** 116 linhas
- ⚠️ Apenas layout e busca de conversas
- ⚠️ Sem chat
- ⚠️ Sem pedidos
- ⚠️ Sem WebSocket

**GAP:** ~1300 linhas de funcionalidade faltando

---

### OwnerDashboard
**TSX (Completo):** 583 linhas
- ✅ Gráficos de vendas (Chart.js)
- ✅ Carregamento de métricas
- ✅ Atividades recentes
- ✅ Top produtos
- ✅ Configurações de negócio
- ✅ Dashboard com estatísticas

**JSX (Básico):** 121 linhas
- ⚠️ Apenas cartões de estatísticas
- ⚠️ Sem gráficos
- ⚠️ Sem configurações
- ⚠️ Sem atividades

**GAP:** ~460 linhas de funcionalidade faltando

---

### AdminDashboard
**TSX (Completo):** 611 linhas
- ✅ Mapa com Leaflet
- ✅ Gerenciamento de pedidos (tabs)
- ✅ Chat de conversas
- ✅ WebSocket
- ✅ Stats e filtros

**JSX (Básico):** 407 linhas
- ✅ Gerenciamento de roles (NOVO)
- ✅ Busca e ordenação
- ⚠️ Sem mapa
- ⚠️ Sem gerenciamento de pedidos
- ⚠️ Sem chat

**STATUS:** Parcialmente mantido (roles) + perdeu pedidos/conversas

---

## 🔧 Migração por Prioridade

### Prioridade 1: OperatorDashboard (Alta - Principal)
Operador é o usuário mais ativo do sistema

#### Funcionalidades a Implementar:
1. **WebSocket com Reconexão**
   - Conectar/desconectar
   - Tratamento de erros
   - Tentativas de reconexão automática
   - Listeners: new_order, order_update, messages

2. **Chat Completo**
   - Carregar mensagens da conversa
   - Enviar mensagens em tempo real
   - Scroll automático
   - Identificar sender (cliente/bot/agente)

3. **Pedidos**
   - Carregar lista de pedidos
   - Modal/painel de pedidos
   - Notificações de novos pedidos
   - Som + Navegador + Toast

4. **Conversas Avançadas**
   - Minhas conversas (atribuídas)
   - Todas conversas (disponíveis)
   - Filtros (todas/bot_only)
   - Atribuir conversa
   - Encerrar conversa

5. **Interações Bot**
   - Listar interações do bot
   - Mostrar respostas bot

---

### Prioridade 2: OwnerDashboard (Média)
Proprietário precisa de visão executiva

#### Funcionalidades a Implementar:
1. **Gráficos**
   - Instalar Chart.js
   - Gráfico de vendas (linha)
   - Gráfico de status de pedidos (rosca)

2. **Métricas Dinâmicas**
   - Receita do dia
   - Pedidos do dia
   - Novos clientes
   - Rating médio
   - Variações (% vs mês anterior)

3. **Atividades**
   - Timeline de atividades recentes
   - Tipos: user_login, order_placed, payment_received, etc

4. **Top Produtos**
   - Produtos mais vendidos
   - Ranking por receita

5. **Configurações**
   - Horário de funcionamento
   - Taxa de entrega
   - Pedido mínimo
   - Auto-aceitar pedidos

---

### Prioridade 3: AdminDashboard (Média)
Admin precisa gerenciar sistema + users

#### Funcionalidades a Implementar:
1. **Mapa de Entregas** (Leaflet)
   - Mostrar posições dos pedidos
   - Cluster de pedidos

2. **Gerenciamento de Pedidos**
   - Lista com tabs (hoje/pendentes/todos)
   - Filtros por status
   - Atualizar status

3. **Chat de Conversas**
   - Carregar conversa completa
   - Enviar mensagem

4. **WebSocket**
   - Atualizar orders em tempo real
   - Atualizar conversations em tempo real

---

## 📦 Dependências Necessárias

```bash
# Já instaladas
- react
- react-router-dom
- tailwindcss

# Precisa instalar
npm install chart.js react-chartjs-2
npm install leaflet
```

---

## 📝 Estrutura de Migração

### Padrão para OperatorDashboard:

```jsx
import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { apiRequest } from '../../utils/api'

export default function OperatorDashboard() {
  const { user, logout } = useAuth()
  
  // Estados para conversas
  const [myConversations, setMyConversations] = useState([])
  const [allConversations, setAllConversations] = useState([])
  const [chatMessages, setChatMessages] = useState([])
  
  // Estados para pedidos
  const [orders, setOrders] = useState([])
  
  // Estados para UI
  const [notification, setNotification] = useState(null)
  
  // Refs para WebSocket e controle
  const wsRef = useRef(null)
  const currentConversationIdRef = useRef(null)
  
  // WebSocket connection
  const connectWebSocket = useCallback(async () => {
    // ... implementação
  }, [])
  
  // Load conversas
  const fetchMyConversations = useCallback(async () => {
    // ... implementação
  }, [])
  
  // Load chat
  const loadChat = useCallback(async (conversationId) => {
    // ... implementação
  }, [])
  
  // Send message
  const sendMessage = useCallback(async () => {
    // ... implementação
  }, [])
  
  // Load orders
  const loadOrders = useCallback(async () => {
    // ... implementação
  }, [])
  
  // ... rest of component
}
```

---

## 🚀 Próximas Etapas

1. **Escolher qual painel migrar primeiro**
   - Recomendado: OperatorDashboard (mais crítico)

2. **Extrair funções do TSX**
   - WebSocket
   - Load data
   - Enviar mensagens
   - Tratamento de erros

3. **Adaptar para React Hooks + JSX**
   - Converter para useState/useCallback
   - Manter autenticação do novo código
   - Usar adminHelpers para formatação

4. **Testar funcionalidades**
   - Seguir guia em GUIA_TESTES_ROLES.md
   - Adicionar testes para novas funcionalidades

5. **Commit e documentar**
   - Descrever mudanças
   - Atualizar documentação

---

## 💾 Arquivo de Referência

Mantenha os TSX originais como referência enquanto migra:
- `/frontend/src/pages/operator/OperatorDashboard.tsx` → Referência
- `/frontend/src/pages/operator/OperatorDashboard.jsx` → Alvo de migração
- Idem para Owner e Admin

---

## ⚠️ Pontos de Atenção

1. **WebSocket URL**
   - Precisa estar correto: `/ws?token=...`
   - Usar `window.location.host` para obter domain

2. **CORS/Autenticação**
   - Usar token do localStorage
   - Headers: `Authorization: Bearer token`

3. **Performance**
   - Mensagens do chat podem ficar muitas
   - Considerar paginação/virtualização depois

4. **Estilo**
   - CSS original está em arquivos `.css`
   - Adaptar para Tailwind ou deixar CSS importado

---

## 📋 Checklist de Migração

### OperatorDashboard
- [ ] WebSocket conectando
- [ ] Minhas conversas carregando
- [ ] Todas conversas carregando
- [ ] Chat abrindo e carregando mensagens
- [ ] Envio de mensagem funcionando
- [ ] Pedidos carregando
- [ ] Notificação de novo pedido
- [ ] Encerramento de conversa
- [ ] Filtros funcionando
- [ ] Logout funcionando

### OwnerDashboard
- [ ] Chart.js instalado
- [ ] Gráficos renderizando
- [ ] Métricas carregando
- [ ] Atividades mostradas
- [ ] Top produtos listados
- [ ] Configurações funcionando

### AdminDashboard
- [ ] Mapa renderizando (Leaflet)
- [ ] Pedidos em abas
- [ ] Chat de conversa
- [ ] WebSocket atualizando

---

**Status:** Pronto para iniciar migração
**Recomendação:** Começar com OperatorDashboard (complexo mas crítico)

