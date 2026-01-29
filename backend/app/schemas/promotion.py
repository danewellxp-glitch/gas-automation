"""
Schemas Pydantic para Promoções.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PromotionBase(BaseModel):
    """Schema base para promoção."""
    code: str = Field(..., min_length=3, max_length=50, description="Código do cupom")
    name: str = Field(..., min_length=1, max_length=200, description="Nome da promoção")
    description: Optional[str] = Field(None, description="Descrição detalhada")
    discount_type: str = Field(default="percentage", description="Tipo: percentage ou fixed")
    discount_value: Decimal = Field(..., gt=0, description="Valor do desconto")
    min_order_value: Optional[Decimal] = Field(None, ge=0, description="Valor mínimo do pedido")
    max_discount: Optional[Decimal] = Field(None, ge=0, description="Desconto máximo")
    usage_limit: Optional[int] = Field(None, ge=1, description="Limite de usos")
    valid_from: date = Field(..., description="Data de início")
    valid_until: Optional[date] = Field(None, description="Data de fim")
    is_active: Optional[bool] = Field(True, description="Se está ativa")
    applies_to_all_products: Optional[bool] = Field(True, description="Aplica a todos produtos")
    
    @field_validator("discount_type")
    @classmethod
    def validate_discount_type(cls, v):
        if v not in ["percentage", "fixed"]:
            raise ValueError("discount_type deve ser 'percentage' ou 'fixed'")
        return v


class PromotionCreate(PromotionBase):
    """Schema para criar promoção."""
    pass


class PromotionUpdate(BaseModel):
    """Schema para atualizar promoção."""
    code: Optional[str] = Field(None, min_length=3, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = Field(None, gt=0)
    min_order_value: Optional[Decimal] = Field(None, ge=0)
    max_discount: Optional[Decimal] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_active: Optional[bool] = None
    applies_to_all_products: Optional[bool] = None


class PromotionResponse(PromotionBase):
    """Schema de resposta para promoção."""
    id: UUID
    usage_count: int
    created_at: date
    updated_at: date
    
    class Config:
        from_attributes = True