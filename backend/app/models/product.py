"""
Modelo de Produto.
Catálogo de botijões de gás (P13, P20, P45) e galões de água (G20L).
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Product(BaseModel):
    """
    Modelo de Produto.

    Attributes:
        code: Código do produto (P13, P20, P45, G20L)
        name: Nome completo do produto
        description: Descrição detalhada
        categoria: Categoria do produto (gas, agua, outro)
        weight_kg: Peso em kg (nullable para produtos de água)
        volume_litros: Volume em litros (para galões de água)
        requer_retorno_vasilhame: Se o vasilhame vazio deve ser devolvido
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
        comment="Código do produto (P13, P20, P45, G20L)"
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
        comment="Nome completo (ex: Botijão P13 - 13kg, Galão de Água 20L)"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Descrição detalhada"
    )
    categoria: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="gas",
        server_default="gas",
        comment="Categoria: gas, agua, outro"
    )
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Peso em kg (nulo para produtos de água)"
    )
    volume_litros: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Volume em litros (para galões de água: 20)"
    )
    requer_retorno_vasilhame: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Se o vasilhame vazio deve retornar"
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
        Index("ix_products_categoria", "categoria"),
    )

    def __repr__(self) -> str:
        return f"<Product(code={self.code}, name={self.name}, price={self.price})>"

    @property
    def display_name(self) -> str:
        """Nome para exibição no bot."""
        if self.categoria == "agua" and self.volume_litros:
            return f"{self.code} ({self.volume_litros}L) - R$ {self.price:.2f}"
        return f"{self.code} ({self.weight_kg}kg) - R$ {self.price:.2f}"

    @property
    def button_text(self) -> str:
        """Texto para botão do WhatsApp."""
        return f"{self.code} - R$ {self.price:.0f}"


# NOTA: Produtos devem ser sincronizados do Firebird (Gerente.fdb)
# Não usar dados hardcoded em produção
# Para sincronização inicial, usar: backend/scripts/sync_products_from_firebird.py


# ===== CONSTANTES DE PRODUTO =====
# Códigos padrão de produtos de gás (usados para detecção em mensagens)
DEFAULT_PRODUCT_CODES = ["P13", "P20", "P45"]

# Todos os produtos (incluindo água)
ALL_PRODUCT_CODES = ["P13", "P20", "P45", "G20L"]

# Mapeamento de peso -> código (gás)
WEIGHT_TO_CODE = {
    "13": "P13",
    "20": "P20",
    "45": "P45",
}

# Mapeamento de opção numérica -> código (para menu do bot)
OPTION_TO_CODE = {
    "1": "P13",
    "2": "P20",
    "3": "P45",
    "4": "G20L",
}
