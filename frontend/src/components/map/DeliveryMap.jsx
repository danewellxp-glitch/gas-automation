import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Truck, RefreshCw, Clock, Navigation, CheckCircle } from 'lucide-react';

// Corrigir icones do Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Configuracao de status para o mapa
const STATUS_CONFIG = {
  pending: {
    color: '#F59E0B',
    bgColor: '#FEF3C7',
    borderColor: '#D97706',
    label: 'Pendente',
    pinColor: '#F59E0B',
  },
  in_route: {
    color: '#3B82F6',
    bgColor: '#DBEAFE',
    borderColor: '#2563EB',
    label: 'Em Rota',
    pinColor: '#3B82F6',
  },
  completed: {
    color: '#10B981',
    bgColor: '#D1FAE5',
    borderColor: '#059669',
    label: 'Concluido',
    pinColor: '#10B981',
  },
};

// Criar icone de pin com tag de status
const createOrderIcon = (status) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="36" height="50" viewBox="0 0 36 50">
      <path d="M18 0C8.06 0 0 8.06 0 18c0 13.5 18 32 18 32s18-18.5 18-32C36 8.06 27.94 0 18 0z" fill="${config.pinColor}" stroke="white" stroke-width="2"/>
      <circle cx="18" cy="18" r="8" fill="white"/>
      <text x="18" y="22" text-anchor="middle" font-size="12" font-weight="bold" fill="${config.pinColor}">#</text>
    </svg>
  `;
  return L.divIcon({
    html: `<div style="position:relative;display:inline-block;">
      ${svg}
      <span style="
        position:absolute;
        top:-8px;
        left:28px;
        background:${config.bgColor};
        color:${config.color};
        border:1px solid ${config.borderColor};
        border-radius:4px;
        padding:1px 6px;
        font-size:10px;
        font-weight:600;
        white-space:nowrap;
        box-shadow:0 1px 3px rgba(0,0,0,0.15);
      ">${config.label}</span>
    </div>`,
    className: 'order-marker',
    iconSize: [36, 50],
    iconAnchor: [18, 50],
    popupAnchor: [0, -50],
  });
};

// Icone de entregador (caminhao azul)
const driverIcon = L.divIcon({
  html: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#3B82F6" stroke="white" stroke-width="2">
    <rect x="1" y="3" width="15" height="13" rx="2"/>
    <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
    <circle cx="5.5" cy="18.5" r="2.5"/>
    <circle cx="18.5" cy="18.5" r="2.5"/>
  </svg>`,
  className: 'custom-marker',
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
});

