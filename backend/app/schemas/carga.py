"""
Schemas Pydantic para Carga de Veículo.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, validator


class CargaItemBase(BaseModel):
    """Schema base para item da carga."""
    produto_id: UUID = Field(..., description="ID do produto")
    qtd_saida: int = Field(..., ge=0, description="Quantidade que sai (cheios)")


class CargaItemCreate(CargaItemBase):
    """Schema para criar item da carga."""
    pass


class CargaItemAcerto(BaseModel):
    """Schema para acerto de item da carga."""
    produto_id: UUID = Field(..., description="ID do produto")
    qtd_retorno_cheio: int = Field(0, ge=0, description="Quantidade que retornou cheia")
    qtd_retorno_vazio: int = Field(0, ge=0, description="Quantidade de vazios retornados")
    qtd_vendida: int = Field(0, ge=0, description="Quantidade vendida")


class CargaItemResponse(BaseModel):
    """Schema de resposta do item da carga."""
    id: UUID
    carga_id: UUID
    produto_id: UUID
    produto_nome: Optional[str] = None
    produto_codigo: Optional[str] = None
    qtd_saida: int
    qtd_retorno_cheio: int
    qtd_retorno_vazio: int
    qtd_vendida: int
    qtd_pendente: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CargaBase(BaseModel):
    """Schema base para carga."""
    driver_id: UUID = Field(..., description="ID do motorista")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações")


class CargaCreate(CargaBase):
    """Schema para criar carga."""
    itens: List[CargaItemCreate] = Field(..., min_items=1, description="Itens da carga")


class CargaUpdate(BaseModel):
    """Schema para atualizar carga."""
    observacoes: Optional[str] = Field(None, max_length=500)


class CargaSaidaRequest(BaseModel):
    """Schema para registrar saída."""
    pass  # Por enquanto vazio, pode adicionar campos depois


class CargaAcertoRequest(BaseModel):
    """Schema para realizar acerto da carga."""
    itens: List[CargaItemAcerto] = Field(..., description="Acerto dos itens")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações do acerto")


class CargaResponse(BaseModel):
    """Schema de resposta da carga."""
    id: UUID
    driver_id: UUID
    driver_nome: Optional[str] = None
    status: str
    data_saida: Optional[datetime] = None
    data_retorno: Optional[datetime] = None
    observacoes: Optional[str] = None
    itens: List[CargaItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CargaBrief(BaseModel):
    """Schema resumido da carga (para listagens)."""
    id: UUID
    driver_id: UUID
    driver_nome: Optional[str] = None
    status: str
    data_saida: Optional[datetime] = None
    total_itens: int = 0
    total_produtos: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CargaAtualResponse(BaseModel):
    """Schema para carga atual do motorista."""
    tem_carga: bool = False
    carga: Optional[CargaResponse] = None
