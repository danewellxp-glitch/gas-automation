/**
 * OrdersPinMap — Mapa de Pedidos em Andamento
 * Mapa Leaflet simples: pins coloridos por status nos endereços dos clientes.
 * Componente separado do DeliveryMap (que é para rastreio GPS de entregadores).
 */

import { useEffect, useRef, useCallback, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { RefreshCw, MapPin } from 'lucide-react'
import api from '../../services/api'

// Corrigir ícones padrão do Leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const STATUS_PIN = {
  pending:    { color: '#F59E0B', label: 'Pendente' },
  paid:       { color: '#3B82F6', label: 'Aprovado' },
  preparing:  { color: '#8B5CF6', label: 'Em preparo' },
  dispatched: { color: '#06B6D4', label: 'Em rota' },
}

const createPin = (status) => {
  const { color, label } = STATUS_PIN[status] || STATUS_PIN.pending
  return L.divIcon({
    html: `<div style="
      position:relative;
      display:flex;
      flex-direction:column;
      align-items:center;
    ">
      <div style="
        background:${color};
        color:white;
        font-size:10px;
        font-weight:700;
        padding:2px 6px;
        border-radius:4px;
        white-space:nowrap;
        box-shadow:0 1px 4px rgba(0,0,0,0.25);
        margin-bottom:2px;
      ">${label}</div>
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="28" viewBox="0 0 20 28">
        <path d="M10 0C4.48 0 0 4.48 0 10c0 7.5 10 18 10 18s10-10.5 10-18C20 4.48 15.52 0 10 0z"
          fill="${color}" stroke="white" stroke-width="1.5"/>
        <circle cx="10" cy="10" r="4" fill="white"/>
      </svg>
    </div>`,
    className: '',
    iconSize: [20, 42],
    iconAnchor: [10, 42],
    popupAnchor: [0, -44],
  })
}

export default function OrdersPinMap({ height = '360px' }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const markersRef = useRef({})
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [pinCount, setPinCount] = useState(0)

  // Buscar pedidos ativos com coordenadas do endpoint map-data
  const fetchOrders = useCallback(async () => {
    try {
      setLoading(true)
      const res = await api.get('/locations/map-data', {
        params: { today_only: true, include_offline_drivers: false },
      })
      const data = res.data
      // Pedidos não concluídos que tenham coordenadas
      const active = (data.orders || []).filter(
        o => !['delivered', 'cancelled'].includes(o.status) &&
             o.latitude && o.longitude
      )
      setOrders(active)
    } catch (err) {
      console.error('OrdersPinMap: erro ao buscar pedidos', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Inicializar mapa Leaflet
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    mapInstanceRef.current = L.map(mapRef.current, { zoomControl: true }).setView(
      [-25.4284, -49.2733], // Curitiba — ajuste para sua cidade
      13
    )

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap',
      maxZoom: 19,
    }).addTo(mapInstanceRef.current)

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  // Buscar dados ao montar + auto-refresh
  useEffect(() => {
    fetchOrders()
    const t = setInterval(fetchOrders, 60000)
    return () => clearInterval(t)
  }, [fetchOrders])

  // Atualizar pins quando orders mudam
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return

    // Remover pins antigos
    Object.values(markersRef.current).forEach(m => map.removeLayer(m))
    markersRef.current = {}

    let count = 0
    orders.forEach(order => {
      if (!order.latitude || !order.longitude) return

      const marker = L.marker(
        [order.latitude, order.longitude],
        { icon: createPin(order.status) }
      ).addTo(map)

      const statusLabel = STATUS_PIN[order.status]?.label || order.status
      const addr = order.address || order.delivery_address || ''

      marker.bindPopup(`
        <div style="min-width:180px;font-family:sans-serif">
          <div style="font-weight:700;font-size:13px;margin-bottom:4px">
            Pedido #${String(order.order_number || order.id).padStart(4, '0')}
          </div>
          <div style="
            display:inline-block;
            background:${STATUS_PIN[order.status]?.color || '#6b7280'}22;
            color:${STATUS_PIN[order.status]?.color || '#6b7280'};
            border:1px solid ${STATUS_PIN[order.status]?.color || '#6b7280'}66;
            border-radius:4px;
            padding:1px 7px;
            font-size:11px;
            font-weight:600;
            margin-bottom:6px;
          ">${statusLabel}</div>
          ${order.customer_name ? `<div style="font-size:12px;color:#374151">${order.customer_name}</div>` : ''}
          ${order.customer_phone ? `<div style="font-size:11px;color:#6b7280">${order.customer_phone}</div>` : ''}
          ${addr ? `<div style="font-size:11px;color:#6b7280;margin-top:3px">${addr}</div>` : ''}
          ${order.total_amount ? `<div style="font-size:12px;font-weight:600;color:#111827;margin-top:4px">
            ${new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(order.total_amount)}
          </div>` : ''}
        </div>
      `)

      markersRef.current[order.id] = marker
      count++
    })

    setPinCount(count)

    // Ajustar zoom para exibir todos os pins
    if (count > 0) {
      const group = L.featureGroup(Object.values(markersRef.current))
      map.fitBounds(group.getBounds().pad(0.15))
    }
  }, [orders])

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <MapPin className="w-3.5 h-3.5 text-gray-400 dark:text-gray-500" />
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Pedidos em Andamento</span>
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {loading ? '…' : `${pinCount} no mapa`}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {/* Legenda */}
          <div className="hidden sm:flex items-center gap-3">
            {Object.entries(STATUS_PIN).map(([, { color, label }]) => (
              <span key={label} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                <span className="text-xs text-gray-400 dark:text-gray-500">{label}</span>
              </span>
            ))}
          </div>
          <button
            onClick={fetchOrders}
            disabled={loading}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500 disabled:opacity-50 transition-colors"
            title="Atualizar mapa"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Mapa */}
      <div style={{ position: 'relative', height }}>
        <div ref={mapRef} style={{ height: '100%', width: '100%', zIndex: 0 }} />

        {/* Overlay de carregamento */}
        {loading && orders.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70 dark:bg-gray-800/70 z-10">
            <div className="w-6 h-6 animate-spin rounded-full border-2 border-gray-200 border-t-primary-500" />
          </div>
        )}

        {/* Empty state */}
        {!loading && orders.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/90 dark:bg-gray-800/90 z-10">
            <MapPin className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
            <p className="text-sm text-gray-400 dark:text-gray-500">Sem pedidos ativos com localização</p>
            <p className="text-xs text-gray-300 dark:text-gray-600 mt-1">Pedidos precisam ter endereço geocodificado</p>
          </div>
        )}
      </div>

    </div>
  )
}
