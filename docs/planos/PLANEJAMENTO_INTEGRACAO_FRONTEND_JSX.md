# 📋 Planejamento de Integração Backend → Frontend JSX

## 🎯 Objetivo
Conectar os endpoints e schemas do backend FastAPI com componentes React/JSX, criando uma interface unificada e responsiva.

---

## 📊 Diagnóstico Atual

### Backend (✅ 73% Pronto)
- **Framework:** FastAPI 0.115.0
- **Autenticação:** JWT + Argon2
- **Banco de Dados:** PostgreSQL + Redis
- **Integrações:** ASAAS, WAHA, Firebird, MinIO, Ollama
- **Endpoints:** 13 arquivos de rotas REST + WebSocket

### Frontend (🟡 Estrutura Básica)
- **Framework:** React 18.2.0
- **Build Tool:** Vite 5.0.0
- **HTTP Client:** Axios 1.6.0
- **Estilo:** TailwindCSS 3.3.5
- **Router:** React Router 6.20.0
- **Status:** Estrutura criada, precisa integração com backend

---

## 🏗️ Arquitetura de Integração

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React/JSX)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Components/Pages                  Services/Hooks             │
│  ├── Login                    →    ├── authService.js        │
│  ├── Dashboard               →    ├── customerService.js     │
│  ├── Orders                  →    ├── orderService.js        │
│  ├── Customers               →    ├── driverService.js       │
│  ├── Products                →    ├── useAuth.js             │
│  ├── Drivers                 →    ├── useFetch.js            │
│  └── ChatBot                 →    └── useWebSocket.js        │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                          API Client Layer                     │
│                    (axios + interceptors)                     │
├─────────────────────────────────────────────────────────────┤
│                     HTTP/WebSocket Bridge                     │
│              (http://localhost:8000 - CORS enabled)          │
├─────────────────────────────────────────────────────────────┤
│                      BACKEND (FastAPI)                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  API Routes                       Services                    │
│  ├── /api/auth               →    ├── authService           │
│  ├── /api/customers          →    ├── customerService       │
│  ├── /api/orders             →    ├── orderService          │
│  ├── /api/drivers            →    ├── driverService         │
│  ├── /api/products           →    ├── productService        │
│  ├── /api/webhooks           →    ├── webhookService        │
│  ├── /api/chatbot            →    └── chatbotService        │
│  └── /ws                                                      │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                    Database & Cache Layer                     │
│              (PostgreSQL + Redis + Integrations)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Estrutura de Pastas Proposta

### Frontend - Nova Estrutura

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.js                 # Configuração Axios
│   │   ├── endpoints.js              # URLs centralizadas
│   │   └── interceptors.js           # Auth + Error handling
│   │
│   ├── services/
│   │   ├── authService.js            # Login, Register, Logout
│   │   ├── customerService.js        # CRUD Customers
│   │   ├── orderService.js           # CRUD Orders
│   │   ├── driverService.js          # CRUD Drivers
│   │   ├── productService.js         # CRUD Products
│   │   ├── webhookService.js         # Webhook handlers
│   │   └── chatbotService.js         # Chat operations
│   │
│   ├── hooks/
│   │   ├── useAuth.js                # Auth state + methods
│   │   ├── useFetch.js               # Generic data fetching
│   │   ├── useWebSocket.js           # WebSocket connection
│   │   ├── useForm.js                # Form handling
│   │   └── useNotification.js        # Toast/alerts
│   │
│   ├── context/
│   │   ├── AuthContext.jsx           # Global auth state
│   │   ├── DataContext.jsx           # Global data state
│   │   └── WebSocketContext.jsx      # Global WS state
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── Header.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Footer.jsx
│   │   │   ├── Card.jsx
│   │   │   ├── Button.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── Loader.jsx
│   │   │   └── Notification.jsx
│   │   │
│   │   ├── auth/
│   │   │   ├── LoginForm.jsx
│   │   │   ├── RegisterForm.jsx
│   │   │   └── ForgotPassword.jsx
│   │   │
│   │   ├── dashboard/
│   │   │   ├── DashboardHome.jsx
│   │   │   ├── OrderStats.jsx
│   │   │   ├── DriverStats.jsx
│   │   │   ├── RevenueChart.jsx
│   │   │   └── RecentOrders.jsx
│   │   │
│   │   ├── customers/
│   │   │   ├── CustomerList.jsx
│   │   │   ├── CustomerForm.jsx
│   │   │   ├── CustomerDetail.jsx
│   │   │   └── CustomerMap.jsx
│   │   │
│   │   ├── orders/
│   │   │   ├── OrderList.jsx
│   │   │   ├── OrderForm.jsx
│   │   │   ├── OrderDetail.jsx
│   │   │   ├── OrderTimeline.jsx
│   │   │   └── OrderMap.jsx
│   │   │
│   │   ├── drivers/
│   │   │   ├── DriverList.jsx
│   │   │   ├── DriverForm.jsx
│   │   │   ├── DriverDetail.jsx
│   │   │   ├── DriverTracking.jsx
│   │   │   └── DriverStats.jsx
│   │   │
│   │   ├── products/
│   │   │   ├── ProductList.jsx
│   │   │   ├── ProductForm.jsx
│   │   │   └── ProductDetail.jsx
│   │   │
│   │   └── chat/
│   │       ├── ChatBot.jsx
│   │       ├── ChatMessage.jsx
│   │       ├── ChatInput.jsx
│   │       └── ChatHistory.jsx
│   │
│   ├── pages/
│   │   ├── LoginPage.jsx
│   │   ├── DashboardPage.jsx
│   │   ├── CustomersPage.jsx
│   │   ├── OrdersPage.jsx
│   │   ├── DriversPage.jsx
│   │   ├── ProductsPage.jsx
│   │   ├── ChatPage.jsx
│   │   ├── SettingsPage.jsx
│   │   └── NotFoundPage.jsx
│   │
│   ├── utils/
│   │   ├── constants.js              # Constantes globais
│   │   ├── formatters.js             # Formatação de dados
│   │   ├── validators.js             # Validação de forms
│   │   ├── helpers.js                # Funções utilitárias
│   │   └── localStorage.js           # Storage management
│   │
│   ├── styles/
│   │   ├── globals.css
│   │   ├── components.css
│   │   └── animations.css
│   │
│   ├── App.jsx                       # Root component
│   ├── Router.jsx                    # Route definitions
│   └── main.jsx                      # Entry point
│
├── index.html
├── vite.config.js
├── tailwind.config.js
├── tsconfig.json
├── package.json
└── .env                              # Environment variables

```

---

## 🔌 Guia de Integração por Módulo

### 1️⃣ **AUTENTICAÇÃO & SEGURANÇA**

#### Backend (Já Pronto)
```python
# GET/POST /api/auth/login
# POST /api/auth/register
# POST /api/auth/logout
# POST /api/auth/refresh-token
# GET /api/auth/me
```

#### Frontend - Implementação

**arquivo:** `src/services/authService.js`
```javascript
import apiClient from '../api/client';

export const authService = {
  login: (email, password) => 
    apiClient.post('/auth/login', { email, password }),
  
  register: (userData) => 
    apiClient.post('/auth/register', userData),
  
  logout: () => 
    apiClient.post('/auth/logout'),
  
  getCurrentUser: () => 
    apiClient.get('/auth/me'),
  
  refreshToken: () => 
    apiClient.post('/auth/refresh-token'),
};
```

**arquivo:** `src/hooks/useAuth.js`
```javascript
import { useContext, useCallback } from 'react';
import { AuthContext } from '../context/AuthContext';

export const useAuth = () => {
  const { user, token, login, logout, isLoading } = useContext(AuthContext);
  
  return {
    user,
    token,
    isAuthenticated: !!token,
    login: useCallback(login, []),
    logout: useCallback(logout, []),
    isLoading,
  };
};
```

**arquivo:** `src/context/AuthContext.jsx`
```javascript
import { createContext, useState, useCallback } from 'react';
import { authService } from '../services/authService';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState(false);

  const login = useCallback(async (email, password) => {
    setIsLoading(true);
    try {
      const { data } = await authService.login(email, password);
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('token', data.access_token);
      return data;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    authService.logout().catch(() => {});
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};
```

---

### 2️⃣ **GESTÃO DE PEDIDOS (ORDERS)**

#### Backend (Já Pronto)
```python
# GET /api/orders                  # Listar todos
# POST /api/orders                 # Criar novo
# GET /api/orders/{id}             # Obter detalhe
# PUT /api/orders/{id}             # Atualizar
# DELETE /api/orders/{id}          # Deletar
# PATCH /api/orders/{id}/status    # Mudar status
# GET /api/orders/{id}/timeline    # Histórico
```

#### Frontend - Componentes

**arquivo:** `src/pages/OrdersPage.jsx`
```jsx
import { useState, useEffect } from 'react';
import OrderList from '../components/orders/OrderList';
import OrderForm from '../components/orders/OrderForm';
import { orderService } from '../services/orderService';

export default function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async () => {
    try {
      const { data } = await orderService.getAll();
      setOrders(data);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (formData) => {
    const { data } = await orderService.create(formData);
    setOrders([...orders, data]);
    setShowForm(false);
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Pedidos</h1>
      <button onClick={() => setShowForm(true)}>+ Novo Pedido</button>
      
      {showForm && <OrderForm onSubmit={handleCreate} />}
      <OrderList orders={orders} loading={loading} />
    </div>
  );
}
```

---

### 3️⃣ **GESTÃO DE CLIENTES (CUSTOMERS)**

#### Backend (Já Pronto)
```python
# GET /api/customers              # Listar
# POST /api/customers             # Criar
# GET /api/customers/{id}         # Detalhe
# PUT /api/customers/{id}         # Atualizar
# DELETE /api/customers/{id}      # Deletar
# GET /api/customers/{id}/orders  # Pedidos do cliente
```

#### Frontend - Componentes

**arquivo:** `src/pages/CustomersPage.jsx`
```jsx
import { useState, useEffect } from 'react';
import CustomerList from '../components/customers/CustomerList';
import CustomerMap from '../components/customers/CustomerMap';

export default function CustomersPage() {
  const [customers, setCustomers] = useState([]);
  const [mapView, setMapView] = useState(false);

  // Similar ao exemplo OrdersPage
  
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Clientes</h1>
      <button onClick={() => setMapView(!mapView)}>
        {mapView ? 'Lista' : 'Mapa'}
      </button>
      
      {mapView ? 
        <CustomerMap customers={customers} /> : 
        <CustomerList customers={customers} />
      }
    </div>
  );
}
```

---

### 4️⃣ **RASTREAMENTO DE ENTREGADORES (DRIVERS)**

#### Backend (Já Pronto)
```python
# GET /api/drivers                # Listar
# POST /api/drivers               # Criar
# GET /api/drivers/{id}           # Detalhe
# PUT /api/drivers/{id}           # Atualizar
# GET /api/drivers/{id}/location  # Localização em tempo real
# POST /api/drivers/{id}/online   # Ir online
# POST /api/drivers/{id}/offline  # Ir offline
```

#### Frontend - Componentes com WebSocket

**arquivo:** `src/components/drivers/DriverTracking.jsx`
```jsx
import { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

export default function DriverTracking({ driverId }) {
  const ws = useWebSocket(`/ws/drivers/${driverId}/location`);
  const [location, setLocation] = useState(null);

  useEffect(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.onmessage = (event) => {
        setLocation(JSON.parse(event.data));
      };
    }
  }, [ws]);

  return (
    <div>
      {location && (
        <div>
          <p>Latitude: {location.lat}</p>
          <p>Longitude: {location.lng}</p>
          <p>Velocidade: {location.speed} km/h</p>
        </div>
      )}
    </div>
  );
}
```

---

### 5️⃣ **DASHBOARD EXECUTIVO**

#### Backend (Já Pronto)
```python
# GET /api/dashboard/stats        # Estatísticas gerais
# GET /api/dashboard/charts       # Dados para gráficos
# GET /api/dashboard/alerts       # Alertas ativos
```

#### Frontend - Visualizações

**arquivo:** `src/pages/DashboardPage.jsx`
```jsx
import DashboardStats from '../components/dashboard/OrderStats';
import RevenueChart from '../components/dashboard/RevenueChart';
import RecentOrders from '../components/dashboard/RecentOrders';

export default function DashboardPage() {
  return (
    <div className="p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
      <DashboardStats />
      <RevenueChart />
      <RecentOrders />
    </div>
  );
}
```

---

### 6️⃣ **CHATBOT COM IA (OLLAMA)**

#### Backend (Já Pronto)
```python
# POST /api/chatbot/message       # Enviar mensagem
# GET /api/chatbot/history        # Histórico
# POST /api/chatbot/clear         # Limpar conversa
# WebSocket: /ws/chat             # Chat em tempo real
```

#### Frontend - Chat Interface

**arquivo:** `src/pages/ChatPage.jsx`
```jsx
import { useState, useRef, useEffect } from 'react';
import ChatMessage from '../components/chat/ChatMessage';
import ChatInput from '../components/chat/ChatInput';
import { useWebSocket } from '../hooks/useWebSocket';

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const ws = useWebSocket('/ws/chat');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = (text) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ message: text }));
      setMessages([...messages, { role: 'user', content: text }]);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      <ChatInput onSend={handleSendMessage} />
    </div>
  );
}
```

---

### 7️⃣ **WEBHOOKS & INTEGRAÇÕES EXTERNAS**

#### Backend (Já Pronto)
```python
# POST /api/webhooks/asaas        # Pagamentos confirmados
# POST /api/webhooks/waha         # Mensagens WhatsApp
# GET /api/integrations/status    # Status das integrações
```

#### Frontend - Handlers

**arquivo:** `src/services/webhookService.js`
```javascript
export const webhookService = {
  // Listeners para eventos do backend
  onPaymentConfirmed: (callback) => {
    window.addEventListener('payment:confirmed', callback);
  },
  
  onWhatsAppMessage: (callback) => {
    window.addEventListener('whatsapp:message', callback);
  },
  
  // Disparar eventos
  emit: (event, data) => {
    window.dispatchEvent(new CustomEvent(event, { detail: data }));
  },
};
```

---

## 📅 Plano de Implementação

### **Fase 1: Setup & Infraestrutura (2-3 dias)**
```
1. [ ] Configurar API client (axios + interceptors)
2. [ ] Criar estrutura de pastas
3. [ ] Implementar AuthContext
4. [ ] Criar arquivo .env.example
5. [ ] Configurar CORS no backend
6. [ ] Setup de temas TailwindCSS
```

### **Fase 2: Autenticação & Core (3-4 dias)**
```
1. [ ] Implementar Login/Register pages
2. [ ] Setup de rotas privadas
3. [ ] Implementar refresh token
4. [ ] Criar Layout base (Header/Sidebar)
5. [ ] Testes de autenticação
```

### **Fase 3: Módulos CRUD (5-7 dias)**
```
1. [ ] Customers (List, Create, Edit, Delete)
2. [ ] Products (List, Create, Edit, Delete)
3. [ ] Orders (List, Create, Edit, Status change)
4. [ ] Drivers (List, Create, Edit, Status)
5. [ ] Validação de forms
```

### **Fase 4: Dashboard & Visualizações (3-4 dias)**
```
1. [ ] Dashboard com estatísticas
2. [ ] Gráficos (Chart.js)
3. [ ] Mapas (Leaflet)
4. [ ] Filtros e buscas
5. [ ] Exportação de dados
```

### **Fase 5: Real-time Features (3-4 dias)**
```
1. [ ] WebSocket para tracking de drivers
2. [ ] Notificações em tempo real
3. [ ] ChatBot com Ollama
4. [ ] Sincronização de dados
```

### **Fase 6: Testes & Otimizações (2-3 dias)**
```
1. [ ] Testes unitários (Jest)
2. [ ] Testes E2E (Cypress)
3. [ ] Otimização de performance
4. [ ] SEO basics
5. [ ] Acessibilidade
```

### **Fase 7: Deploy & Documentação (2 dias)**
```
1. [ ] Build otimizado
2. [ ] Docker para frontend
3. [ ] Documentação de API
4. [ ] README de deploy
5. [ ] Guia de desenvolvedor
```

---

## 🛠️ Ferramentas & Configurações

### `.env` do Frontend
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_APP_NAME=Gas Automation
VITE_APP_VERSION=1.0.0
```

