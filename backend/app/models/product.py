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


# Dados iniciais para seed
DEFAULT_PRODUCTS = [
    {
        "code": "P13",
        "name": "Botijão P13 - 13kg",
        "description": "Botijão residencial padrão de 13kg. Ideal para uso doméstico.",
        "weight_kg": Decimal("13.00"),
        "price": Decimal("110.00"),
        "is_active": True,
    },
    {
        "code": "P20",
        "name": "Botijão P20 - 20kg",
        "description": "Botijão de 20kg. Indicado para residências com maior consumo ou pequenos comércios.",
        "weight_kg": Decimal("20.00"),
        "price": Decimal("150.00"),
        "is_active": True,
    },
    {
        "code": "P45",
        "name": "Botijão P45 - 45kg",
        "description": "Botijão comercial/industrial de 45kg. Para estabelecimentos com alto consumo.",
        "weight_kg": Decimal("45.00"),
        "price": Decimal("280.00"),
        "is_active": True,
    },
]
