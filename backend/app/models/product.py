"""
Modelo de Produto.
Catálogo de botijões de gás (P13, P20, P45).
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Product(BaseModel):
    """
    Modelo de Produto (Botijão de Gás).

    Attributes:
        code: Código do produto (P13, P20, P45)
        name: Nome completo do produto
        description: Descrição detalhada
        weight_kg: Peso em kg
        price: Preço unitário
        is_active: Se está disponível para venda
        firebird_code: Código no sistema legado
    """

    __tablename__ = "products"

    # Identificação
    code: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
        index=True,
        comment="Código do produto (P13, P20, P45)"
    )
    firebird_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        comment="Código no sistema legado Firebird"
    )

    # Dados do produto
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Nome completo (ex: Botijão P13 - 13kg)"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Descrição detalhada"
    )
    weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Peso em kg"
    )

    # Preço
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Preço unitário em R$"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Se está disponível para venda"
    )

    # Índices
    __table_args__ = (
        Index("ix_products_active", "is_active", "code"),
    )

    def __repr__(self) -> str:
        return f"<Product(code={self.code}, name={self.name}, price={self.price})>"

    @property
    def display_name(self) -> str:
        """Nome para exibição no bot."""
        return f"{self.code} ({self.weight_kg}kg) - R$ {self.price:.2f}"

    @property
    def button_text(self) -> str:
        """Texto para botão do WhatsApp."""
        return f"{self.code} - R$ {self.price:.0f}"


# NOTA: Produtos devem ser sincronizados do Firebird (Gerente.fdb)
# Não usar dados hardcoded em produção
# Para sincronização inicial, usar: backend/scripts/sync_products_from_firebird.py
