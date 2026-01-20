import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import './OwnerDashboard.css';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface Metrics {
  revenueToday: number;
  ordersToday: number;
  newCustomers: number;
  avgRating: number;
  revenueChange: number;
  ordersChange: number;
  customersChange: number;
  ratingChange: number;
}

interface Activity {
  type: string;
  description: string;
  timestamp: string;
}

interface Product {
  name: string;
  sales: number;
  revenue: number;
}

interface ChartData {
  sales?: {
    labels: string[];
    data: number[];
  };
  ordersStatus?: number[];
}

interface Settings {
  businessHours: string;
  deliveryFee: number;
  minOrder: number;
  autoAcceptOrders: boolean;
}

const API_BASE = '/api';

export default function OwnerDashboard() {
  const [metrics, setMetrics] = useState<Metrics>({
    revenueToday: 0,
    ordersToday: 0,
    newCustomers: 0,
    avgRating: 0,
    revenueChange: 0,
    ordersChange: 0,
    customersChange: 0,
    ratingChange: 0,
  });
  const [activities, setActivities] = useState<Activity[]>([]);
  const [topProducts, setTopProducts] = useState<Product[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<Settings>({
    businessHours: '',
    deliveryFee: 0,
    minOrder: 0,
    autoAcceptOrders: false,
  });
  const [salesChartData, setSalesChartData] = useState<{
    labels: string[];
    datasets: { label: string; data: number[]; borderColor: string; backgroundColor: string; tension: number }[];
  }>({
    labels: [],
    datasets: [{
      label: 'Vendas (R$)',
      data: [],
      borderColor: '#4CAF50',
      backgroundColor: 'rgba(76, 175, 80, 0.1)',
      tension: 0.4,
    }],
  });
  const [ordersStatusData, setOrdersStatusData] = useState<{
    labels: string[];
    datasets: { data: number[]; backgroundColor: string[] }[];
  }>({
    labels: ['Pendente', 'Confirmado', 'Em Transito', 'Entregue', 'Cancelado'],
    datasets: [{
      data: [0, 0, 0, 0, 0],
      backgroundColor: ['#FFC107', '#2196F3', '#FF9800', '#4CAF50', '#F44336'],
    }],
  });

  const token = localStorage.getItem('access_token') || localStorage.getItem('token');
  const refreshIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchAPI = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    const defaultOptions: RequestInit = {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...((options.headers as Record<string, string>) || {}),
      },
    };

    try {
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
    } catch (error) {
      console.error('API Error:', error);
      return null;
    }
  }, [token]);

  const loadDashboardData = useCallback(async () => {
    try {
      // Try to load owner dashboard data
      const response = await fetchAPI('/dashboard/owner');

      if (response && response.ok) {
        const data = await response.json();

        if (data.metrics) {
          setMetrics(data.metrics);
        }

        if (data.activity) {
          setActivities(data.activity);
        }

        if (data.topProducts) {
          setTopProducts(data.topProducts);
        }

        if (data.chartData) {
          if (data.chartData.sales) {
            setSalesChartData({
              labels: data.chartData.sales.labels,
              datasets: [{
                label: 'Vendas (R$)',
                data: data.chartData.sales.data,
                borderColor: '#4CAF50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                tension: 0.4,
              }],
            });
          }

          if (data.chartData.ordersStatus) {
            setOrdersStatusData(prev => ({
              ...prev,
              datasets: [{
                ...prev.datasets[0],
                data: data.chartData.ordersStatus,
              }],
            }));
          }
        }
      } else {
        // Fallback: load data from existing endpoints
        await loadFallbackData();
      }
    } catch (error) {
      console.error('Erro ao carregar dados do dashboard:', error);
      await loadFallbackData();
    }
  }, [fetchAPI]);

  const loadFallbackData = useCallback(async () => {
    try {
      // Load orders for today
      const ordersResponse = await fetchAPI('/orders/today');
      if (ordersResponse && ordersResponse.ok) {
        const orders = await ordersResponse.json();

        const revenue = orders
          .filter((o: { status: string }) => o.status !== 'cancelled')
          .reduce((sum: number, o: { total_amount?: number }) => sum + parseFloat(String(o.total_amount || 0)), 0);

        const statusCounts = {
          pending: orders.filter((o: { status: string }) => o.status === 'pending').length,
          paid: orders.filter((o: { status: string }) => o.status === 'paid').length,
          dispatched: orders.filter((o: { status: string }) => o.status === 'dispatched').length,
          delivered: orders.filter((o: { status: string }) => o.status === 'delivered').length,
          cancelled: orders.filter((o: { status: string }) => o.status === 'cancelled').length,
        };

        setMetrics(prev => ({
          ...prev,
          revenueToday: revenue,
          ordersToday: orders.length,
        }));

        setOrdersStatusData(prev => ({
          ...prev,
          datasets: [{
            ...prev.datasets[0],
            data: [statusCounts.pending, statusCounts.paid, statusCounts.dispatched, statusCounts.delivered, statusCounts.cancelled],
          }],
        }));

        // Create activity from recent orders
        const recentActivities: Activity[] = orders.slice(0, 5).map((order: { id: string; order_number?: number; created_at: string }) => ({
          type: 'order',
          description: `Pedido #${order.order_number || order.id} criado`,
          timestamp: order.created_at,
        }));
        setActivities(recentActivities);
      }

      // Load products
      const productsResponse = await fetchAPI('/products');
      if (productsResponse && productsResponse.ok) {
        const products = await productsResponse.json();
        setTopProducts(products.slice(0, 5).map((p: { name: string; price?: number }) => ({
          name: p.name,
          sales: Math.floor(Math.random() * 50) + 10, // Placeholder
          revenue: (p.price || 0) * (Math.floor(Math.random() * 50) + 10),
        })));
      }

      // Generate sample sales chart data
      const last7Days = Array.from({ length: 7 }, (_, i) => {
        const date = new Date();
        date.setDate(date.getDate() - (6 - i));
        return date.toLocaleDateString('pt-BR', { weekday: 'short' });
      });

      setSalesChartData({
        labels: last7Days,
        datasets: [{
          label: 'Vendas (R$)',
          data: Array.from({ length: 7 }, () => Math.floor(Math.random() * 1000) + 500),
          borderColor: '#4CAF50',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          tension: 0.4,
        }],
      });
    } catch (error) {
      console.error('Erro ao carregar dados fallback:', error);
    }
  }, [fetchAPI]);

  const loadSettings = useCallback(async () => {
    try {
      const response = await fetchAPI('/settings');
      if (response && response.ok) {
        const data = await response.json();
        setSettings({
          businessHours: data.businessHours || '',
          deliveryFee: data.deliveryFee || 0,
          minOrder: data.minOrder || 0,
          autoAcceptOrders: data.autoAcceptOrders || false,
        });
      }
    } catch (error) {
      console.error('Erro ao carregar configuracoes:', error);
    }
  }, [fetchAPI]);

  const saveSettings = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const response = await fetchAPI('/settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
      });

      if (response && response.ok) {
        alert('Configuracoes salvas com sucesso!');
        setShowSettings(false);
      } else {
        alert('Erro ao salvar configuracoes');
      }
    } catch (error) {
      alert('Erro de conexao');
    }
  };

  const getActivityIcon = (type: string) => {
    const icons: Record<string, string> = {
      order: 'box',
      payment: 'money',
      customer: 'users',
      delivery: 'truck',
      system: 'cog',
    };
    return icons[type] || 'file';
  };

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date();
    const time = new Date(timestamp);
    const diff = now.getTime() - time.getTime();

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (days > 0) return `${days} dia${days > 1 ? 's' : ''} atras`;
    if (hours > 0) return `${hours} hora${hours > 1 ? 's' : ''} atras`;
    if (minutes > 0) return `${minutes} minuto${minutes > 1 ? 's' : ''} atras`;
    return 'Agora';
  };

  const exportReport = () => {
    alert('Funcionalidade de exportacao em desenvolvimento');
  };

  useEffect(() => {
    // TODO: Implementar autenticação adequada
    // Por enquanto, permite acesso sem token para desenvolvimento

    loadDashboardData();

    // Auto refresh every 5 minutes
    refreshIntervalRef.current = setInterval(loadDashboardData, 300000);

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [token, loadDashboardData]);

  const salesChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: function(value: string | number) {
            return 'R$ ' + Number(value).toFixed(2);
          },
        },
      },
    },
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
  };

  return (
    <div className="owner-dashboard">
      <div className="owner-container">
        {/* Header */}
        <header className="owner-header">
          <h1>Painel do Dono</h1>
          <nav className="owner-nav">
            <a href="/" className="owner-nav-link">Voltar ao Dashboard</a>
            <a href="/admin" className="owner-nav-link">Painel Admin</a>
          </nav>
        </header>

        {/* Overview Cards */}
        <div className="overview-cards">
          <div className="metric-card">
            <div className="metric-icon">$</div>
            <div className="metric-content">
              <h3>Receita Hoje</h3>
              <div className="metric-value">R$ {metrics.revenueToday.toFixed(2)}</div>
              <div className={`metric-change ${metrics.revenueChange >= 0 ? 'positive' : 'negative'}`}>
                {metrics.revenueChange >= 0 ? '+' : ''}{metrics.revenueChange.toFixed(1)}%
              </div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">B</div>
            <div className="metric-content">
              <h3>Pedidos Hoje</h3>
              <div className="metric-value">{metrics.ordersToday}</div>
              <div className={`metric-change ${metrics.ordersChange >= 0 ? 'positive' : 'negative'}`}>
                {metrics.ordersChange >= 0 ? '+' : ''}{metrics.ordersChange.toFixed(1)}%
              </div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">U</div>
            <div className="metric-content">
              <h3>Novos Clientes</h3>
              <div className="metric-value">{metrics.newCustomers}</div>
              <div className={`metric-change ${metrics.customersChange >= 0 ? 'positive' : 'negative'}`}>
                {metrics.customersChange >= 0 ? '+' : ''}{metrics.customersChange.toFixed(1)}%
              </div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon">*</div>
            <div className="metric-content">
              <h3>Avaliacao Media</h3>
              <div className="metric-value">{metrics.avgRating.toFixed(1)}</div>
              <div className={`metric-change ${metrics.ratingChange >= 0 ? 'positive' : 'negative'}`}>
                {metrics.ratingChange >= 0 ? '+' : ''}{metrics.ratingChange.toFixed(1)}%
              </div>
            </div>
          </div>
        </div>

        {/* Charts Section */}
        <div className="charts-section">
          <div className="chart-container">
            <h3>Vendas por Periodo</h3>
            <div style={{ height: '300px' }}>
              <Line data={salesChartData} options={salesChartOptions} />
            </div>
          </div>

          <div className="chart-container">
            <h3>Pedidos por Status</h3>
            <div style={{ height: '300px' }}>
              <Doughnut data={ordersStatusData} options={doughnutOptions} />
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="activity-section">
          <h3>Atividades Recentes</h3>
          <div className="activity-list">
            {activities.length === 0 ? (
              <div className="empty-state">Nenhuma atividade recente</div>
            ) : (
              activities.map((activity, index) => (
                <div key={index} className="activity-item">
                  <div className="activity-icon">{getActivityIcon(activity.type)}</div>
                  <div className="activity-content">
                    <div className="activity-text">{activity.description}</div>
                    <div className="activity-time">{formatTimeAgo(activity.timestamp)}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="quick-actions">
          <h3>Acoes Rapidas</h3>
          <div className="action-buttons">
            <button className="action-btn btn-primary" onClick={() => window.location.href = '/admin'}>
              + Novo Pedido
            </button>
            <button className="action-btn btn-secondary" onClick={exportReport}>
              Relatorio
            </button>
            <button className="action-btn btn-secondary" onClick={() => window.location.href = '/admin'}>
              Ver Logs
            </button>
            <button className="action-btn btn-warning" onClick={() => { setShowSettings(true); loadSettings(); }}>
              Configuracoes
            </button>
          </div>
        </div>

        {/* Top Products */}
        <div className="top-products">
          <h3>Produtos Mais Vendidos</h3>
          <div className="products-list">
            {topProducts.length === 0 ? (
              <div className="empty-state">Nenhum produto encontrado</div>
            ) : (
              topProducts.map((product, index) => (
                <div key={index} className="product-item">
                  <div className="product-name">{product.name}</div>
                  <div className="product-sales">{product.sales} vendas</div>
                  <div className="product-revenue">R$ {product.revenue.toFixed(2)}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Configuracoes do Sistema</h3>
              <span className="modal-close" onClick={() => setShowSettings(false)}>&times;</span>
            </div>
            <div className="modal-body">
              <form onSubmit={saveSettings}>
                <div className="form-group">
                  <label htmlFor="business-hours">Horario de Funcionamento</label>
                  <input
                    type="text"
                    id="business-hours"
                    placeholder="Ex: 8:00-18:00"
                    value={settings.businessHours}
                    onChange={(e) => setSettings({ ...settings, businessHours: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="delivery-fee">Taxa de Entrega (R$)</label>
                  <input
                    type="number"
                    id="delivery-fee"
                    step="0.01"
                    placeholder="0.00"
                    value={settings.deliveryFee}
                    onChange={(e) => setSettings({ ...settings, deliveryFee: parseFloat(e.target.value) || 0 })}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="min-order">Pedido Minimo (R$)</label>
                  <input
                    type="number"
                    id="min-order"
                    step="0.01"
                    placeholder="0.00"
                    value={settings.minOrder}
                    onChange={(e) => setSettings({ ...settings, minOrder: parseFloat(e.target.value) || 0 })}
                  />
                </div>

                <div className="form-group checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      id="auto-accept-orders"
                      checked={settings.autoAcceptOrders}
                      onChange={(e) => setSettings({ ...settings, autoAcceptOrders: e.target.checked })}
                    />
                    Aceitar pedidos automaticamente
                  </label>
                </div>

                <div className="form-actions">
                  <button type="submit" className="btn-primary">Salvar</button>
                  <button type="button" className="btn-secondary" onClick={() => setShowSettings(false)}>
                    Cancelar
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
