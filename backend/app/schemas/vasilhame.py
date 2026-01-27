"""
Schemas de Vasilhames e Controle de Comodato.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


# ==================== VASILHAME ====================

class VasilhameBase(BaseSchema):
    """Schema base de vasilhame."""
    codigo: str = Field(..., max_length=20, description="Código: P13, P45, etc")
    descricao: str = Field(..., max_length=100, description="Descrição")
    peso_kg: Decimal = Field(..., description="Peso vazio em kg")
    valor_caucao: Decimal = Field(..., description="Valor da caução")


class VasilhameCreate(VasilhameBase):
    """Schema para criar vasilhame."""
    firebird_id: Optional[int] = None


class VasilhameUpdate(BaseSchema):
    """Schema para atualizar vasilhame."""
    descricao: Optional[str] = None
    peso_kg: Optional[Decimal] = None
    valor_caucao: Optional[Decimal] = None
    ativo: Optional[bool] = None


class VasilhameResponse(VasilhameBase, TimestampSchema):
    """Schema de resposta de vasilhame."""
    id: UUID
    ativo: bool
    firebird_id: Optional[int] = None


# ==================== CLIENTE VASILHAME ====================

class ClienteVasilhameBase(BaseSchema):
    """Schema base de vasilhame do cliente."""
    customer_id: UUID
    vasilhame_id: UUID
    quantidade: int = Field(default=0, ge=0)
    valor_caucao_pago: Decimal = Field(default=Decimal("0.00"))
    observacoes: Optional[str] = None


class ClienteVasilhameCreate(BaseSchema):
    """Schema para criar/atualizar vasilhame do cliente."""
    customer_id: UUID
    vasilhame_id: UUID
    quantidade: int = Field(..., ge=0)
    valor_caucao_pago: Optional[Decimal] = None
    observacoes: Optional[str] = None


class ClienteVasilhameUpdate(BaseSchema):
    """Schema para atualizar vasilhame do cliente."""
    quantidade: Optional[int] = Field(None, ge=0)
    valor_caucao_pago: Optional[Decimal] = None
    observacoes: Optional[str] = None


class ClienteVasilhameResponse(ClienteVasilhameBase, TimestampSchema):
    """Schema de resposta de vasilhame do cliente."""
    id: UUID
    data_primeiro_emprestimo: Optional[datetime] = None
    # Dados enriquecidos
    vasilhame_codigo: Optional[str] = None
    vasilhame_descricao: Optional[str] = None
    customer_nome: Optional[str] = None


# ==================== MOVIMENTACAO ====================

class MovimentacaoBase(BaseSchema):
    """Schema base de movimentação."""
    tipo: str = Field(..., description="ENTRADA ou SAIDA")
    quantidade: int = Field(..., gt=0)
    valor_caucao: Decimal = Field(default=Decimal("0.00"))
    motivo: str = Field(..., max_length=100)
    observacoes: Optional[str] = None


class MovimentacaoCreate(MovimentacaoBase):
    """Schema para criar movimentação."""
    cliente_vasilhame_id: UUID
    order_id: Optional[UUID] = None


class MovimentacaoResponse(MovimentacaoBase, TimestampSchema):
    """Schema de resposta de movimentação."""
    id: UUID
    cliente_vasilhame_id: UUID
    order_id: Optional[UUID] = None


# ==================== RESUMO DO CLIENTE ====================

class ResumoVasilhamesCliente(BaseSchema):
    """Resumo de vasilhames de um cliente."""
    customer_id: UUID
    customer_nome: str
    total_vasilhames: int
    total_caucao_pago: Decimal
    itens: List[ClienteVasilhameResponse]


# ==================== OPERAÇÕES ====================

class RegistrarVendaVasilhame(BaseSchema):
    """Schema para registrar venda (cliente novo sem vasilhame)."""
    customer_id: UUID
    vasilhame_id: UUID
    quantidade: int = Field(default=1, gt=0)
    order_id: Optional[UUID] = None


class RegistrarDevolucao(BaseSchema):
    """Schema para registrar devolução de vasilhame."""
    customer_id: UUID
    vasilhame_id: UUID
    quantidade: int = Field(default=1, gt=0)
    devolver_caucao: bool = Field(default=True)
    observacoes: Optional[str] = None