export default function DeliveryMap({
  drivers = [],
  orders = [],
  deliveries = [],
  customerLocations = [],
  center = [-25.4284, -49.2733], // Curitiba
  zoom = 13,
  height = '500px',
  onDriverClick,
  onOrderClick,
  onDeliveryClick,
  autoRefresh = true,
}) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({ drivers: {}, orders: {}, deliveries: {}, customers: {} });
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Inicializar mapa
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    mapInstanceRef.current = L.map(mapRef.current).setView(center, zoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(mapInstanceRef.current);

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Atualizar marcadores de entregadores
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    Object.values(markersRef.current.drivers).forEach(marker => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current.drivers = {};

    drivers.forEach(driver => {
      if (!driver.location?.latitude || !driver.location?.longitude) return;

      const marker = L.marker(
        [driver.location.latitude, driver.location.longitude],
        { icon: driverIcon }
      ).addTo(mapInstanceRef.current);

      marker.bindPopup(`
        <div style="min-width:180px;padding:4px">
          <div style="font-weight:700;font-size:14px;margin-bottom:4px">${driver.name || 'Entregador'}</div>
          ${driver.phone ? `<div style="color:#6B7280;font-size:12px">${driver.phone}</div>` : ''}
          <div style="margin-top:4px;display:flex;align-items:center;gap:4px">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${driver.status === 'available' ? '#10B981' : '#6B7280'}"></span>
            <span style="font-size:11px;color:#6B7280">${driver.status === 'available' ? 'Disponivel' : driver.status}</span>
          </div>
          ${driver.active_deliveries > 0 ? `<div style="margin-top:4px;font-size:11px;color:#3B82F6">${driver.active_deliveries} entrega(s) ativa(s)</div>` : ''}
          ${driver.location.timestamp ? `<div style="margin-top:4px;font-size:10px;color:#9CA3AF">Atualizado: ${new Date(driver.location.timestamp).toLocaleTimeString('pt-BR')}</div>` : ''}
        </div>
      `);

      if (onDriverClick) {
        marker.on('click', () => onDriverClick(driver));
      }

      markersRef.current.drivers[driver.id] = marker;
    });

    setLastUpdate(new Date());
  }, [drivers, onDriverClick]);

  // Atualizar marcadores de pedidos (com tags de status)
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    Object.values(markersRef.current.orders).forEach(marker => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current.orders = {};

    orders.forEach(order => {
      if (!order.latitude || !order.longitude) return;

      const config = STATUS_CONFIG[order.status] || STATUS_CONFIG.pending;
      const icon = createOrderIcon(order.status);

      const marker = L.marker(
        [order.latitude, order.longitude],
        { icon }
      ).addTo(mapInstanceRef.current);

      const timeStr = order.created_at
        ? new Date(order.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
        : '';

      marker.bindPopup(`
        <div style="min-width:200px;padding:4px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
            <span style="font-weight:700;font-size:14px">Pedido #${order.order_number || 'N/A'}</span>
            <span style="
              background:${config.bgColor};
              color:${config.color};
              border:1px solid ${config.borderColor};
              border-radius:4px;
              padding:2px 8px;
              font-size:11px;
              font-weight:600;
            ">${config.label}</span>
          </div>
          ${order.customer_name ? `<div style="font-size:13px;color:#374151">${order.customer_name}</div>` : ''}
          ${order.customer_phone ? `<div style="font-size:12px;color:#6B7280">${order.customer_phone}</div>` : ''}
          ${order.address ? `<div style="margin-top:4px;font-size:12px;color:#6B7280">${order.address}</div>` : ''}
          ${order.driver_name ? `<div style="margin-top:4px;font-size:12px;color:#3B82F6">Entregador: ${order.driver_name}</div>` : ''}
          ${timeStr ? `<div style="margin-top:4px;font-size:10px;color:#9CA3AF">${timeStr}</div>` : ''}
        </div>
      `);

      if (onOrderClick) {
        marker.on('click', () => onOrderClick(order));
      }

      markersRef.current.orders[order.id] = marker;
    });
  }, [orders, onOrderClick]);

  // Atualizar marcadores de entregas (compatibilidade)
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    Object.values(markersRef.current.deliveries).forEach(marker => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current.deliveries = {};

    deliveries.forEach(delivery => {
      if (!delivery.location?.latitude || !delivery.location?.longitude) return;

      const marker = L.marker(
        [delivery.location.latitude, delivery.location.longitude],
        { icon: createOrderIcon('in_route') }
      ).addTo(mapInstanceRef.current);

      marker.bindPopup(`
        <div style="min-width:180px;padding:4px">
          <div style="font-weight:700;font-size:14px">Entrega</div>
          ${delivery.customer_name ? `<div style="font-size:13px;color:#374151">${delivery.customer_name}</div>` : ''}
          <div style="font-size:12px;color:#6B7280">${delivery.status || 'em andamento'}</div>
          ${delivery.address ? `<div style="font-size:12px;color:#6B7280">${delivery.address}</div>` : ''}
          ${delivery.driver_name ? `<div style="margin-top:4px;font-size:12px;color:#3B82F6">Entregador: ${delivery.driver_name}</div>` : ''}
        </div>
      `);

      if (onDeliveryClick) {
        marker.on('click', () => onDeliveryClick(delivery));
      }

      markersRef.current.deliveries[delivery.id] = marker;
    });
  }, [deliveries, onDeliveryClick]);

  // Atualizar marcadores de clientes (localizacoes recebidas)
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    Object.values(markersRef.current.customers).forEach(marker => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current.customers = {};

    customerLocations.forEach((loc, index) => {
      if (!loc.latitude || !loc.longitude) return;

      const customerIcon = L.divIcon({
        html: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="#8B5CF6" stroke="white" stroke-width="2">
          <circle cx="12" cy="8" r="5"/>
          <path d="M20 21a8 8 0 1 0-16 0"/>
        </svg>`,
        className: 'custom-marker',
        iconSize: [24, 24],
        iconAnchor: [12, 24],
        popupAnchor: [0, -24],
      });

      const marker = L.marker(
        [loc.latitude, loc.longitude],
        { icon: customerIcon }
      ).addTo(mapInstanceRef.current);

      marker.bindPopup(`
        <div style="min-width:160px;padding:4px">
          <div style="font-weight:700;font-size:13px">${loc.name || 'Cliente'}</div>
          ${loc.phone ? `<div style="font-size:12px;color:#6B7280">${loc.phone}</div>` : ''}
          ${loc.address ? `<div style="font-size:12px;color:#6B7280">${loc.address}</div>` : ''}
        </div>
      `);

      markersRef.current.customers[index] = marker;
    });
  }, [customerLocations]);

  // Ajustar zoom para mostrar todos os marcadores
  const fitAllMarkers = () => {
    if (!mapInstanceRef.current) return;

    const allMarkers = [
      ...Object.values(markersRef.current.drivers),
      ...Object.values(markersRef.current.orders),
      ...Object.values(markersRef.current.deliveries),
      ...Object.values(markersRef.current.customers),
    ];

    if (allMarkers.length === 0) return;

    const group = L.featureGroup(allMarkers);
    mapInstanceRef.current.fitBounds(group.getBounds().pad(0.1));
  };

  // Contagens de pedidos por status
  const ordersByStatus = {
    pending: orders.filter(o => o.status === 'pending').length,
    in_route: orders.filter(o => o.status === 'in_route').length,
    completed: orders.filter(o => o.status === 'completed').length,
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {/* Header com legenda */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-gray-800">Mapa de Pedidos - Hoje</h3>
          </div>
          <button
            onClick={fitAllMarkers}
            className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
            title="Ajustar zoom para mostrar todos"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Legenda de status */}
        <div className="flex items-center gap-4 text-xs flex-wrap">
          <span className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            <span className="text-amber-700 font-medium">Pendente ({ordersByStatus.pending})</span>
          </span>
          <span className="flex items-center gap-1.5">
            <Navigation className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-blue-700 font-medium">Em Rota ({ordersByStatus.in_route})</span>
          </span>
          <span className="flex items-center gap-1.5">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-emerald-700 font-medium">Concluido ({ordersByStatus.completed})</span>
          </span>
          <span className="flex items-center gap-1.5">
            <Truck className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-gray-600">Entregadores ({drivers.filter(d => d.location).length})</span>
          </span>
        </div>
      </div>

      {/* Mapa */}
      <div
        ref={mapRef}
        style={{ height, width: '100%' }}
        className="z-0"
      />

      {/* Footer */}
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
        <span>
          Atualizado: {lastUpdate.toLocaleTimeString('pt-BR')}
        </span>
        <div className="flex items-center gap-3">
          <span>{orders.length} pedidos no mapa</span>
          {autoRefresh && (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              Live
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
