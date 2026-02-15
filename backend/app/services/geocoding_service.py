"""
Serviço de Geocoding para endereços.
BrasilAPI v2 (primário) + Nominatim/OpenStreetMap (fallback).
"""

import json
import logging
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

BRASILAPI_CEP_URL = "https://brasilapi.com.br/api/cep/v2"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "GasAutomation/1.0 (delivery-tracking)"
GEOCODE_CACHE_TTL = 86400  # 24 horas


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


async def geocode_by_cep(cep: str) -> Optional[Tuple[float, float]]:
    """
    Geocodifica via BrasilAPI v2 (retorna lat/lng do CEP).
    Usa cache Redis para evitar chamadas repetidas.
    """
    clean_cep = cep.replace("-", "").replace(".", "").replace(" ", "").strip()
    if len(clean_cep) != 8 or not clean_cep.isdigit():
        return None

    # Checar cache Redis
    try:
        from app.database import redis_manager
        cached = await redis_manager.client.get(f"geocode:cep:{clean_cep}")
        if cached:
            coords = json.loads(cached)
            return (coords[0], coords[1])
    except Exception:
        pass  # Redis indisponível, segue sem cache

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{BRASILAPI_CEP_URL}/{clean_cep}",
                headers={"User-Agent": USER_AGENT},
            )
            r.raise_for_status()
            data = r.json()
            loc = data.get("location", {})
            coords = loc.get("coordinates", {})
            lat = coords.get("latitude")
            lng = coords.get("longitude")
            if lat is not None and lng is not None:
                lat, lng = float(lat), float(lng)
                logger.info(f"BrasilAPI geocodificado CEP {clean_cep} -> ({lat}, {lng})")
                # Salvar no cache
                try:
                    from app.database import redis_manager
                    await redis_manager.client.set(
                        f"geocode:cep:{clean_cep}",
                        json.dumps([lat, lng]),
                        ex=GEOCODE_CACHE_TTL,
                    )
                except Exception:
                    pass
                return (lat, lng)
            else:
                logger.debug(f"BrasilAPI CEP {clean_cep}: sem coordenadas na resposta")
    except Exception as e:
        logger.warning(f"BrasilAPI geocoding falhou para CEP {clean_cep}: {e}")
    return None


async def geocode_address(
    delivery_address: Optional[dict],
    bairro: Optional[str],
    city_hint: str = "Curitiba, Paraná, Brasil",
) -> Optional[Tuple[float, float]]:
    """
    Geocodifica endereço e retorna (lat, lng) ou None.
    Estratégia: BrasilAPI por CEP (primário) → Nominatim (fallback).

    Args:
        delivery_address: Dict com street, number, bairro, city, cep
        bairro: Bairro da entrega (fallback)
        city_hint: Cidade padrão para busca (evita ambiguidade)
    """
    # 1. Tentar por CEP via BrasilAPI (mais confiável para endereços brasileiros)
    if delivery_address and delivery_address.get("cep"):
        coords = await geocode_by_cep(delivery_address["cep"])
        if coords:
            return coords

    # 2. Fallback: Nominatim (endereço completo)
    addr_str = _build_address_string(delivery_address, bairro)
    if not addr_str:
        return None

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
                logger.info(f"Nominatim geocodificado: {addr_str[:50]}... -> ({lat}, {lon})")
                return (lat, lon)
    except Exception as e:
        logger.warning(f"Nominatim geocoding falhou para '{addr_str[:50]}': {e}")
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
