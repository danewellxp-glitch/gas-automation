"""
"""
Serviço de Geocoding com fallback estratégico.
Converte CEPs em coordenadas geográficas usando múltiplas APIs brasileiras.
BrasilAPI v2 (primário) + Nominatim/OpenStreetMap (fallback).
"""

import json
import logging
import httpx
import re
import math
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

BRASILAPI_CEP_URL = "https://brasilapi.com.br/api/cep/v2"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "GasAutomation/1.0 (delivery-tracking)"
GEOCODE_CACHE_TTL = 86400  # 24 horas

class GeocodingService:
    """
    Serviço de geocodificação com cache e fallback.
    
    Estratégia:
    1. Verificar cache Redis (rápido)
    2. Verificar cache DB (persistente)
    3. Tentar CEPAberto (se token disponível) → coordenadas + endereço
    4. Tentar ViaCEP → apenas endereço
    5. Tentar Nominatim → coordenadas do endereço
    """
    
    # Tempo de cache: 30 dias
    CACHE_TTL = 30 * 24 * 60 * 60
    
    def __init__(self, db: AsyncSession, redis_manager=None):
        """
        Inicializa o serviço de geocoding.
        
        Args:
            db: Sessão assíncrona do banco de dados
            redis_manager: Gerenciador Redis (opcional)
        """
        self.db = db
        self.redis = redis_manager
        
        # Token CEPAberto (opcional)
        import os
        self.cepaberto_token = os.getenv("CEPABERTO_TOKEN")
    
    async def geocode_by_cep(self, cep: str) -> Optional[Dict[str, Any]]:
        """
        Geocodifica um CEP usando estratégia de fallback.
        
        Args:
            cep: CEP (com ou sem formatação)
            
        Returns:
            {
                "cep": "80010000",
                "logradouro": "Rua XV de Novembro",
                "bairro": "Centro",
                "cidade": "Curitiba",
                "estado": "PR",
                "latitude": -25.428954,
                "longitude": -49.273386,
                "source": "cepaberto",
                "accuracy": "street"
            }
        """
        # Limpar CEP (apenas dígitos)
        cep_clean = self._clean_cep(cep)
        
        if not cep_clean or len(cep_clean) != 8:
            logger.warning(f"CEP inválido: {cep}")
            return None
        
        # 1. Verificar cache Redis
        if self.redis:
            cached = await self._get_from_redis(cep_clean)
            if cached:
                logger.info(f"Geocoding cache HIT (Redis): {cep_clean}")
                return cached
        
        # 2. Verificar cache DB
        db_cached = await self._get_from_db_cache(cep_clean)
        if db_cached:
            logger.info(f"Geocoding cache HIT (DB): {cep_clean}")
            
            # Salvar no Redis para próximas consultas
            if self.redis:
                await self._save_to_redis(cep_clean, db_cached)
            
            return db_cached
        
        # 3. Tentar APIs externas
        logger.info(f"Geocoding cache MISS: {cep_clean} - Consultando APIs externas")
        
        result = None
        
        # 3.1. CEPAberto (retorna coordenadas)
        if self.cepaberto_token:
            result = await self._try_cepaberto(cep_clean)
            if result:
                await self._save_to_cache(cep_clean, result)
                return result
        
        # 3.2. ViaCEP (apenas endereço)
        viacep_result = await self._try_viacep(cep_clean)
        if viacep_result:
            # 3.3. Tentar Nominatim para obter coordenadas
            address_str = self._build_address_string(viacep_result)
            coords = await self._try_nominatim(address_str)
            
            if coords:
                result = {
                    **viacep_result,
                    "latitude": coords["latitude"],
                    "longitude": coords["longitude"],
                    "source": "viacep+nominatim",
                    "accuracy": "neighborhood"
                }
            else:
                result = {
                    **viacep_result,
                    "latitude": None,
                    "longitude": None,
                    "source": "viacep",
                    "accuracy": "cep_only"
                }
            
            await self._save_to_cache(cep_clean, result)
            return result
        
        logger.warning(f"Geocoding falhou para CEP: {cep_clean}")
        return None
    
    async def geocode_by_address(self, address: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Geocodifica um endereço completo usando Nominatim.
        
        Args:
            address: Dicionário com street, number, bairro, cidade, estado, cep
            
        Returns:
            Mesmo formato de geocode_by_cep()
        """
        # Se tem CEP, usar geocode_by_cep
        if address.get("cep"):
            return await self.geocode_by_cep(address["cep"])
        
        # Caso contrário, usar Nominatim com endereço completo
        address_str = self._build_address_string(address)
        coords = await self._try_nominatim(address_str)
        
        if coords:
            return {
                "cep": address.get("cep"),
                "logradouro": address.get("street"),
                "bairro": address.get("bairro"),
                "cidade": address.get("cidade"),
                "estado": address.get("estado"),
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
                "source": "nominatim",
                "accuracy": "approximate"
            }
        
        return None
    
    # ==================== Métodos Privados ====================
    
    def _clean_cep(self, cep: str) -> str:
        """Remove formatação do CEP, mantendo apenas dígitos."""
        if not cep:
            return ""
        return re.sub(r'\D', '', str(cep))
    
    def _build_address_string(self, address: Dict[str, Any]) -> str:
        """Constrói string de endereço para geocoding."""
        parts = []
        
        if address.get("logradouro") or address.get("street"):
            parts.append(address.get("logradouro") or address.get("street"))
        
        if address.get("number"):
            parts.append(str(address["number"]))
        
        if address.get("bairro"):
            parts.append(address["bairro"])
        
        if address.get("cidade") or address.get("localidade"):
            cidade = address.get("cidade") or address.get("localidade")
            estado = address.get("estado") or address.get("uf")
            if estado:
                parts.append(f"{cidade}, {estado}")
            else:
                parts.append(cidade)
        
        parts.append("Brasil")
        
        return ", ".join(parts)
    
    async def _try_cepaberto(self, cep: str) -> Optional[Dict[str, Any]]:
        """
        Tenta geocodificar via CEPAberto (retorna coordenadas).
        
        Requer token de acesso (gratuito até 10k req/mês).
        """
        if not self.cepaberto_token:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://www.cepaberto.com/api/v3/cep?cep={cep}",
                    headers={"Authorization": f"Token token={self.cepaberto_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    logger.info(f"CEPAberto SUCCESS: {cep}")
                    
                    return {
                        "cep": cep,
                        "logradouro": data.get("logradouro"),
                        "bairro": data.get("bairro"),
                        "cidade": data["cidade"]["nome"],
                        "estado": data["estado"]["sigla"],
                        "latitude": float(data["latitude"]) if data.get("latitude") else None,
                        "longitude": float(data["longitude"]) if data.get("longitude") else None,
                        "source": "cepaberto",
                        "accuracy": "street"
                    }
                else:
                    logger.warning(f"CEPAberto erro {response.status_code}: {cep}")
        
        except Exception as e:
            logger.warning(f"CEPAberto exception: {e}")
        
        return None
    
    async def _try_viacep(self, cep: str) -> Optional[Dict[str, Any]]:
        """
        Tenta buscar endereço via ViaCEP (sem coordenadas).
        
        API gratuita e sem autenticação.
        """
        try:
            # Usar API diretamente via httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"https://viacep.com.br/ws/{cep}/json/")
                
                if response.status_code == 200:
                    address = response.json()
                    
                    if address and not address.get("erro"):
                        logger.info(f"ViaCEP SUCCESS: {cep}")
                        
                        return {
                            "cep": address.get("cep", "").replace("-", ""),
                            "logradouro": address.get("logradouro"),
                            "bairro": address.get("bairro"),
                            "cidade": address.get("localidade"),
                            "estado": address.get("uf"),
                        }
                    else:
                        logger.warning(f"ViaCEP não encontrou: {cep}")
                else:
                    logger.warning(f"ViaCEP erro {response.status_code}: {cep}")
        
        except Exception as e:
            logger.warning(f"ViaCEP exception: {e}")
        
        return None
    
    async def _try_nominatim(self, address_str: str) -> Optional[Dict[str, float]]:
        """
        Tenta obter coordenadas via Nominatim (OpenStreetMap).
        
        Limite: 1 req/segundo
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": address_str,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": "br"
                    },
                    headers={"User-Agent": "GasAutomation/1.0"}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    
                    if results:
                        logger.info(f"Nominatim SUCCESS: {address_str[:50]}")
                        
                        return {
                            "latitude": float(results[0]["lat"]),
                            "longitude": float(results[0]["lon"])
                        }
                    else:
                        logger.warning(f"Nominatim não encontrou: {address_str[:50]}")
        
        except Exception as e:
            logger.warning(f"Nominatim exception: {e}")
        
        return None
    
    async def _get_from_redis(self, cep: str) -> Optional[Dict[str, Any]]:
        """Busca resultado no cache Redis."""
        if not self.redis:
            return None
        
        try:
            cache_key = f"geocoding:cep:{cep}"
            # RedisManager usa get_json para retornar dict diretamente
            if hasattr(self.redis, 'get_json'):
                cached = await self.redis.get_json(cache_key)
            else:
                # Fallback: não usar Redis se não tem método adequado
                return None
            return cached
        except Exception as e:
            logger.warning(f"Redis GET error: {e}")
            return None
    
    async def _get_from_db_cache(self, cep: str) -> Optional[Dict[str, Any]]:
        """Busca resultado no cache do banco de dados."""
        from app.models.geocoding_cache import GeocodingCache
        
        try:
            result = await self.db.execute(
                select(GeocodingCache).where(GeocodingCache.cep == cep)
            )
            cache = result.scalar_one_or_none()
            
            if cache:
                return {
                    "cep": cache.cep,
                    "logradouro": cache.logradouro,
                    "bairro": cache.bairro,
                    "cidade": cache.cidade,
                    "estado": cache.estado,
                    "latitude": float(cache.latitude) if cache.latitude else None,
                    "longitude": float(cache.longitude) if cache.longitude else None,
                    "source": cache.source or "cached",
                    "accuracy": "cached"
                }
        
        except Exception as e:
            logger.warning(f"DB cache GET error: {e}")
        
        return None
    
    async def _save_to_redis(self, cep: str, data: Dict[str, Any]):
        """Salva resultado no cache Redis."""
        if not self.redis:
            return
        
        try:
            cache_key = f"geocoding:cep:{cep}"
            # RedisManager usa set_json para salvar dict
            if hasattr(self.redis, 'set_json'):
                await self.redis.set_json(cache_key, data, ttl=self.CACHE_TTL)
            else:
                # Fallback: não usar Redis se não tem método adequado
                pass
        except Exception as e:
            logger.warning(f"Redis SET error: {e}")
    
    async def _save_to_cache(self, cep: str, data: Dict[str, Any]):
        """Salva resultado nos caches (Redis + DB)."""
        # Redis
        await self._save_to_redis(cep, data)
        
        # DB
        from app.models.geocoding_cache import GeocodingCache
        
        try:
            # Verificar se já existe
            result = await self.db.execute(
                select(GeocodingCache).where(GeocodingCache.cep == cep)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Atualizar
                existing.latitude = data.get("latitude")
                existing.longitude = data.get("longitude")
                existing.logradouro = data.get("logradouro")
                existing.bairro = data.get("bairro")
                existing.cidade = data.get("cidade")
                existing.estado = data.get("estado")
                existing.source = data.get("source")
            else:
                # Criar novo
                cache_obj = GeocodingCache(
                    cep=cep,
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    logradouro=data.get("logradouro"),
                    bairro=data.get("bairro"),
                    cidade=data.get("cidade"),
                    estado=data.get("estado"),
                    source=data.get("source")
                )
                self.db.add(cache_obj)
            
            await self.db.commit()
            logger.info(f"Geocoding salvo no cache DB: {cep}")
        
        except Exception as e:
            logger.error(f"Erro ao salvar no cache DB: {e}")
            await self.db.rollback()


# ==================== Funções Helper (Compatibilidade) ====================

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
    address: Dict[str, Any],
    bairro: Optional[str] = None,
    session: Optional[AsyncSession] = None
) -> Optional[Tuple[float, float]]:
    """
    Geocodifica endereço e retorna (lat, lng) ou None.
    Estratégia: BrasilAPI por CEP (primário) → Nominatim (fallback).
    
    Args:
        address: Dicionário com dados do endereço (street, cidade, estado, cep)
        bairro: Bairro (opcional, sobrescreve address.bairro)
        session: Sessão do banco de dados (opcional)
        
    Returns:
        (latitude, longitude) ou None
    """
    # 1. Tentar por CEP via BrasilAPI (mais confiável para endereços brasileiros)
    if address and address.get("cep"):
        coords = await geocode_by_cep(address["cep"])
        if coords:
            return coords

    # 2. Utilizar o GeocodingService se sessão fornecida
    if session:
        service = GeocodingService(session)
        if bairro:
            address = {**address, "bairro": bairro}
        result = await service.geocode_by_address(address)
        if result and result.get("latitude") and result.get("longitude"):
            return (result["latitude"], result["longitude"])

    # 3. Fallback: Nominatim (endereço completo)
    addr_str = _build_address_string(address, bairro) if '_build_address_string' in globals() else f"{address.get('street', '')} {address.get('number', '')} {bairro or address.get('bairro', '')} {address.get('cidade', '')} {address.get('estado', '')}"
    if not addr_str.strip():
        return None

    if "curitiba" not in addr_str.lower() and "paraná" not in addr_str.lower() and "pr" not in addr_str.lower():
        addr_str = f"{addr_str}, Curitiba, PR"

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
    lat1: float, 
    lon1: float, 
    lat2: float, 
    lon2: float
) -> float:
    """
    Calcula a distância entre dois pontos geográficos usando a fórmula de Haversine.
    
    Args:
        lat1: Latitude do ponto 1
        lon1: Longitude do ponto 1
        lat2: Latitude do ponto 2
        lon2: Longitude do ponto 2
        
    Returns:
        Distância em quilômetros
    """
    # Raio da Terra em km
    R = 6371.0
    
    # Converter graus para radianos
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferenças
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula de Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    
    return distance
