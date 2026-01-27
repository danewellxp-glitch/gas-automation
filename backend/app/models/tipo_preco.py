"""
Modelos de Tipo de Preço e Preços por Produto.
Permite preços diferenciados por modalidade (varejo, atacado, funcionário, etc).
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.product import Product


class TipoPreco(BaseModel):
    """
    Tipo/Modalidade de Preço.

    Attributes:
        codigo: Código único (varejo, atacado, funcionario, revenda)
        descricao: Descrição para exibição
        percentual_desconto: Desconto padrão sobre preço varejo
        firebird_id: ID no sistema legado
    """

    __tablename__ = "tipos_preco"

    codigo: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="Código: varejo, atacado, funcionario, revenda"
    )
    descricao: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Descrição para exibição"
    )
    percentual_desconto: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Desconto padrão em % sobre preço varejo"
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
        comment="ID no Firebird (TIPOSPRECO.TIPOPRECO_ID)"
    )

    def __repr__(self) -> str:
        return f"<TipoPreco(codigo={self.codigo}, descricao={self.descricao})>"


class ProdutoPreco(BaseModel):
    """
    Preço específico de um produto para uma modalidade.

    Attributes:
        produto_id: FK para produto
        tipo_preco_id: FK para tipo de preço
        preco: Valor do preço
        vigencia_inicio: Data de início da vigência
        vigencia_fim: Data de fim (null = sem fim)
    """

    __tablename__ = "produto_precos"

    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    tipo_preco_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tipos_preco.id", ondelete="CASCADE"),
        nullable=False
    )
    preco: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Preço para esta modalidade"
    )
    vigencia_inicio: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Início da vigência"
    )
    vigencia_fim: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Fim da vigência (null = indefinido)"
    )

    # Relacionamentos
    produto: Mapped["Product"] = relationship("Product")
    tipo_preco: Mapped["TipoPreco"] = relationship("TipoPreco")

    __table_args__ = (
        Index("ix_produto_precos_busca", "produto_id", "tipo_preco_id", "vigencia_inicio"),
    )

    def __repr__(self) -> str:
        return f"<ProdutoPreco(produto={self.produto_id}, tipo={self.tipo_preco_id}, preco={self.preco})>"
