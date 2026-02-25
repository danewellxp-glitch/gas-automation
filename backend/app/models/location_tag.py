"""
Sistema de Tags para Localizações no Mapa.
Define categorias visuais para entidades (clientes, entregadores, entregas).
"""

from enum import Enum
from typing import Dict, Any


class LocationTag(str, Enum):
    """Tags para categorização de localizações no mapa."""
    
    # Clientes
    CUSTOMER_NEW = "customer_new"
    CUSTOMER_RECURRING = "customer_recurring"
    CUSTOMER_VIP = "customer_vip"
    
    # Entregadores
    DRIVER_AVAILABLE = "driver_available"
    DRIVER_BUSY = "driver_busy"
    DRIVER_OFFLINE = "driver_offline"
    DRIVER_ON_BREAK = "driver_on_break"
    
    # Entregas
    DELIVERY_PENDING = "delivery_pending"
    DELIVERY_IN_TRANSIT = "delivery_in_transit"
    DELIVERY_ARRIVED = "delivery_arrived"
    DELIVERY_DELAYED = "delivery_delayed"
    
    # Pedidos
    ORDER_PENDING_PAYMENT = "order_pending_payment"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_PREPARING = "order_preparing"


# Configuração de cores, ícones e labels para cada tag
TAG_CONFIG: Dict[str, Dict[str, Any]] = {
    # Clientes
    LocationTag.CUSTOMER_NEW: {
        "color": "#3B82F6",  # Azul
        "icon": "user-plus",
        "label": "Cliente Novo",
        "category": "customers"
    },
    LocationTag.CUSTOMER_RECURRING: {
        "color": "#10B981",  # Verde
        "icon": "user-check",
        "label": "Cliente Recorrente",
        "category": "customers"
    },
    LocationTag.CUSTOMER_VIP: {
        "color": "#F59E0B",  # Laranja/Dourado
        "icon": "crown",
        "label": "Cliente VIP",
        "category": "customers"
    },
    
    # Entregadores
    LocationTag.DRIVER_AVAILABLE: {
        "color": "#22C55E",  # Verde claro
        "icon": "truck",
        "label": "Disponível",
        "category": "drivers"
    },
    LocationTag.DRIVER_BUSY: {
        "color": "#EF4444",  # Vermelho
        "icon": "truck-loading",
        "label": "Em Entrega",
        "category": "drivers"
    },
    LocationTag.DRIVER_OFFLINE: {
        "color": "#6B7280",  # Cinza
        "icon": "truck",
        "label": "Offline",
        "category": "drivers"
    },
    LocationTag.DRIVER_ON_BREAK: {
        "color": "#F59E0B",  # Laranja
        "icon": "coffee",
        "label": "Em Pausa",
        "category": "drivers"
    },
    
    # Entregas
    LocationTag.DELIVERY_PENDING: {
        "color": "#A855F7",  # Roxo claro
        "icon": "clock",
        "label": "Pendente",
        "category": "deliveries"
    },
    LocationTag.DELIVERY_IN_TRANSIT: {
        "color": "#8B5CF6",  # Roxo
        "icon": "package",
        "label": "Em Trânsito",
        "category": "deliveries"
    },
    LocationTag.DELIVERY_ARRIVED: {
        "color": "#06B6D4",  # Ciano
        "icon": "map-pin",
        "label": "Chegou ao Destino",
        "category": "deliveries"
    },
    LocationTag.DELIVERY_DELAYED: {
        "color": "#DC2626",  # Vermelho escuro
        "icon": "alert-circle",
        "label": "Atrasada",
        "category": "deliveries"
    },
    
    # Pedidos
    LocationTag.ORDER_PENDING_PAYMENT: {
        "color": "#FBBF24",  # Amarelo
        "icon": "dollar-sign",
        "label": "Aguardando Pagamento",
        "category": "orders"
    },
    LocationTag.ORDER_CONFIRMED: {
        "color": "#10B981",  # Verde
        "icon": "check-circle",
        "label": "Pedido Confirmado",
        "category": "orders"
    },
    LocationTag.ORDER_PREPARING: {
        "color": "#F97316",  # Laranja
        "icon": "shopping-bag",
        "label": "Em Preparação",
        "category": "orders"
    },
}


