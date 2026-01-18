"""
Schemas de Produto.
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class ProductBase(BaseSchema):
    """Schema base de produto."""

    code: str = Field(..., min_length=2, max_length=10, description="Código do produto (P13, P20, P45)")
    name: str = Field(..., max_length=100, description="Nome do produto")
    description: Optional[str] = Field(None, description="Descrição")
    weight_kg: Decimal = Field(..., gt=0, description="Peso em kg")
    price: Decimal = Field(..., gt=0, description="Preço em R$")
    is_active: bool = Field(True, description="Disponível para venda")


class ProductCreate(ProductBase):
    """Schema para criar produto."""

    firebird_code: Optional[str] = Field(None, max_length=50, description="Código no Firebird")


class ProductUpdate(BaseSchema):
    """Schema para atualizar produto."""

    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase, TimestampSchema):
    """Schema de resposta de produto."""

    id: UUID
    firebird_code: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Nome para exibição."""
        return f"{self.code} ({self.weight_kg}kg) - R$ {self.price:.2f}"

    @property
    def button_text(self) -> str:
        """Texto para botão do WhatsApp."""
        return f"{self.code} - R$ {self.price:.0f}"


class ProductBrief(BaseSchema):
    """Schema resumido de produto (para listas e bot)."""

    id: UUID
    code: str
    name: str
    price: Decimal
    weight_kg: Decimal

    @property
    def button_text(self) -> str:
        return f"{self.code} ({self.weight_kg}kg) - R$ {self.price:.0f}"
