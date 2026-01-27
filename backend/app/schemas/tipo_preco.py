"""
Schemas de Tipo de Preço e Preços por Produto.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class TipoPrecoBase(BaseSchema):
    """Schema base de tipo de preço."""
    codigo: str = Field(..., max_length=20, description="Código único")
    descricao: str = Field(..., max_length=100, description="Descrição")
    percentual_desconto: Decimal = Field(default=Decimal("0.00"), description="Desconto %")


class TipoPrecoCreate(TipoPrecoBase):
    """Schema para criar tipo de preço."""
    firebird_id: Optional[int] = None


class TipoPrecoUpdate(BaseSchema):
    """Schema para atualizar tipo de preço."""
    descricao: Optional[str] = None
    percentual_desconto: Optional[Decimal] = None
    ativo: Optional[bool] = None


class TipoPrecoResponse(TipoPrecoBase, TimestampSchema):
    """Schema de resposta de tipo de preço."""
    id: UUID
    ativo: bool
    firebird_id: Optional[int] = None


class ProdutoPrecoBase(BaseSchema):
    """Schema base de preço por produto."""
    produto_id: UUID
    tipo_preco_id: UUID
    preco: Decimal = Field(..., description="Preço para esta modalidade")
    vigencia_inicio: date
    vigencia_fim: Optional[date] = None


class ProdutoPrecoCreate(ProdutoPrecoBase):
    """Schema para criar preço de produto."""
    pass


class ProdutoPrecoUpdate(BaseSchema):
    """Schema para atualizar preço de produto."""
    preco: Optional[Decimal] = None
    vigencia_fim: Optional[date] = None


class ProdutoPrecoResponse(ProdutoPrecoBase, TimestampSchema):
    """Schema de resposta de preço de produto."""
    id: UUID
    produto_nome: Optional[str] = None
    tipo_preco_codigo: Optional[str] = None
