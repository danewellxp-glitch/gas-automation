"""
Modelo de Entregador (Driver).
Gerencia entregadores e motoristas.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, Index, String, Text, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DriverStatus(str, enum.Enum):
    """Status do entregador."""
    OFFLINE = "offline"           # Fora do sistema
    AVAILABLE = "available"       # Disponível para entregas
    BUSY = "busy"                 # Em entrega
    BREAK = "break"              # Em pausa


class Driver(BaseModel):
    """
    Modelo de Entregador.

    Attributes:
        name: Nome completo
        phone: Telefone para contato
        email: Email (opcional)
        vehicle_type: Tipo de veículo
        license_plate: Placa do veículo
        status: Status atual
        current_location: Localização GPS atual
        rating: Avaliação média
        total_deliveries: Total de entregas realizadas
    """

    __tablename__ = "drivers"

    # Dados pessoais
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nome completo do entregador"
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment="Telefone para contato"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Email opcional"
    )

    # Veículo
    vehicle_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Tipo de veículo (moto, carro, etc.)"
    )
    license_plate: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Placa do veículo"
    )

    # Status operacional
    status: Mapped[str] = mapped_column(
        String(20),
        default=DriverStatus.OFFLINE.value,
        nullable=False,
        index=True,
        comment="Status atual do entregador"
    )

    # Localização
    current_location: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Localização atual: {'latitude': float, 'longitude': float, 'timestamp': datetime}"
    )

    # Estatísticas
    rating: Mapped[float] = mapped_column(
        default=5.0,
        nullable=False,
        comment="Avaliação média (0-5)"
    )
    total_deliveries: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Total de entregas realizadas"
    )

    # Configurações
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Se o entregador está ativo no sistema"
    )

    # Timestamps
    last_online: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Última vez que ficou online"
    )

    # Índices
    __table_args__ = (
        Index("ix_drivers_status_active", "status", "is_active"),
        # ix_drivers_phone já é criado automaticamente pelo unique=True no campo phone
    )

    # Relacionamentos
    time_logs: Mapped[List["DriverTimeLog"]] = relationship(
        "DriverTimeLog",
        back_populates="driver",
        cascade="all, delete-orphan"
    )
    cargas: Mapped[List["CargaVeiculo"]] = relationship(
        "CargaVeiculo",
        back_populates="driver",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, name={self.name}, status={self.status})>"

    def go_online(self):
        """Coloca entregador online"""
        self.status = DriverStatus.AVAILABLE.value
        self.last_online = datetime.now()
        return self

    def go_offline(self):
        """Coloca entregador offline"""
        self.status = DriverStatus.OFFLINE.value
        return self

    def start_delivery(self):
        """Marca como ocupado (em entrega)"""
        self.status = DriverStatus.BUSY.value
        return self

    def finish_delivery(self):
        """Volta para disponível após entrega"""
        self.status = DriverStatus.AVAILABLE.value
        self.total_deliveries += 1
        return self

    @property
    def is_available(self) -> bool:
        """Verifica se está disponível para entregas"""
        return self.status == DriverStatus.AVAILABLE.value and self.is_active

    @property
    def display_name(self) -> str:
        """Nome para exibição"""
        return f"{self.name} ({self.vehicle_type or 'Sem veículo'})"