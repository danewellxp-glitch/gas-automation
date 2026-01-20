import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './AdminDashboard.css';

interface Order {
  id: string;
  order_number?: number;
  status: string;
  delivery_bairro?: string;
  total_amount: number;
  payment_method?: string;
  created_at: string;
}

interface Conversation {
  phone: string;
  customer_name?: string;
  last_message?: string;
}

interface Message {
  text: string;
  from_me: boolean;
  timestamp: string;
}

interface ToastState {
  type: 'success' | 'error' | 'info';
  message: string;
}

const API_BASE = '/api';

export default function AdminDashboard() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentConversation, setCurrentConversation] = useState<string | null>(null);
  const [messageInput, setMessageInput] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const [currentTab, setCurrentTab] = useState<'today' | 'pending' | 'all'>('today');
  const [activeSection, setActiveSection] = useState('pedidos');
  const [toast, setToast] = useState<ToastState | null>(null);

  // Stats
  const [statPedidos, setStatPedidos] = useState(0);
  const [statEntregas, setStatEntregas] = useState(0);
  const [statFaturamento, setStatFaturamento] = useState('R$ 0,00');

  const token = localStorage.getItem('access_token') || localStorage.getItem('token');
  const wsRef = useRef<WebSocket | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const chatMessagesRef = useRef<HTMLDivElement>(null);

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const fetchAPI = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    const defaultOptions: RequestInit = {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...((options.headers as Record<string, string>) || {}),
      },
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: defaultOptions.headers,
    });

    if (response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      console.warn('API 401: Não autenticado');
      return null;
    }

    return response;
  }, [token]);

  // Load Orders
  const loadOrders = useCallback(async () => {
    try {
      let endpoint = '/orders';
      if (currentTab === 'pending') {
        endpoint = '/orders?status=pending';
      } else if (currentTab === 'today') {
        endpoint = '/orders/today';
      }

      const response = await fetchAPI(endpoint);
      if (response && response.ok) {
        const data = await response.json();
        setOrders(data);
      }
    } catch (error) {
      console.error('Erro ao carregar pedidos:', error);
    }
  }, [currentTab, fetchAPI]);

  // Update Stats
  const updateStats = useCallback(async () => {
    try {
      const response = await fetchAPI('/orders/today');
      if (response && response.ok) {
        const data = await response.json();
        const total = data.length;
        const delivered = data.filter((o: Order) => o.status === 'delivered').length;
        const revenue = data
          .filter((o: Order) => o.status !== 'cancelled')
          .reduce((sum: number, o: Order) => sum + parseFloat(String(o.total_amount || 0)), 0);

        setStatPedidos(total);
        setStatEntregas(delivered);
        setStatFaturamento(`R$ ${revenue.toFixed(2)}`);
      }
    } catch (error) {
      console.error('Erro ao atualizar stats:', error);
    }
  }, [fetchAPI]);

  // Update Order Status
  const updateOrderStatus = useCallback(async (orderId: string, status: string) => {
    try {
      const response = await fetchAPI(`/orders/${orderId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });

      if (response && response.ok) {
        showToast('Status atualizado!', 'success');
        loadOrders();
        updateStats();
      } else {
        showToast('Erro ao atualizar status', 'error');
      }
    } catch (error) {
      console.error('Erro:', error);
      showToast('Erro ao atualizar status', 'error');
    }
  }, [fetchAPI, loadOrders, updateStats, showToast]);

  // Cancel Order
  const cancelOrder = useCallback(async (orderId: string) => {
    if (!window.confirm('Tem certeza que deseja cancelar este pedido?')) {
      return;
    }
    await updateOrderStatus(orderId, 'cancelled');
  }, [updateOrderStatus]);

  // Load Conversations
  const loadConversations = useCallback(async () => {
    try {
      const response = await fetchAPI('/chats');
      if (response && response.ok) {
        const data = await response.json();
        setConversations(data);
      }
    } catch (error) {
      console.error('Erro ao carregar conversas:', error);
    }
  }, [fetchAPI]);

  // Select Conversation
  const selectConversation = useCallback(async (phone: string) => {
    setCurrentConversation(phone);

    try {
      const response = await fetchAPI(`/chats/${phone}/messages`);
      if (response && response.ok) {
        const data = await response.json();
        setMessages(data);
      }
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error);
    }
  }, [fetchAPI]);

  // Send Message
  const sendMessage = useCallback(async () => {
    const message = messageInput.trim();
    if (!message || !currentConversation) return;

    try {
      const response = await fetchAPI(`/chats/${currentConversation}/send`, {
        method: 'POST',
        body: JSON.stringify({ phone: currentConversation, message }),
      });

      if (response && response.ok) {
        setMessageInput('');
        setMessages(prev => [...prev, {
          text: message,
          from_me: true,
          timestamp: new Date().toISOString(),
        }]);
      }
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
    }
  }, [messageInput, currentConversation, fetchAPI]);

  // WebSocket
  const connectWebSocket = useCallback(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/dashboard`);

    ws.onopen = () => {
      console.log('WebSocket conectado');
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Mensagem recebida:', data);

      if (data.type === 'new_message') {
        if (currentConversation === data.data.phone) {
          setMessages(prev => [...prev, {
            text: data.data.message,
            from_me: false,
            timestamp: new Date().toISOString(),
          }]);
        }
        loadConversations();
      }

      if (data.type === 'new_order') {
        if (Notification.permission === 'granted') {
          new Notification('Novo Pedido!', {
            body: `#${data.data.order_number || data.data.id}`,
          });
        }
        loadOrders();
        updateStats();
      }

      if (data.type === 'order_update') {
        loadOrders();
        updateStats();
      }
    };

    ws.onclose = () => {
      console.log('WebSocket desconectado');
      setWsConnected(false);
      setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket erro:', error);
      setWsConnected(false);
    };

    wsRef.current = ws;
  }, [currentConversation, loadConversations, loadOrders, updateStats]);

  // Initialize Map
  const initMap = useCallback(() => {
    if (mapContainerRef.current && !mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current).setView([-25.4284, -49.2733], 12);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(mapRef.current);

      L.marker([-25.4284, -49.2733])
        .addTo(mapRef.current)
        .bindPopup('<b>Gas Automation</b><br>Sede');
    }
  }, []);

  // Utilities
  const formatStatus = (status: string) => {
    const statusMap: Record<string, string> = {
      pending: 'Pendente',
      paid: 'Pago',
      preparing: 'Preparando',
      dispatched: 'Em Entrega',
      delivered: 'Entregue',
      cancelled: 'Cancelado',
    };
    return statusMap[status] || status;
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleString('pt-BR');
  };

  const formatTime = (timestamp: string) => {
    if (!timestamp) return '';
    return new Date(timestamp).toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatPhone = (phone: string) => {
    if (!phone) return '';
    const cleaned = phone.replace(/\D/g, '');
    if (cleaned.length === 13) {
      return `+${cleaned.slice(0, 2)} (${cleaned.slice(2, 4)}) ${cleaned.slice(4, 9)}-${cleaned.slice(9)}`;
    }
    return phone;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('access_token');
    window.location.href = '/';
  };

  // Scroll to bottom on new messages
  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [messages]);

  // Initialization
  useEffect(() => {
    // TODO: Implementar autenticação adequada
    // Por enquanto, permite acesso sem token para desenvolvimento

    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }

    connectWebSocket();
    initMap();
    loadConversations();
    loadOrders();
    updateStats();

    const ordersInterval = setInterval(loadOrders, 30000);
    const statsInterval = setInterval(updateStats, 60000);

    return () => {
      clearInterval(ordersInterval);
      clearInterval(statsInterval);
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [token, connectWebSocket, initMap, loadConversations, loadOrders, updateStats]);

  // Reload orders when tab changes
  useEffect(() => {
    loadOrders();
  }, [currentTab, loadOrders]);

  const getOrderActions = (order: Order) => {
    const actions: JSX.Element[] = [];

    if (order.status === 'pending') {
      actions.push(
        <button key="pay" className="btn btn-success" onClick={() => updateOrderStatus(order.id, 'paid')}>
          Confirmar Pago
        </button>
      );
      actions.push(
        <button key="cancel" className="btn btn-danger" onClick={() => cancelOrder(order.id)}>
          Cancelar
        </button>
      );
    }

    if (order.status === 'paid') {
      actions.push(
        <button key="prepare" className="btn btn-primary" onClick={() => updateOrderStatus(order.id, 'preparing')}>
          Preparando
        </button>
      );
    }

    if (order.status === 'preparing') {
      actions.push(
        <button key="dispatch" className="btn btn-warning" onClick={() => updateOrderStatus(order.id, 'dispatched')}>
          Saiu p/ Entrega
        </button>
      );
    }

    if (order.status === 'dispatched') {
      actions.push(
        <button key="deliver" className="btn btn-success" onClick={() => updateOrderStatus(order.id, 'delivered')}>
          Entregue
        </button>
      );
    }

    return actions;
  };

  return (
    <div className="admin-dashboard">
      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}

      <div className="admin-container">
        {/* Sidebar */}
        <div className="admin-sidebar">
          <div className="admin-logo">Gas Automation</div>

          <div
            className={`admin-menu-item ${activeSection === 'pedidos' ? 'active' : ''}`}
            onClick={() => setActiveSection('pedidos')}
          >
            Pedidos
          </div>
          <div
            className={`admin-menu-item ${activeSection === 'entregas' ? 'active' : ''}`}
            onClick={() => setActiveSection('entregas')}
          >
            Entregas
          </div>
          <div
            className={`admin-menu-item ${activeSection === 'clientes' ? 'active' : ''}`}
            onClick={() => setActiveSection('clientes')}
          >
            Clientes
          </div>
          <div
            className={`admin-menu-item ${activeSection === 'produtos' ? 'active' : ''}`}
            onClick={() => setActiveSection('produtos')}
          >
            Produtos
          </div>
          <div
            className={`admin-menu-item ${activeSection === 'relatorios' ? 'active' : ''}`}
            onClick={() => setActiveSection('relatorios')}
          >
            Relatorios
          </div>
          <div
            className="admin-menu-item"
            onClick={() => window.location.href = '/operador'}
          >
            Painel Operador
          </div>

          <div className="admin-stats-box">
            <h4>Resumo Hoje</h4>
            <div className="admin-stat-item">
              <span>Pedidos</span>
              <span className="admin-stat-value">{statPedidos}</span>
            </div>
            <div className="admin-stat-item">
              <span>Entregas</span>
              <span className="admin-stat-value">{statEntregas}</span>
            </div>
            <div className="admin-stat-item">
              <span>Faturamento</span>
              <span className="admin-stat-value">{statFaturamento}</span>
            </div>
          </div>

          <div style={{ marginTop: 'auto', paddingTop: '20px' }}>
            <div className="admin-menu-item" onClick={logout}>
              Sair
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="admin-main-content">
          <div className="admin-header">
            <h1>Painel Administrativo</h1>
            <div className="connection-status">
              <span className={`status-dot ${wsConnected ? 'connected' : 'disconnected'}`}></span>
              <span>{wsConnected ? 'Conectado' : 'Desconectado'}</span>
            </div>
          </div>

          {/* Tabs */}
          <div className="admin-tabs">
            <button
              className={`admin-tab-btn ${currentTab === 'today' ? 'active' : ''}`}
              onClick={() => setCurrentTab('today')}
            >
              Hoje
            </button>
            <button
              className={`admin-tab-btn ${currentTab === 'pending' ? 'active' : ''}`}
              onClick={() => setCurrentTab('pending')}
            >
              Pendentes
            </button>
            <button
              className={`admin-tab-btn ${currentTab === 'all' ? 'active' : ''}`}
              onClick={() => setCurrentTab('all')}
            >
              Todos
            </button>
          </div>

          {/* Orders Grid */}
          <div className="orders-grid">
            {orders.length === 0 ? (
              <div className="empty-state">Nenhum pedido encontrado</div>
            ) : (
              orders.map((order) => (
                <div key={order.id} className="order-card">
                  <div className="order-header">
                    <span className="order-id">#{order.order_number || order.id}</span>
                    <span className={`order-status status-${order.status}`}>
                      {formatStatus(order.status)}
                    </span>
                  </div>
                  <div className="order-info">
                    <p><strong>Bairro:</strong> {order.delivery_bairro || 'N/A'}</p>
                    <p><strong>Total:</strong> R$ {parseFloat(String(order.total_amount || 0)).toFixed(2)}</p>
                    <p><strong>Pagamento:</strong> {order.payment_method || 'N/A'}</p>
                    <p><small>Criado: {formatDate(order.created_at)}</small></p>
                  </div>
                  <div className="order-actions">
                    {getOrderActions(order)}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Map Section */}
          <div className="map-section">
            <h3>Mapa de Entregas</h3>
            <div className="map-container" ref={mapContainerRef}></div>
          </div>
        </div>

        {/* Chat Panel */}
        <div className="admin-chat-panel">
          <div className="chat-header">
            Conversas
            <div className="connection-status">
              <span className={`status-dot ${wsConnected ? 'connected' : 'disconnected'}`}></span>
            </div>
          </div>

          {/* Conversation List */}
          <div className="conversation-list">
            {conversations.length === 0 ? (
              <div className="empty-state" style={{ padding: '20px' }}>Nenhuma conversa</div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.phone}
                  className={`conversation-item ${currentConversation === conv.phone ? 'active' : ''}`}
                  onClick={() => selectConversation(conv.phone)}
                >
                  <div className="conversation-name">
                    {conv.customer_name || formatPhone(conv.phone)}
                  </div>
                  <div className="conversation-preview">
                    {conv.last_message || 'Sem mensagens'}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Chat Messages */}
          <div className="chat-messages" ref={chatMessagesRef}>
            {!currentConversation ? (
              <div className="empty-state">Selecione uma conversa</div>
            ) : messages.length === 0 ? (
              <div className="empty-state">Sem mensagens</div>
            ) : (
              messages.map((msg, index) => (
                <div key={index} className={`message ${msg.from_me ? 'outgoing' : 'incoming'}`}>
                  <div className="message-bubble">{msg.text}</div>
                  <div className="message-info">{formatTime(msg.timestamp)}</div>
                </div>
              ))
            )}
          </div>

          {/* Chat Input */}
          <div className="chat-input">
            <input
              type="text"
              placeholder="Digite sua mensagem..."
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              disabled={!currentConversation}
            />
            <button onClick={sendMessage} disabled={!currentConversation}>
              Enviar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
