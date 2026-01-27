import { useState, useEffect, useCallback, useRef } from 'react';
import api from '../services/api';

/**
 * Hook para buscar e manter dados do mapa atualizados.
 * Integra com WebSocket para atualizacoes em tempo real.
 */
export default function useMapData({
  autoRefresh = true,
  refreshInterval = 30000, // 30 segundos
  includeOfflineDrivers = false,
  hoursBack = 24,
} = {}) {
  const [drivers, setDrivers] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [customerLocations, setCustomerLocations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const intervalRef = useRef(null);
  const wsRef = useRef(null);

  // Buscar dados do mapa
  const fetchMapData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await api.get('/api/locations/map-data', {
        params: {
          include_offline_drivers: includeOfflineDrivers,
          hours_back: hoursBack,
        },
      });

      const data = response.data;

      setDrivers(data.drivers || []);
      setDeliveries(data.deliveries || []);
      setCustomerLocations(data.customer_locations || []);
      setLastUpdate(new Date(data.updated_at));

    } catch (err) {
      console.error('Erro ao buscar dados do mapa:', err);
      setError(err.message || 'Erro ao carregar mapa');
    } finally {
      setIsLoading(false);
    }
  }, [includeOfflineDrivers, hoursBack]);

  // Atualizar localizacao de um entregador (via WebSocket)
  const handleDriverLocationUpdate = useCallback((data) => {
    const { driver_id, location } = data;

    setDrivers(prevDrivers =>
      prevDrivers.map(driver =>
        driver.id === driver_id
          ? { ...driver, location }
          : driver
      )
    );

    setLastUpdate(new Date());
  }, []);

  // Adicionar nova localizacao de cliente (via WebSocket)
  const handleCustomerLocationReceived = useCallback((data) => {
    const newLocation = {
      phone: data.phone,
      name: data.name,
      latitude: data.latitude,
      longitude: data.longitude,
      address: data.address,
      timestamp: new Date().toISOString(),
    };

    setCustomerLocations(prev => {
      // Remover localizacao antiga do mesmo telefone
      const filtered = prev.filter(loc => loc.phone !== data.phone);
      return [newLocation, ...filtered].slice(0, 100); // Manter max 100
    });

    setLastUpdate(new Date());
  }, []);

  // Configurar WebSocket
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/messages?token=${token}`;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          switch (message.type) {
            case 'driver_location_update':
              handleDriverLocationUpdate(message);
              break;
            case 'location_received':
            case 'new_message':
              // Verificar se e uma mensagem de localizacao
              if (message.content?.includes('Localização recebida')) {
                // Refetch para pegar nova localizacao
                fetchMapData();
              }
              break;
            case 'delivery_assigned':
            case 'order_update':
              // Refetch para atualizar entregas
              fetchMapData();
              break;
          }
        } catch (e) {
          console.warn('Erro ao processar mensagem WebSocket:', e);
        }
      };

      wsRef.current.onerror = (err) => {
        console.warn('WebSocket error:', err);
      };

    } catch (e) {
      console.warn('Erro ao conectar WebSocket:', e);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [handleDriverLocationUpdate, fetchMapData]);

  // Buscar dados iniciais
  useEffect(() => {
    fetchMapData();
  }, [fetchMapData]);

  // Auto refresh
  useEffect(() => {
    if (!autoRefresh) return;

    intervalRef.current = setInterval(fetchMapData, refreshInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, fetchMapData]);

  // Funcao para forcar refresh
  const refresh = useCallback(() => {
    return fetchMapData();
  }, [fetchMapData]);

  return {
    drivers,
    deliveries,
    customerLocations,
    isLoading,
    error,
    lastUpdate,
    refresh,
  };
}
