import React, { useEffect, useRef, useState, useCallback } from 'react';

interface Conversation {
  id: number;
  name?: string;
  customer_number: string;
  status: string;
  created_at: string;
}

interface Message {
  id?: number;
  sender: string;
  content: string;
  message_type?: string;
  bot_service?: string;
  timestamp: string;
  isFromCurrentUser?: boolean; // Nova propriedade para identificar mensagens do usuário atual
}

interface Order {
  id: number;
  customer_name: string;
  total: number;
  status: string;
  endereco_entrega: string;
  numero_entrega: string;
  bairro_entrega: string;
}

interface BotInteraction {
  customer_name: string;
  phone_number: string;
  user_message: string;
  bot_response: string;
  bot_type: string;
  timestamp: string;
}

interface NotificationState {
  type: 'success' | 'error' | 'info';
  message: string;
}

// Configuração centralizada de endpoints
const API_BASE = '/api';
const ENDPOINTS = {
  conversations: `${API_BASE}/conversations`,
  myConversations: `${API_BASE}/my-conversations`,
  orders: `${API_BASE}/orders/pending`,
  botInteractions: `${API_BASE}/bot-interactions`,
  conversationMessages: (id: number) => `${API_BASE}/conversations/${id}/messages`,
  conversationAssign: (id: number) => `${API_BASE}/conversations/${id}/assign`,
  conversationReply: (id: number) => `${API_BASE}/conversations/${id}/reply`,
  conversationEnd: (id: number) => `${API_BASE}/conversations/${id}/end`,
};

