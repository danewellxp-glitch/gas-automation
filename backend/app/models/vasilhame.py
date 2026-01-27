"""
Modelos de Vasilhames e Controle de Comodato.
Gerencia botijões emprestados aos clientes.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer


class Vasilhame(BaseModel):
    """
    Tipo de Vasilhame (P13, P45, etc).

    Attributes:
        codigo: Código único (P13, P45, P20, etc)
        descricao: Descrição do vasilhame
        peso_kg: Peso do botijão vazio em kg
        valor_caucao: Valor da caução cobrada na venda
        firebird_id: ID no sistema legado
    """

    __tablename__ = "vasilhames"

    codigo: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="Código: P13, P45, P20, etc"
    )
    descricao: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Descrição do vasilhame"
    )
    peso_kg: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Peso do botijão vazio em kg"
    )
    valor_caucao: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Valor da caução para venda"
    )
    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    firebird_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        unique=True,
        nullable=True,
        comment="ID no Firebird (VASILHAMES.VASILHAME_ID)"
    )

    # Relacionamentos
    clientes_vasilhames: Mapped[List["ClienteVasilhame"]] = relationship(
        "ClienteVasilhame",
        back_populates="vasilhame",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Vasilhame(codigo={self.codigo}, caucao={self.valor_caucao})>"


class ClienteVasilhame(BaseModel):
    """
    Controle de vasilhames em posse do cliente (comodato).

    Attributes:
        customer_id: FK para cliente
        vasilhame_id: FK para tipo de vasilhame
        quantidade: Quantidade de botijões em posse
        valor_caucao_pago: Valor total de caução pago
        data_primeiro_emprestimo: Data do primeiro empréstimo
        observacoes: Observações sobre o comodato
    """

    __tablename__ = "cliente_vasilhames"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )
    vasilhame_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vasilhames.id", ondelete="RESTRICT"),
        nullable=False
    )
    quantidade: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Quantidade de botijões em posse do cliente"
    )
    valor_caucao_pago: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Valor total de caução pago pelo cliente"
    )
    data_primeiro_emprestimo: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data do primeiro empréstimo"
    )
    observacoes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Observações sobre o comodato"
    )

    # Relacionamentos
    customer: Mapped["Customer"] = relationship("Customer", back_populates="vasilhames")
    vasilhame: Mapped["Vasilhame"] = relationship("Vasilhame", back_populates="clientes_vasilhames")

    __table_args__ = (
        Index("ix_cliente_vasilhames_customer", "customer_id"),
        Index("ix_cliente_vasilhames_unique", "customer_id", "vasilhame_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ClienteVasilhame(customer={self.customer_id}, vasilhame={self.vasilhame_id}, qtd={self.quantidade})>"


class MovimentacaoVasilhame(BaseModel):
    """
    Histórico de movimentações de vasilhames.

    Attributes:
        cliente_vasilhame_id: FK para controle do cliente
        tipo: ENTRADA (venda/emprestimo) ou SAIDA (devolucao)
        quantidade: Quantidade movimentada
        order_id: Pedido relacionado (opcional)
        motivo: Motivo da movimentação
    """

    __tablename__ = "movimentacoes_vasilhame"

    cliente_vasilhame_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cliente_vasilhames.id", ondelete="CASCADE"),
        nullable=False
    )
    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="ENTRADA ou SAIDA"
    )
    quantidade: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Quantidade movimentada"
    )
    valor_caucao: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Valor de caução cobrado/devolvido"
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        comment="Pedido relacionado"
    )
    motivo: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Motivo: venda, troca, devolucao, ajuste"
    )
    observacoes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Relacionamentos
    cliente_vasilhame: Mapped["ClienteVasilhame"] = relationship("ClienteVasilhame")

    __table_args__ = (
        Index("ix_movimentacoes_cliente", "cliente_vasilhame_id"),
        Index("ix_movimentacoes_order", "order_id"),
    )

    def __repr__(self) -> str:
        return f"<MovimentacaoVasilhame(tipo={self.tipo}, qtd={self.quantidade})>"
