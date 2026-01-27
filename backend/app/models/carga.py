"""
Modelo de Carga de Veículo.
Controla produtos que o entregador leva e acerto no fim do dia.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import DateTime, Index, String, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class CargaStatus(str, enum.Enum):
    """Status da carga."""
    CRIADA = "criada"           # Carga criada, aguardando saída
    EM_ROTA = "em_rota"         # Motorista saiu com a carga
    FINALIZADA = "finalizada"   # Acerto realizado


class CargaVeiculo(BaseModel):
    """
    Modelo de Carga do Veículo.

    Representa a carga diária que um motorista leva para entregas.

    Attributes:
        driver_id: ID do motorista responsável
        data_saida: Data/hora que saiu para entregas
        data_retorno: Data/hora que retornou
        status: Status atual da carga
        observacoes: Observações gerais
    """

    __tablename__ = "cargas_veiculo"

    # Relacionamento com motorista
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id"),
        nullable=False,
        index=True,
        comment="ID do motorista responsável"
    )

    # Datas
    data_saida: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora da saída para entregas"
    )
    data_retorno: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora do retorno"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=CargaStatus.CRIADA.value,
        nullable=False,
        index=True,
        comment="Status: criada, em_rota, finalizada"
    )

    # Observações
    observacoes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Observações gerais"
    )

    # Índices
    __table_args__ = (
        Index("ix_cargas_driver_status", "driver_id", "status"),
        Index("ix_cargas_data_saida", "data_saida"),
    )

    # Relacionamentos
    driver: Mapped["Driver"] = relationship(
        "Driver",
        back_populates="cargas"
    )
    itens: Mapped[List["CargaItem"]] = relationship(
        "CargaItem",
        back_populates="carga",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CargaVeiculo(id={self.id}, driver_id={self.driver_id}, status={self.status})>"

    def registrar_saida(self):
        """Registra saída do motorista."""
        self.status = CargaStatus.EM_ROTA.value
        self.data_saida = datetime.now()
        return self

    def finalizar(self):
        """Finaliza a carga (acerto realizado)."""
        self.status = CargaStatus.FINALIZADA.value
        self.data_retorno = datetime.now()
        return self


class CargaItem(BaseModel):
    """
    Modelo de Item da Carga.

    Representa cada produto na carga do veículo.

    Attributes:
        carga_id: ID da carga
        produto_id: ID do produto
        qtd_saida: Quantidade que saiu (cheios)
        qtd_retorno_cheio: Quantidade que retornou cheia
        qtd_retorno_vazio: Quantidade de vazios retornados
        qtd_vendida: Quantidade efetivamente vendida
    """

    __tablename__ = "carga_itens"

    # Relacionamentos
    carga_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cargas_veiculo.id"),
        nullable=False,
        index=True,
        comment="ID da carga"
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=False,
        index=True,
        comment="ID do produto"
    )

    # Quantidades
    qtd_saida: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Quantidade que saiu (cheios)"
    )
    qtd_retorno_cheio: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Quantidade que retornou cheia"
    )
    qtd_retorno_vazio: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Quantidade de vazios retornados"
    )
    qtd_vendida: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Quantidade efetivamente vendida"
    )

    # Índices
    __table_args__ = (
        Index("ix_carga_itens_carga_produto", "carga_id", "produto_id"),
    )

    # Relacionamentos
    carga: Mapped["CargaVeiculo"] = relationship(
        "CargaVeiculo",
        back_populates="itens"
    )
    produto: Mapped["Product"] = relationship("Product")

    def __repr__(self) -> str:
        return f"<CargaItem(carga_id={self.carga_id}, produto_id={self.produto_id}, qtd_saida={self.qtd_saida})>"

    @property
    def qtd_pendente(self) -> int:
        """Calcula quantidade ainda não contabilizada."""
        return self.qtd_saida - self.qtd_vendida - self.qtd_retorno_cheio

    def validar_acerto(self) -> bool:
        """Valida se o acerto está correto (saída = vendida + retornos)."""
        total_retorno = self.qtd_vendida + self.qtd_retorno_cheio
        return total_retorno <= self.qtd_saida