// Componente para renderizar mensagens individuais
const MessageComponent: React.FC<{ message: Message }> = ({ message }) => {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getMessageClass = () => {
    if (message.isFromCurrentUser) return "message agent";
    if (message.message_type === "bot" || message.sender === "bot") return "message bot";
    if (message.message_type === "agent" || message.sender === "agent") return "message agent";
    return "message";
  };

  const getSenderDisplay = () => {
    if (message.isFromCurrentUser) return "Você";
    if (message.message_type === "bot" || message.sender === "bot") return "Bot";
    if (message.message_type === "agent" || message.sender === "agent") return "Atendente";
    if (message.message_type === "customer" || message.sender === "customer") return "Cliente";
    return message.sender;
  };

  const getBotBadge = () => {
    if ((message.message_type === "bot" || message.sender === "bot") && message.bot_service) {
      const badgeClass = message.bot_service.toLowerCase();
      return <span className={`bot-badge ${badgeClass}`}>{message.bot_service}</span>;
    }
    return null;
  };

  return (
    <div className={getMessageClass()}>
      <div className="message-content-wrapper">
        <div className="message-header">
          <span className="sender-name">{getSenderDisplay()}</span>
          {getBotBadge()}
        </div>
        <div className="message-text">{message.content}</div>
        <div className="message-footer">
          <span className="message-timestamp">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
};

export default function OperatorDashboard() {
  const [allConversations, setAllConversations] = useState<Conversation[]>([]);
  const [myConversations, setMyConversations] = useState<Conversation[]>([]);
  const [chatMessages, setChatMessages] = useState<Message[]>([]); // Novo estado para mensagens do chat
  const [orders, setOrders] = useState<Order[]>([]);
  const [botInteractions, setBotInteractions] = useState<BotInteraction[]>([]);
  const [showBotInteractions, setShowBotInteractions] = useState(false);
  const [ordersCount, setOrdersCount] = useState(0);
  const [showOrdersPanel, setShowOrdersPanel] = useState(false);
  const [messageInput, setMessageInput] = useState('');
  const [filterValue, setFilterValue] = useState('all');
  const [notification, setNotification] = useState<NotificationState | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const currentConversationIdRef = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const isSendingRef = useRef(false);
  const chatMessagesRef = useRef<HTMLDivElement>(null);
  const messageInputRef = useRef<HTMLInputElement>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;

  const token = localStorage.getItem("access_token");

  // Utilitários de notificação
  const showError = useCallback((message: string) => {
    setNotification({ type: 'error', message });
    setTimeout(() => setNotification(null), 5000);
  }, []);

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = "success") => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 3000);
  }, []);

  // Notificação de pedido
  const showOrderNotification = useCallback((order: Order) => {
    // Som de notificação
    try {
      const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdH2JkZiYl5eSjImEf35/goeMkZaZmpmYlZGNiYWBf4CGi5CUl5mZmJaSkY2JhYKAg4iNkpWYmZiWk5CL');
      audio.volume = 0.3;
      audio.play().catch(() => {});
    } catch(e) {
      console.error('Erro ao tocar som:', e);
    }

    // Notificação do navegador
    if (Notification.permission === 'granted') {
      new Notification('Novo Pedido!', {
        body: `#${order.id} - ${order.customer_name}\nR$ ${order.total.toFixed(2)}`,
        icon: '/static/icon.png'
      });
    }

    // Toast na tela
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed; top: 20px; right: 20px; z-index: 9999;
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white; padding: 15px 25px; border-radius: 10px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.3);
      animation: slideIn 0.3s ease;
    `;
    toast.innerHTML = `
      <strong>Novo Pedido #${order.id}</strong><br>
      ${order.customer_name}<br>
      <small>${order.endereco_entrega}, ${order.bairro_entrega}</small><br>
      <strong>R$ ${order.total.toFixed(2)}</strong>
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
  }, []);

  // WebSocket com reconexão automática
  const connectWebSocket = useCallback(() => {
    if (!token) {
      console.error('Token ausente - não é possível conectar WebSocket');
      return;
    }

    // Limpa timeout anterior
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Fecha conexão anterior se existir
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws?token=${token}`;
    
    console.log('Conectando WebSocket:', wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket conectado com sucesso');
      reconnectAttemptsRef.current = 0;
      showToast('Conexão estabelecida', 'success');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket message:", data);

        // Novo pedido
        if (data.type === 'new_order') {
          showOrderNotification(data.order);
          loadOrders();
          return;
        }

        // Atualização de pedido
        if (data.type === 'order_update') {
          console.log('Pedido atualizado:', data);
          loadOrders();
          return;
        }

        // Mensagens da conversa atual
        if (!data.conversation_id || data.conversation_id !== currentConversationIdRef.current) {
          return;
        }

        appendMessageToChat(data);
      } catch (error) {
        console.error('Erro ao processar mensagem WebSocket:', error);
      }
    };

    ws.onerror = (error) => {
      console.error("Erro WebSocket:", error);
    };

    ws.onclose = (event) => {
      console.log('WebSocket fechado:', event.code, event.reason);
      wsRef.current = null;

      // Tenta reconectar se não foi fechamento intencional
      if (event.code !== 1000 && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current++;
        console.log(`Tentando reconectar (${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})...`);
        
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, RECONNECT_DELAY * reconnectAttemptsRef.current);
      } else if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
        showError('Não foi possível restabelecer conexão. Recarregue a página.');
      }
    };

    wsRef.current = ws;
  }, [token, showToast, showError, showOrderNotification]);

  // Adiciona mensagem ao chat usando estado React
  const appendMessageToChat = useCallback((data: any) => {
    const newMessage: Message = {
      id: data.id,
      sender: data.sender,
      content: data.message || data.content || '',
      message_type: data.message_type,
      bot_service: data.bot_service,
      timestamp: data.timestamp || new Date().toISOString(),
      isFromCurrentUser: false
    };

    setChatMessages(prev => [...prev, newMessage]);

    // Scroll automático para o final
    setTimeout(() => {
      if (chatMessagesRef.current) {
        chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
      }
    }, 100);
  }, []);



  // Carregar pedidos
  const loadOrders = useCallback(async () => {
    try {
      const response = await fetch(ENDPOINTS.orders, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const ordersData = await response.json();
        setOrders(ordersData);
        setOrdersCount(ordersData.length);
      } else if (response.status === 401) {
        showError("Sessão expirada. Faça login novamente.");
        localStorage.removeItem("access_token");
        console.warn('API 401: Não autenticado');
      }
    } catch (error) {
      console.error('Erro ao carregar pedidos:', error);
    }
  }, [token, showError]);

  const toggleOrders = useCallback(() => {
    setShowOrdersPanel(prev => {
      if (!prev) {
        loadOrders();
      }
      return !prev;
    });
  }, [loadOrders]);

  const highlightSelected = useCallback((conversationId: number) => {
    document.querySelectorAll(".conversation").forEach(div => {
      const el = div as HTMLElement;
      if (parseInt(el.dataset.id || '0') === conversationId) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    });
  }, []);

  // Buscar minhas conversas
  const fetchMyConversations = useCallback(async () => {
    try {
      const res = await fetch(ENDPOINTS.myConversations, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.status === 401) {
        showError("Sessão expirada. Faça login novamente.");
        localStorage.removeItem("access_token");
        console.warn('API 401: Não autenticado');
        return;
      }

      const myData = await res.json();
      setMyConversations(myData);
    } catch (error) {
      console.error("Erro ao carregar minhas conversas:", error);
    }
  }, [token, showError]);

  // Buscar todas conversas
  const fetchAllConversations = useCallback(async () => {
    try {
      const res = await fetch(ENDPOINTS.conversations, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.status === 401) {
        showError("Sessão expirada. Faça login novamente.");
        localStorage.removeItem("access_token");
        console.warn('API 401: Não autenticado');
        return;
      }

      const data = await res.json();
      setAllConversations(data.filter((c: Conversation) => c.status === "pending"));
    } catch (error) {
      console.error("Erro ao carregar todas as conversas:", error);
    }
  }, [token, showError]);

  // Carregar chat
  const loadChat = useCallback(async (conversationId: number) => {
    if (currentConversationIdRef.current !== conversationId) {
      currentConversationIdRef.current = conversationId;

      try {
        const assignRes = await fetch(ENDPOINTS.conversationAssign(conversationId), {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!assignRes.ok) {
          console.error("Erro ao atribuir conversa:", assignRes.status);
          showError("Erro ao atribuir conversa.");
          return;
        }

        fetchMyConversations();
        fetchAllConversations();
      } catch (error) {
        console.error("Erro ao atribuir conversa:", error);
        showError("Erro ao atribuir conversa.");
        return;
      }
    }

    highlightSelected(conversationId);

    try {
      const res = await fetch(ENDPOINTS.conversationMessages(conversationId), {
        headers: { Authorization: `Bearer ${token}` }
      });

      const messagesData: Message[] = await res.json();
      
      // Carregar mensagens no estado React
      const formattedMessages: Message[] = messagesData.map(msg => ({
        ...msg,
        isFromCurrentUser: false
      }));
      setChatMessages(formattedMessages);

      // Scroll automático para o final
      setTimeout(() => {
        if (chatMessagesRef.current) {
          chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
        }
      }, 100);
    } catch (error) {
      console.error("Erro ao carregar mensagens:", error);
    }
  }, [token, showError, fetchMyConversations, fetchAllConversations, highlightSelected]);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("token");
    window.location.href = "/";
  }, []);

  // Enviar mensagem
  const sendMessage = useCallback(async () => {
    if (isSendingRef.current) {
      console.log('Já está enviando mensagem, ignorando...');
      return;
    }

    const content = messageInput.trim();

    if (!content || !currentConversationIdRef.current) {
      console.warn("Mensagem vazia ou conversa não selecionada");
      return;
    }

    isSendingRef.current = true;
    if (messageInputRef.current) messageInputRef.current.disabled = true;

    try {
      const res = await fetch(ENDPOINTS.conversationReply(currentConversationIdRef.current), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ message: content })
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error("Erro na resposta da API:", res.status, errorText);
        showError("Erro ao enviar mensagem: " + errorText);
        return;
      }

      // Adicionar mensagem do usuário ao chat
      const userMessage: Message = {
        sender: "agent",
        content: content,
        message_type: "agent",
        timestamp: new Date().toISOString(),
        isFromCurrentUser: true
      };
      setChatMessages(prev => [...prev, userMessage]);

      // Scroll automático para o final
      setTimeout(() => {
        if (chatMessagesRef.current) {
          chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
        }
      }, 100);

      setMessageInput("");
      highlightSelected(currentConversationIdRef.current);
    } catch (error) {
      console.error("Erro ao enviar mensagem:", error);
      showError("Erro ao enviar mensagem");
    } finally {
      isSendingRef.current = false;
      if (messageInputRef.current) messageInputRef.current.disabled = false;
      messageInputRef.current?.focus();
    }
  }, [messageInput, token, showError, highlightSelected]);

  // Encerrar conversa
  const endConversation = useCallback(async () => {
    if (!currentConversationIdRef.current) {
      showError("Nenhuma conversa selecionada para encerrar.");
      return;
    }

    setShowConfirmDialog(true);
  }, [showError]);

  const confirmEndConversation = useCallback(async () => {
    setShowConfirmDialog(false);

    if (!currentConversationIdRef.current) return;

    try {
      const res = await fetch(ENDPOINTS.conversationEnd(currentConversationIdRef.current), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error("Erro na resposta da API:", res.status, errorText);
        showError("Erro ao encerrar conversa: " + res.status);
        return;
      }

      showToast("Conversa encerrada com sucesso.");
      setChatMessages([]); // Limpar mensagens do estado
      currentConversationIdRef.current = null;
      fetchMyConversations();
      fetchAllConversations();
    } catch (error: any) {
      console.error("Erro ao encerrar conversa:", error);
      showError("Erro de conexao: " + error.message);
    }
  }, [token, showError, showToast, fetchMyConversations, fetchAllConversations]);

  // Criar conversa de teste (para debug)
  const criarConversaTeste = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations/test`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          customer_number: `5541${Math.floor(Math.random() * 90000000) + 10000000}`,
          name: `Cliente Teste ${Math.floor(Math.random() * 1000)}`
        })
      });

      if (res.ok) {
        showToast("Conversa de teste criada!");
        fetchAllConversations();
      } else {
        showError("Erro ao criar conversa de teste");
      }
    } catch (error) {
      console.error("Erro ao criar conversa de teste:", error);
      showError("Erro ao criar conversa de teste");
    }
  }, [token, showToast, showError, fetchAllConversations]);

  // Buscar interações bot
  const fetchBotInteractions = useCallback(async () => {
    try {
      const res = await fetch(ENDPOINTS.botInteractions, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.status === 401) {
        showError("Sessão expirada. Faça login novamente.");
        localStorage.removeItem("access_token");
        console.warn('API 401: Não autenticado');
        return;
      }

      const data = await res.json();
      setBotInteractions(data);
    } catch (error) {
      console.error("Erro:", error);
      setBotInteractions([]);
    }
  }, [token, showError]);

  // Filtrar conversas
  const filterConversations = useCallback(async () => {
    if (filterValue === 'bot_only') {
      setShowBotInteractions(true);
      fetchBotInteractions();
    } else {
      setShowBotInteractions(false);

      try {
        const url = filterValue === 'all' 
          ? ENDPOINTS.conversations 
          : `${ENDPOINTS.conversations}?filter_type=${filterValue}`;

        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (res.status === 401) {
          showError("Sessão expirada. Faça login novamente.");
          localStorage.removeItem("access_token");
          console.warn('API 401: Não autenticado');
          return;
        }

        const data = await res.json();
        setAllConversations(data);
      } catch (error) {
        console.error("Erro:", error);
        setAllConversations([]);
      }
    }
  }, [filterValue, token, showError, fetchBotInteractions]);

  const clearFilter = useCallback(() => {
    setFilterValue('all');
  }, []);

  const handleFilterChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilterValue(e.target.value);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  // Solicitar permissão de notificação
  useEffect(() => {
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  // Inicialização
  useEffect(() => {
    if (!token) {
      showError("Token ausente. Faça login novamente.");
      window.location.href = "/";
      return;
    }

    connectWebSocket();
    fetchMyConversations();
    fetchAllConversations();
    loadOrders();

    const ordersInterval = setInterval(loadOrders, 30000);

    return () => {
      clearInterval(ordersInterval);
      
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [token, connectWebSocket, fetchMyConversations, fetchAllConversations, loadOrders, showError]);

  // Aplicar filtro quando mudar
  useEffect(() => {
    if (filterValue !== 'all') {
      filterConversations();
    } else {
      fetchAllConversations();
    }
  }, [filterValue, filterConversations, fetchAllConversations]);

  return (
    <>
      <style>{`        :root {
          --primary-color: #4f46e5;
          --secondary-color: #3b82f6;
          --background-color: #f9fafb;
          --text-color: #111827;
          --muted-text: #6b7280;
          --border-color: #e5e7eb;
          --card-bg: #ffffff;
        }

        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background-color: var(--background-color);
          color: var(--text-color);
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          height: 100vh;
        }

        header {
          background-color: var(--primary-color);
          color: white;
          padding: 1rem 2rem;
          text-align: center;
          font-size: 1.5rem;
          font-weight: bold;
        }

        main {
          display: flex;
          gap: 1rem;
          padding: 1rem;
          height: 100%;
        }

        section {
          overflow-y: auto;
          padding: 1rem;
          background: var(--card-bg);
          border: 1px solid var(--border-color);
          border-radius: 10px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
          transition: box-shadow 0.3s ease;
        }

        section:hover {
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
        }

        section:nth-child(1),
        section:nth-child(2) {
          flex: 0 0 300px;
        }

        section:nth-child(3) {
          flex: 1;
          display: flex;
          flex-direction: column;
        }

        section h2 {
          color: var(--primary-color);
          margin-bottom: 15px;
          font-size: 20px;
          border-bottom: 2px solid #f0f0f0;
          padding-bottom: 10px;
        }

        .conversation {
          background: var(--card-bg);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          padding: 10px;
          margin-bottom: 10px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .conversation:hover {
          background: #e8eaf6;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .conversation.active {
          background: #c5cae9 !important;
          border-left: 4px solid var(--primary-color);
          box-shadow: 0 2px 8px rgba(79, 70, 229, 0.2);
        }

        .conversation p {
          margin: 4px 0;
          font-size: 0.9em;
        }

        .conversation small {
          font-size: 0.8em;
          color: var(--muted-text);
        }

        .assign-btn, button {
          background-color: var(--primary-color);
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          cursor: pointer;
          margin-top: 5px;
          transition: all 0.3s ease;
          font-weight: 500;
        }

        .assign-btn:hover, button:hover {
          background-color: #4338ca;
          transform: translateY(-1px);
          box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
        }

        #chat {
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        #chat-messages {
          flex: 1;
          background-color: var(--card-bg);
          padding: 1rem;
          border-radius: 8px;
          overflow-y: auto;
          margin-bottom: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .message {
          padding: 0.75rem 1rem;
          border-radius: 8px;
          max-width: 70%;
          word-wrap: break-word;
          font-size: 0.95rem;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
          transition: all 0.3s ease;
        }

        .message:hover {
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
          transform: translateY(-1px);
        }

        .message.customer {
          align-self: flex-start;
          background-color: #e0e7ff;
          color: var(--text-color);
          border-radius: 18px 18px 18px 4px;
          margin-right: auto;
        }

        .message.agent {
          align-self: flex-end;
          background-color: var(--secondary-color);
          color: white;
          border-radius: 18px 18px 4px 18px;
          margin-left: auto;
        }

        .message.bot {
          align-self: flex-start;
          background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
          border-left: 4px solid #4caf50;
          border-radius: 18px 18px 18px 4px;
          margin-right: auto;
        }

        .message-content-wrapper {
          padding: 10px 14px;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .message-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 4px;
        }

        .message-text {
          font-size: 14px;
          line-height: 1.5;
          color: #212121;
          word-break: break-word;
        }

        .message-footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-top: 4px;
          gap: 8px;
        }

        .message-timestamp {
          font-size: 11px;
          color: var(--muted-text);
          font-weight: 400;
        }

        .message-status {
          font-size: 12px;
          color: var(--muted-text);
        }

        .sender-name {
          font-weight: 600;
          font-size: 13px;
          color: #424242;
        }

        .bot-badge {
          display: inline-block;
          padding: 2px 6px;
          border-radius: 8px;
          font-size: 10px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .bot-badge.claude {
          background: #9c27b0;
          color: white;
        }

        .bot-badge.ollama {
          background: #ff9800;
          color: white;
        }

        .bot-badge.fallback {
          background: #607d8b;
          color: white;
        }

        .message.bot .sender {
          color: #2e7d32;
        }

        .bot-indicator {
          font-size: 12px;
          color: #4caf50;
          font-weight: bold;
          margin-right: 5px;
        }

        .escalation-indicator {
          background-color: #fff3e0;
          border-left: 3px solid #ff9800;
          color: #e65100;
          font-size: 12px;
          padding: 5px;
          margin: 5px 0;
          border-radius: 4px;
        }

        .chat-input {
          display: flex;
          gap: 0.5rem;
          margin-top: 1rem;
        }

        .chat-input input {
          flex: 1;
          padding: 0.75rem;
          border-radius: 8px;
          border: 1px solid var(--border-color);
          font-size: 1rem;
          transition: border-color 0.3s ease;
        }

        .chat-input input:focus {
          outline: none;
          border-color: var(--primary-color);
          box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
        }

        /* Filter Section Styling */
        .filter-section {
          background-color: #f8f9fa;
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1rem;
          border: 1px solid var(--border-color);
        }

        .filter-section label {
          font-weight: 600;
          color: var(--muted-text);
          margin-right: 0.5rem;
          font-size: 0.9rem;
        }

        .filter-select {
          background-color: var(--card-bg);
          border: 2px solid var(--border-color);
          border-radius: 8px;
          padding: 0.5rem;
          font-size: 0.9rem;
          color: var(--muted-text);
          cursor: pointer;
          transition: all 0.2s ease;
          min-width: 120px;
        }

        .filter-select:hover {
          border-color: var(--primary-color);
        }

        .filter-select:focus {
          outline: none;
          border-color: var(--primary-color);
          box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
        }

        .clear-filter-btn {
          background-color: var(--primary-color);
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.9rem;
          margin-left: 0.5rem;
          transition: all 0.2s ease;
        }

        .clear-filter-btn:hover {
          background-color: #5a6268;
          transform: translateY(-1px);
        }

        .filter-controls {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        /* Pedidos Section */
        .orders-panel {
          position: fixed;
          top: 60px;
          right: 20px;
          width: 320px;
          max-height: 400px;
          background: var(--card-bg);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.15);
          z-index: 1000;
          overflow: hidden;
          display: none;
        }

        .orders-panel.show {
          display: block;
        }

        .orders-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 12px 15px;
          font-weight: bold;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .orders-header .close-btn {
          background: none;
          border: none;
          color: white;
          font-size: 20px;
          cursor: pointer;
        }

        .orders-list {
          max-height: 340px;
          overflow-y: auto;
          padding: 10px;
        }

        .order-card-mini {
          background: #f8f9fa;
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 10px;
          border-left: 4px solid #667eea;
          transition: all 0.3s ease;
        }

        .order-card-mini:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .order-card-mini.novo { border-left-color: #ffc107; }
        .order-card-mini.confirmado { border-left-color: #17a2b8; }
        .order-card-mini.saiu_entrega { border-left-color: #28a745; }

        .order-card-mini h4 {
          margin: 0 0 8px 0;
          display: flex;
          justify-content: space-between;
        }

        .order-card-mini p {
          margin: 4px 0;
          font-size: 13px;
          color: #666;
        }

        .order-badge {
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 10px;
          background: #667eea;
          color: white;
        }

        .orders-toggle {
          position: fixed;
          top: 70px;
          right: 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          padding: 10px 15px;
          border-radius: 20px;
          cursor: pointer;
          z-index: 999;
          box-shadow: 0 2px 10px rgba(0,0,0,0.2);
          display: flex;
          align-items: center;
          gap: 8px;
          transition: all 0.3s ease;
        }

        .orders-toggle:hover {
          transform: scale(1.05);
          box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }

        .orders-toggle .badge {
          background: #ff4757;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 12px;
        }

        @keyframes pulse {
          0% { transform: scale(1); }
          50% { transform: scale(1.1); }
          100% { transform: scale(1); }
        }

        .orders-toggle.has-orders {
          animation: pulse 2s infinite;
        }

        /* Notificações */
        .notification {
          position: fixed;
          top: 20px;
          right: 20px;
          padding: 15px 25px;
          border-radius: 10px;
          color: white;
          font-weight: 600;
          z-index: 1000;
          box-shadow: 0 4px 15px rgba(0,0,0,0.3);
          animation: slideInRight 0.3s ease;
        }

        .notification.success {
          background: linear-gradient(135deg, #48bb78, #38a169);
        }

        .notification.error {
          background: linear-gradient(135deg, #f56565, #e53e3e);
        }

        .notification.info {
          background: linear-gradient(135deg, #4299e1, #3182ce);
        }

        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        /* Dialog de confirmação */
        .confirm-dialog {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 2000;
        }

        .confirm-dialog-content {
          background: var(--card-bg);
          padding: 30px;
          border-radius: 10px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.3);
          max-width: 400px;
          width: 90%;
          text-align: center;
          border: 1px solid var(--border-color);
        }

        .confirm-dialog-content h3 {
          margin-bottom: 15px;
          color: var(--text-color);
        }

        .confirm-dialog-content p {
          margin-bottom: 20px;
          color: var(--muted-text);
        }

        .confirm-buttons {
          display: flex;
          gap: 10px;
          justify-content: center;
        }

        .confirm-buttons button {
          padding: 10px 20px;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.3s ease;
        }

        .confirm-buttons button:first-child {
          background: #e53e3e;
          color: white;
        }

        .confirm-buttons button:first-child:hover {
          background: #c53030;
          transform: translateY(-1px);
        }

        .confirm-buttons button:last-child {
          background: #a0aec0;
          color: white;
        }

        .confirm-buttons button:last-child:hover {
          background: #718096;
          transform: translateY(-1px);
        }

        /* Responsividade */
        @media (max-width: 768px) {
          main {
            flex-direction: column;
            height: auto;
          }

          section {
            margin-bottom: 20px;
          }

          .chat-input {
            flex-direction: column;
          }

          .chat-input input {
            margin-bottom: 10px;
          }
        }
`}</style>

      {/* Notificação */}
      {notification && (
        <div className={`notification ${notification.type}`}>
          {notification.message}
        </div>
      )}

      {/* Dialog de confirmação */}
      {showConfirmDialog && (
        <div className="confirm-dialog">
          <div className="confirm-dialog-content">
            <h3>Encerrar Conversa</h3>
            <p>Tem certeza que deseja encerrar esta conversa?</p>
            <div className="confirm-buttons">
              <button onClick={confirmEndConversation}>Sim, encerrar</button>
              <button onClick={() => setShowConfirmDialog(false)}>Cancelar</button>
            </div>
          </div>
        </div>
      )}

      <header>
        <h1>Painel do Operador</h1>
      </header>

      <main>
        <section>
          <h2>Conversas disponíveis</h2>
          <div className="filter-section">
            <div className="filter-controls">
              <label htmlFor="conversation-filter">Filtro:</label>
              <select
                id="conversation-filter"
                className="filter-select"
                value={filterValue}
                onChange={handleFilterChange}
              >
                <option value="all">📋 Todas</option>
                <option value="active">🟢 Ativas</option>
                <option value="escalated">🔥 Escaladas</option>
              </select>
              <button onClick={clearFilter} className="clear-filter-btn">
                🔄 Limpar
              </button>
            </div>
          </div>
          <div id="all-conversations" style={{ display: showBotInteractions ? 'none' : 'block' }}>
            {allConversations.map(c => (
              <div
                key={c.id}
                className="conversation"
                data-id={c.id}
                onClick={() => loadChat(c.id)}
              >
                <p><strong>Nome:</strong> {c.name ?? '(Sem nome)'}</p>
                <p><strong>Número:</strong> {c.customer_number}</p>
                <p><strong>Status:</strong> {c.status}</p>
              </div>
            ))}
          </div>
          <div id="bot-interactions" style={{ display: showBotInteractions ? 'block' : 'none' }}>
            <h4>Interações Bot</h4>
            <div id="bot-interactions-list">
              {botInteractions.map((interaction, idx) => (
                <div key={idx} className="conversation">
                  <div><strong>{interaction.customer_name}</strong></div>
                  <div><small>{interaction.phone_number}</small></div>
                  <div>Pergunta: {interaction.user_message}</div>
                  <div style={{ color: '#2e7d32' }}>Bot: {interaction.bot_response.substring(0, 100)}...</div>
                  <div><small>Bot: {interaction.bot_type} | {new Date(interaction.timestamp).toLocaleString()}</small></div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section>
          <h2>Minhas conversas</h2>
          <div id="my-conversations">
            {myConversations.map(c => (
              <div key={c.id} className="conversation" onClick={() => loadChat(c.id)}>
                <p><strong>Nome:</strong> {c.name ?? '(Sem nome)'}</p>
                <p><strong>Número:</strong> {c.customer_number}</p>
                <p><strong>Status:</strong> {c.status}</p>
                <small>Iniciado em: {new Date(c.created_at).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" })}</small>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2>Chat</h2>
          <div id="chat">
            <div id="chat-messages" ref={chatMessagesRef}>
              {chatMessages.map((message, index) => (
                <MessageComponent key={`${message.timestamp}-${index}`} message={message} />
              ))}
            </div>
            <div className="chat-input">
              <input
                type="text"
                id="message-input"
                ref={messageInputRef}
                placeholder="Digite sua mensagem..."
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <button id="send-button" onClick={sendMessage}>Enviar</button>
              <button onClick={endConversation}>Encerrar</button>
              <button onClick={criarConversaTeste}>Criar conversa teste</button>
              <a href="/" style={{ position: 'absolute', top: '10px', right: '90px', backgroundColor: '#667eea', color: 'white', padding: '0.5rem 1rem', borderRadius: '5px', textDecoration: 'none', fontWeight: 600 }}>
                Dashboard
              </a>
              <button id="logout" onClick={logout} style={{ position: 'absolute', top: '10px', right: '10px' }}>
                Logout
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Botão de Pedidos */}
      <button className={`orders-toggle ${ordersCount > 0 ? 'has-orders' : ''}`} onClick={toggleOrders}>
        📦 Pedidos <span className="badge" id="orders-count">{ordersCount}</span>
      </button>

      {/* Painel de Pedidos */}
      <div className={`orders-panel ${showOrdersPanel ? 'show' : ''}`} id="orders-panel">
        <div className="orders-header">
          📦 Pedidos Pendentes
          <button className="close-btn" onClick={toggleOrders}>&times;</button>
        </div>
        <div className="orders-list" id="orders-list">
          {orders.length === 0 ? (
            <p style={{ color: '#999', textAlign: 'center', padding: '20px' }}>Nenhum pedido pendente</p>
          ) : (
            orders.map(order => (
              <div key={order.id} className={`order-card-mini ${order.status}`}>
                <h4>
                  Pedido #{order.id}
                  <span className="order-badge">{order.status.toUpperCase()}</span>
                </h4>
                <p><strong>{order.endereco_entrega}, {order.numero_entrega}</strong></p>
                <p>{order.bairro_entrega}</p>
                <p style={{ color: '#667eea', fontWeight: 'bold' }}>R$ {order.total.toFixed(2)}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}