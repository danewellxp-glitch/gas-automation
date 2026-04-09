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

    code: str = Field(..., min_length=2, max_length=10, description="Código do produto (P13, P20, P45, G20L)")
    name: str = Field(..., max_length=100, description="Nome do produto")
    description: Optional[str] = Field(None, description="Descrição")
    categoria: str = Field("gas", description="Categoria: gas, agua, outro")
    weight_kg: Optional[Decimal] = Field(None, ge=0, description="Peso em kg (nulo para água)")
    volume_litros: Optional[int] = Field(None, ge=1, description="Volume em litros (para galões)")
    requer_retorno_vasilhame: bool = Field(True, description="Se o vasilhame vazio deve retornar")
    price: Decimal = Field(..., gt=0, description="Preço em R$")
    is_active: bool = Field(True, description="Disponível para venda")


class ProductCreate(ProductBase):
    """Schema para criar produto."""

    firebird_code: Optional[str] = Field(None, max_length=50, description="Código no Firebird")


class ProductUpdate(BaseSchema):
    """Schema para atualizar produto."""

    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    categoria: Optional[str] = None
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    volume_litros: Optional[int] = Field(None, ge=1)
    requer_retorno_vasilhame: Optional[bool] = None
    price: Optional[Decimal] = Field(None, gt=0)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase, TimestampSchema):
    """Schema de resposta de produto."""

    id: UUID
    firebird_code: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Nome para exibição."""
        if self.categoria == "agua" and self.volume_litros:
            return f"{self.code} ({self.volume_litros}L) - R$ {self.price:.2f}"
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
    categoria: str = "gas"
    weight_kg: Optional[Decimal] = None
    volume_litros: Optional[int] = None

    @property
    def button_text(self) -> str:
        if self.categoria == "agua" and self.volume_litros:
            return f"{self.code} ({self.volume_litros}L) - R$ {self.price:.0f}"
        return f"{self.code} ({self.weight_kg}kg) - R$ {self.price:.0f}"