### API Client (`src/api/client.js`)
```javascript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
});

// Interceptor para adicionar token JWT
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para tratar erros
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirecionar para login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

---

## 📞 Endpoints Mapeados

| Funcionalidade | Método | Endpoint | Frontend Component |
|---|---|---|---|
| **Autenticação** | POST | /api/auth/login | LoginForm |
| | POST | /api/auth/register | RegisterForm |
| | POST | /api/auth/logout | Header |
| **Clientes** | GET | /api/customers | CustomerList |
| | POST | /api/customers | CustomerForm |
| | PUT | /api/customers/{id} | CustomerDetail |
| | DELETE | /api/customers/{id} | CustomerList |
| **Pedidos** | GET | /api/orders | OrderList |
| | POST | /api/orders | OrderForm |
| | PATCH | /api/orders/{id}/status | OrderDetail |
| **Entregadores** | GET | /api/drivers | DriverList |
| | GET | /api/drivers/{id}/location | DriverTracking |
| **Produtos** | GET | /api/products | ProductList |
| | POST | /api/products | ProductForm |
| **Pagamentos** | POST | /api/payments | OrderForm |
| | GET | /api/payments/{id} | OrderDetail |
| **Chat** | WebSocket | /ws/chat | ChatBot |

---

## ✅ Checklist de Implementação

### Setup Inicial
- [ ] Estrutura de pastas criada
- [ ] .env configurado
- [ ] API client implementado
- [ ] Interceptors configurados
- [ ] AuthContext criado

### Autenticação
- [ ] LoginPage implementada
- [ ] RegisterPage implementada
- [ ] Token storage funcionando
- [ ] Refresh token implementado
- [ ] Logout funcionando

### Páginas principais
- [ ] Dashboard implementada
- [ ] CustomersPage implementada
- [ ] OrdersPage implementada
- [ ] DriversPage implementada
- [ ] ProductsPage implementada

### Features avançadas
- [ ] WebSocket conectando
- [ ] Maps carregando
- [ ] Charts renderizando
- [ ] Notificações funcionando
- [ ] ChatBot respondendo

### Qualidade
- [ ] Tests unitários passando
- [ ] Tests E2E passando
- [ ] Build sem erros
- [ ] Performance otimizada
- [ ] Documentação completa

---

## 🚀 Como Começar

### 1. Clonar e instalar
```bash
cd frontend
npm install
```

### 2. Copiar arquivo .env
```bash
cp .env.example .env
# Editar com valores corretos
```

### 3. Iniciar desenvolvimento
```bash
npm run dev
```

### 4. Abrir no navegador
```
http://localhost:5173
```

---

## 📚 Documentação Referência

- **Backend API Docs:** http://localhost:8000/docs
- **Axios Docs:** https://axios-http.com
- **React Router:** https://reactrouter.com
- **TailwindCSS:** https://tailwindcss.com
- **Vite Guide:** https://vitejs.dev

---

**Documento criado:** 21 de Janeiro de 2026
**Versão:** 1.0
**Status:** Planejamento Completo - Pronto para Implementação
