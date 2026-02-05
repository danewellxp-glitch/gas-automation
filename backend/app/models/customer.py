"""
Modelo de Cliente.
Armazena dados dos clientes que fazem pedidos via WhatsApp.
"""

import uuid
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.tipo_preco import TipoPreco
    from app.models.vasilhame import ClienteVasilhame


class Customer(BaseModel):
    """
    Modelo de Cliente.

    Attributes:
        firebird_id: ID do cliente no sistema legado (Firebird)
        phone: Telefone WhatsApp (único, formato: 5541999999999)
        name: Nome completo do cliente
        email: Email (opcional, para Asaas)
        cpf_cnpj: CPF ou CNPJ (opcional, para Asaas)
        address: Endereço completo em JSON
        asaas_customer_id: ID do cliente no Asaas
        notes: Observações internas
    """

    __tablename__ = "customers"

    # Identificadores externos
    firebird_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        unique=True,
        nullable=True,
        comment="ID no sistema legado Firebird"
    )
    asaas_customer_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        comment="ID do cliente no Asaas"
    )

    # Dados básicos
    phone: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Telefone WhatsApp (ex: 5541999999999)"
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Nome completo"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email para notificações e Asaas"
    )
    cpf_cnpj: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="CPF ou CNPJ"
    )

    # Endereço estruturado
    address: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Endereço: {street, number, complement, bairro, city, state, cep}"
    )

    # Observações
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Observações internas"
    )

    # Tipo de preço (modalidade: varejo, atacado, funcionario, revenda)
    tipo_preco_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tipos_preco.id", ondelete="SET NULL"),
        nullable=True,
        comment="Modalidade de preço do cliente (null = varejo)"
    )

    # Relacionamentos
    tipo_preco: Mapped[Optional["TipoPreco"]] = relationship("TipoPreco")
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="customer",
        lazy="selectin"
    )
    vasilhames: Mapped[List["ClienteVasilhame"]] = relationship(
        "ClienteVasilhame",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    # Índices
    __table_args__ = (
        Index("ix_customers_phone_name", "phone", "name"),
        Index("ix_customers_cpf_cnpj", "cpf_cnpj"),
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, phone={self.phone}, name={self.name})>"

    @property
    def formatted_phone(self) -> str:
        """Retorna telefone formatado: (41) 99999-9999"""
        if len(self.phone) == 13:  # 5541999999999
            return f"({self.phone[2:4]}) {self.phone[4:9]}-{self.phone[9:]}"
        return self.phone

    @property
    def full_address(self) -> str:
        """Retorna endereço completo formatado."""
        if not self.address:
            return ""

        parts = []
        if self.address.get("street"):
            parts.append(self.address["street"])
        if self.address.get("number"):
            parts.append(self.address["number"])
        if self.address.get("complement"):
            parts.append(f"- {self.address['complement']}")
        if self.address.get("bairro"):
            parts.append(f"- {self.address['bairro']}")

        return ", ".join(parts)
