"""
Modelo de Cache de Geocoding.
Armazena resultados de geocodificação de CEPs para otimizar performance.
"""

from typing import Optional
from sqlalchemy import Index, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class GeocodingCache(BaseModel):
    """
    Cache de resultados de geocodificação.
    
    Attributes:
        cep: CEP (8 dígitos, sem formatação)
        latitude: Coordenada geográfica (latitude)
        longitude: Coordenada geográfica (longitude)
        logradouro: Nome da rua/avenida
        bairro: Bairro
        cidade: Cidade
        estado: Sigla do estado (UF)
        source: Fonte dos dados (cepaberto, viacep, nominatim)
    """
    
    __tablename__ = "geocoding_cache"
    
    # CEP (único)
    cep: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
        index=True,
        comment="CEP sem formatação (somente dígitos)"
    )
    
    # Coordenadas geográficas
    latitude: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 8),
        nullable=True,
        comment="Latitude (-90 a 90)"
    )
    longitude: Mapped[Optional[float]] = mapped_column(
        Numeric(11, 8),
        nullable=True,
        comment="Longitude (-180 a 180)"
    )
    
    # Endereço completo
    logradouro: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Rua, avenida, etc."
    )
    bairro: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Bairro"
    )
    cidade: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Cidade/município"
    )
    estado: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True,
        comment="UF (sigla do estado)"
    )
    
    # Metadados
    source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Fonte: cepaberto, viacep, nominatim"
    )
    
    # Índices compostos
    __table_args__ = (
        Index("ix_geocoding_cache_location", "latitude", "longitude"),
        Index("ix_geocoding_cache_bairro_cidade", "bairro", "cidade"),
    )
    
    def __repr__(self) -> str:
        return f"<GeocodingCache(cep={self.cep}, source={self.source})>"
    
    @property
    def has_coordinates(self) -> bool:
        """Verifica se possui coordenadas válidas."""
        return self.latitude is not None and self.longitude is not None
    
    @property
    def formatted_address(self) -> str:
        """Retorna endereço formatado."""
        parts = []
        if self.logradouro:
            parts.append(self.logradouro)
        if self.bairro:
            parts.append(self.bairro)
        if self.cidade and self.estado:
            parts.append(f"{self.cidade}/{self.estado}")
        
        return ", ".join(parts) if parts else self.cep