def get_tag_for_driver(driver) -> str:
    """
    Determina a tag apropriada para um entregador baseado no status.
    
    Args:
        driver: Objeto Driver com status
        
    Returns:
        Tag do LocationTag
    """
    status = getattr(driver, 'status', 'offline').lower()
    
    if status in ['available', 'online']:
        return LocationTag.DRIVER_AVAILABLE
    elif status == 'busy':
        return LocationTag.DRIVER_BUSY
    elif status == 'break':
        return LocationTag.DRIVER_ON_BREAK
    else:
        return LocationTag.DRIVER_OFFLINE


def get_tag_for_customer(customer=None, order_count: int = 0) -> str:
    """
    Determina a tag apropriada para um cliente baseado no histórico.
    
    Args:
        customer: Objeto Customer (opcional)
        order_count: Número de pedidos do cliente
        
    Returns:
        Tag do LocationTag
    """
    if order_count == 0:
        return LocationTag.CUSTOMER_NEW
    elif order_count >= 10:
        return LocationTag.CUSTOMER_VIP
    else:
        return LocationTag.CUSTOMER_RECURRING


def get_tag_for_delivery(delivery) -> str:
    """
    Determina a tag apropriada para uma entrega baseado no status.
    
    Args:
        delivery: Objeto Delivery com status
        
    Returns:
        Tag do LocationTag
    """
    from datetime import datetime, timezone, timedelta
    
    status = getattr(delivery, 'status', 'pending').lower()
    
    # Verificar se está atrasada
    created_at = getattr(delivery, 'created_at', None)
    if created_at and status in ['in_transit', 'assigned', 'picked_up']:
        time_elapsed = datetime.now(timezone.utc) - created_at
        # Considerar atrasada após 1 hora
        if time_elapsed > timedelta(hours=1):
            return LocationTag.DELIVERY_DELAYED
    
    if status in ['in_transit', 'picked_up']:
        return LocationTag.DELIVERY_IN_TRANSIT
    elif status == 'arrived':
        return LocationTag.DELIVERY_ARRIVED
    else:
        return LocationTag.DELIVERY_PENDING


def get_tag_for_order(order) -> str:
    """
    Determina a tag apropriada para um pedido baseado no status.
    
    Args:
        order: Objeto Order com status
        
    Returns:
        Tag do LocationTag
    """
    status = getattr(order, 'status', 'pending').lower()
    
    if status == 'pending':
        return LocationTag.ORDER_PENDING_PAYMENT
    elif status in ['paid', 'dispatched']:
        return LocationTag.ORDER_CONFIRMED
    elif status == 'preparing':
        return LocationTag.ORDER_PREPARING
    else:
        return LocationTag.ORDER_CONFIRMED


def get_tag_config(tag: str) -> Dict[str, Any]:
    """
    Retorna a configuração visual de uma tag.
    
    Args:
        tag: Tag do LocationTag
        
    Returns:
        Dicionário com color, icon, label, category
    """
    return TAG_CONFIG.get(tag, {
        "color": "#9CA3AF",  # Cinza padrão
        "icon": "map-pin",
        "label": "Desconhecido",
        "category": "other"
    })


def get_all_tag_configs() -> Dict[str, Dict[str, Any]]:
    """
    Retorna todas as configurações de tags disponíveis.
    
    Returns:
        Dicionário completo TAG_CONFIG
    """
    return TAG_CONFIG


def get_tags_by_category() -> Dict[str, list]:
    """
    Retorna tags agrupadas por categoria.
    
    Returns:
        Dicionário com categorias como chaves e listas de tags como valores
    """
    categories = {}
    for tag, config in TAG_CONFIG.items():
        category = config.get("category", "other")
        if category not in categories:
            categories[category] = []
        categories[category].append(tag)
    
    return categories
