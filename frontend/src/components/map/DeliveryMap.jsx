import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Truck, User, RefreshCw } from 'lucide-react';

// Corrigir icones do Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Icones customizados
const createIcon = (color, type) => {
  const svgIcon = type === 'driver'
    ? `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="${color}" stroke="white" stroke-width="2"><rect x="1" y="3" width="15" height="13" rx="2"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>`
    : `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="${color}" stroke="white" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3" fill="white"/></svg>`;

  return L.divIcon({
    html: svgIcon,
    className: 'custom-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

const driverIcon = createIcon('#3B82F6', 'driver'); // Azul
const customerIcon = createIcon('#EF4444', 'customer'); // Vermelho
const pendingIcon = createIcon('#F59E0B', 'customer'); // Amarelo

export default function DeliveryMap({
  drivers = [],
  deliveries = [],
  customerLocations = [],
  center = [-25.4284, -49.2733], // Curitiba
  zoom = 13,
  height = '400px',
  onDriverClick,
  onDeliveryClick,
  autoRefresh = true,
  refreshInterval = 30000
}) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({ drivers: {}, deliveries: {}, customers: {} });
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [isLoading, setIsLoading] = useState(false);

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

    // Remover marcadores antigos
    Object.values(markersRef.current.drivers).forEach(marker => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current.drivers = {};

    // Adicionar novos marcadores
    drivers.forEach(driver => {
      if (!driver.location?.latitude || !driver.location?.longitude) return;

      const marker = L.marker(
        [driver.location.latitude, driver.location.longitude],
        { icon: driverIcon }
      ).addTo(mapInstanceRef.current);

      marker.bindPopup(`
        <div class="p-2">
          <strong>${driver.name || 'Entregador'}</strong><br/>
          <span class="text-sm text-gray-600">${driver.phone || ''}</span><br/>
          <span class="text-xs text-gray-400">
            Atualizado: ${new Date(driver.location.timestamp || Date.now()).toLocaleTimeString()}
          </span>
        </div>
      `);

      if (onDriverClick) {
        marker.on('click', () => onDriverClick(driver));
      }

      markersRef.current.drivers[driver.id] = marker;
    });

    setLastUpdate(new Date());
  }, [drivers, onDriverClick]);

  // Atualizar marcadores de entregas
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    // Remover marcadores antigos
    Object.values(markersRef.current.deliveries).forEach(marker => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current.deliveries = {};

    // Adicionar novos marcadores
    deliveries.forEach(delivery => {
      if (!delivery.location?.latitude || !delivery.location?.longitude) return;

      const isPending = delivery.status === 'pending';
      const marker = L.marker(
        [delivery.location.latitude, delivery.location.longitude],
        { icon: isPending ? pendingIcon : customerIcon }
      ).addTo(mapInstanceRef.current);

      marker.bindPopup(`
        <div class="p-2">
          <strong>Pedido #${delivery.order_id?.slice(0, 8) || 'N/A'}</strong><br/>
          <span class="text-sm">${delivery.customer_name || 'Cliente'}</span><br/>
          <span class="text-xs ${isPending ? 'text-yellow-600' : 'text-green-600'}">
            ${delivery.status || 'pendente'}
          </span><br/>
          ${delivery.address ? `<span class="text-xs text-gray-500">${delivery.address}</span>` : ''}
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

    // Remover marcadores antigos
    Object.values(markersRef.current.customers).forEach(marker => {
      mapInstanceRef.current.removeLayer(marker);
    });
    markersRef.current.customers = {};

    // Adicionar novos marcadores
    customerLocations.forEach((loc, index) => {
      if (!loc.latitude || !loc.longitude) return;

      const marker = L.marker(
        [loc.latitude, loc.longitude],
        { icon: customerIcon }
      ).addTo(mapInstanceRef.current);

      marker.bindPopup(`
        <div class="p-2">
          <strong>${loc.name || 'Cliente'}</strong><br/>
          <span class="text-sm text-gray-600">${loc.phone || ''}</span><br/>
          ${loc.address ? `<span class="text-xs text-gray-500">${loc.address}</span>` : ''}
        </div>
      `);

      markersRef.current.customers[index] = marker;
    });
  }, [customerLocations]);

  // Centralizar no marcador
  const centerOnLocation = (lat, lng) => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([lat, lng], 15);
    }
  };

  // Ajustar zoom para mostrar todos os marcadores
  const fitAllMarkers = () => {
    if (!mapInstanceRef.current) return;

    const allMarkers = [
      ...Object.values(markersRef.current.drivers),
      ...Object.values(markersRef.current.deliveries),
      ...Object.values(markersRef.current.customers),
    ];

    if (allMarkers.length === 0) return;

    const group = L.featureGroup(allMarkers);
    mapInstanceRef.current.fitBounds(group.getBounds().pad(0.1));
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-gray-800">Mapa de Entregas</h3>
        </div>
        <div className="flex items-center gap-4">
          {/* Legenda */}
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1">
              <Truck className="w-4 h-4 text-blue-500" />
              Entregadores ({drivers.length})
            </span>
            <span className="flex items-center gap-1">
              <MapPin className="w-4 h-4 text-red-500" />
              Entregas ({deliveries.length})
            </span>
            <span className="flex items-center gap-1">
              <User className="w-4 h-4 text-yellow-500" />
              Pendentes
            </span>
          </div>
          {/* Botoes */}
          <button
            onClick={fitAllMarkers}
            className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
            title="Ajustar zoom"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
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
          Atualizado: {lastUpdate.toLocaleTimeString()}
        </span>
        {autoRefresh && (
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Atualizacao automatica
          </span>
        )}
      </div>
    </div>
  );
}
