// Dashboard do Operador - Gas Automation
class DashboardApp {
    constructor() {
        this.currentTab = 'chats';
        this.currentChat = null;
        this.ws = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.updateTime();
        setInterval(() => this.updateTime(), 1000);
        this.loadChats();
        this.loadReports();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Chat panel
        document.getElementById('close-chat-btn').addEventListener('click', () => {
            this.closeChatPanel();
        });

        // Message input
        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });

        document.getElementById('send-message-btn').addEventListener('click', () => {
            this.sendMessage();
        });

        // Filters
        document.getElementById('status-filter').addEventListener('change', () => {
            this.loadChats();
        });

        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket conectado');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket desconectado');
            setTimeout(() => this.connectWebSocket(), 5000);
        };

        this.ws.onerror = (error) => {
            console.error('Erro WebSocket:', error);
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'new_message':
                this.handleNewMessage(data);
                break;
            case 'chat_update':
                this.loadChats();
                break;
            case 'order_update':
                this.loadOrders();
                break;
        }
    }

    handleNewMessage(data) {
        if (this.currentChat && this.currentChat.id === data.conversation_id) {
            this.addMessageToChat(data.message);
        }
        this.loadChats(); // Update chat list
    }

    switchTab(tabName) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // Load data for tab
        switch (tabName) {
            case 'chats':
                this.loadChats();
                break;
            case 'orders':
                this.loadOrders();
                break;
            case 'customers':
                this.loadCustomers();
                break;
            case 'reports':
                this.loadReports();
                break;
        }
    }

    async loadChats() {
        try {
            const status = document.getElementById('status-filter').value;
            const url = status === 'all' ? '/api/chats' : `/api/chats?status=${status}`;

            const response = await fetch(url);
            const chats = await response.json();

            this.renderChats(chats);
        } catch (error) {
            console.error('Erro ao carregar conversas:', error);
        }
    }

    renderChats(chats) {
        const container = document.getElementById('chats-list');
        container.innerHTML = '';

        if (chats.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhuma conversa encontrada</p>';
            return;
        }

        chats.forEach(chat => {
            const chatElement = document.createElement('div');
            chatElement.className = `chat-item ${this.currentChat && this.currentChat.id === chat.id ? 'active' : ''}`;
            chatElement.onclick = () => this.openChat(chat);

            chatElement.innerHTML = `
                <div class="chat-info">
                    <div class="chat-name">${chat.profile_name || chat.phone_number}</div>
                    <div class="chat-last-message">${chat.last_message || 'Nova conversa'}</div>
                </div>
                <div class="chat-meta">
                    <span class="chat-time">${this.formatTime(chat.last_message_at)}</span>
                    <span class="chat-status status-${chat.status}">${chat.status}</span>
                </div>
            `;

            container.appendChild(chatElement);
        });
    }

    openChat(chat) {
        this.currentChat = chat;

        // Update chat header
        document.getElementById('chat-contact-name').textContent = chat.profile_name || chat.phone_number;

        // Open panel
        document.getElementById('chat-panel').classList.add('open');

        // Load messages
        this.loadChatMessages(chat.id);

        // Update active chat in list
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        event.target.closest('.chat-item').classList.add('active');
    }

    closeChatPanel() {
        document.getElementById('chat-panel').classList.remove('open');
        this.currentChat = null;

        // Remove active state from chat list
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
    }

    async loadChatMessages(chatId) {
        try {
            const response = await fetch(`/api/chats/${chatId}/messages`);
            const messages = await response.json();

            this.renderChatMessages(messages);
        } catch (error) {
            console.error('Erro ao carregar mensagens:', error);
        }
    }

    renderChatMessages(messages) {
        const container = document.getElementById('chat-messages');
        container.innerHTML = '';

        messages.forEach(message => {
            const messageElement = document.createElement('div');
            messageElement.className = `message ${message.direction}`;

            messageElement.innerHTML = `
                <div class="message-content">${message.content}</div>
                <div class="message-time">${this.formatTime(message.timestamp)}</div>
            `;

            container.appendChild(messageElement);
        });

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    addMessageToChat(message) {
        const container = document.getElementById('chat-messages');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.direction}`;

        messageElement.innerHTML = `
            <div class="message-content">${message.content}</div>
            <div class="message-time">${this.formatTime(message.timestamp)}</div>
        `;

        container.appendChild(messageElement);
        container.scrollTop = container.scrollHeight;
    }

    async sendMessage() {
        if (!this.currentChat) return;

        const input = document.getElementById('message-input');
        const content = input.value.trim();

        if (!content) return;

        try {
            const response = await fetch(`/api/chats/${this.currentChat.id}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    direction: 'outbound'
                })
            });

            if (response.ok) {
                input.value = '';
                // Message will be added via WebSocket
            }
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
        }
    }

    async loadOrders() {
        try {
            const response = await fetch('/api/orders');
            const orders = await response.json();

            this.renderOrders(orders);
        } catch (error) {
            console.error('Erro ao carregar pedidos:', error);
        }
    }

    renderOrders(orders) {
        const container = document.getElementById('orders-list');
        container.innerHTML = '';

        if (orders.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhum pedido encontrado</p>';
            return;
        }

        orders.forEach(order => {
            const orderElement = document.createElement('div');
            orderElement.className = 'order-item';

            orderElement.innerHTML = `
                <div class="order-info">
                    <div class="order-number">#${order.id}</div>
                    <div class="order-customer">${order.customer_name}</div>
                    <div class="order-products">${order.products}</div>
                </div>
                <div class="order-meta">
                    <div class="order-status status-${order.status}">${order.status}</div>
                    <div class="order-total">R$ ${order.total}</div>
                </div>
            `;

            container.appendChild(orderElement);
        });
    }

    async loadCustomers() {
        try {
            const response = await fetch('/api/customers');
            const customers = await response.json();

            this.renderCustomers(customers);
        } catch (error) {
            console.error('Erro ao carregar clientes:', error);
        }
    }

    renderCustomers(customers) {
        const container = document.getElementById('customers-list');
        container.innerHTML = '';

        if (customers.length === 0) {
            container.innerHTML = '<p class="empty-state">Nenhum cliente encontrado</p>';
            return;
        }

        customers.forEach(customer => {
            const customerElement = document.createElement('div');
            customerElement.className = 'customer-item';

            customerElement.innerHTML = `
                <div class="customer-info">
                    <div class="customer-name">${customer.name}</div>
                    <div class="customer-phone">${customer.phone}</div>
                    <div class="customer-address">${customer.address || 'Endereço não informado'}</div>
                </div>
                <div class="customer-meta">
                    <div class="customer-orders">${customer.total_orders || 0} pedidos</div>
                </div>
            `;

            container.appendChild(customerElement);
        });
    }

    async loadReports() {
        try {
            const response = await fetch('/api/reports/dashboard');
            const data = await response.json();

            this.updateReports(data);
        } catch (error) {
            console.error('Erro ao carregar relatórios:', error);
            // Fallback data
            this.updateReports({
                orders_today: 0,
                revenue_today: 0,
                active_chats: 0,
                new_customers: 0
            });
        }
    }

    updateReports(data) {
        document.getElementById('orders-today').textContent = data.orders_today;
        document.getElementById('revenue-today').textContent = `R$ ${data.revenue_today.toFixed(2)}`;
        document.getElementById('active-chats').textContent = data.active_chats;
        document.getElementById('new-customers').textContent = data.new_customers;
    }

    updateTime() {
        const now = new Date();
        document.getElementById('current-time').textContent =
            now.toLocaleString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    logout() {
        if (confirm('Tem certeza que deseja sair?')) {
            // Clear any stored tokens/session
            window.location.href = '/static/index.html';
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DashboardApp();
});