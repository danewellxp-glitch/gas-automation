"""
Serviço de Geocoding para endereços.
Usa Nominatim (OpenStreetMap) - gratuito, sem API key.
"""

import logging
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "GasAutomation/1.0 (delivery-tracking)"


def _build_address_string(delivery_address: Optional[dict], bairro: Optional[str]) -> str:
    """Monta string de endereço a partir do dict ou bairro."""
    if delivery_address and isinstance(delivery_address, dict):
        parts = []
        if delivery_address.get("street"):
            parts.append(delivery_address["street"])
        if delivery_address.get("number"):
            parts.append(str(delivery_address["number"]))
        if delivery_address.get("complement"):
            parts.append(delivery_address["complement"])
        if delivery_address.get("bairro"):
            parts.append(delivery_address["bairro"])
        elif bairro:
            parts.append(bairro)
        if delivery_address.get("city"):
            parts.append(delivery_address["city"])
        if delivery_address.get("cep"):
            parts.append(f"CEP {delivery_address['cep']}")
        if parts:
            return ", ".join(parts)
    if bairro:
        return bairro
    return ""


async def geocode_address(
    delivery_address: Optional[dict],
    bairro: Optional[str],
    city_hint: str = "Curitiba, Paraná, Brasil",
) -> Optional[Tuple[float, float]]:
    """
    Geocodifica endereço e retorna (lat, lng) ou None.

    Args:
        delivery_address: Dict com street, number, bairro, city, cep
        bairro: Bairro da entrega (fallback)
        city_hint: Cidade padrão para busca (evita ambiguidade)
    """
    addr_str = _build_address_string(delivery_address, bairro)
    if not addr_str:
        return None

    # Adiciona cidade se não tiver
    if "curitiba" not in addr_str.lower() and "paraná" not in addr_str.lower():
        addr_str = f"{addr_str}, {city_hint}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                NOMINATIM_URL,
                params={
                    "q": addr_str,
                    "format": "json",
                    "limit": 1,
                },
                headers={"User-Agent": USER_AGENT},
            )
            r.raise_for_status()
            data = r.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                logger.info(f"Geocodificado: {addr_str[:50]}... -> ({lat}, {lon})")
                return (lat, lon)
    except Exception as e:
        logger.warning(f"Geocoding falhou para '{addr_str[:50]}': {e}")
    return None


def haversine_distance_km(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    Calcula distância em km entre dois pontos (fórmula de Haversine).
    """
    import math
    R = 6371  # Raio da Terra em km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
