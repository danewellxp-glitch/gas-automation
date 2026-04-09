"""Schemas Pydantic para o módulo de Despesas."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, field_validator

from app.models.expense import ExpenseTipo, ExpenseTipoGrupo, Periodicidade, EXPENSE_GRUPO


class ExpenseCreate(BaseModel):
    tipo: ExpenseTipo
    descricao: str
    valor: Decimal
    data_vencimento: date
    periodicidade: Periodicidade = Periodicidade.unico
    parcelas_total: int = 1
    # Vínculos opcionais
    veiculo_placa: Optional[str] = None
    funcionario_id: Optional[int] = None
    fornecedor: Optional[str] = None
    numero_nota: Optional[str] = None
    observacao: Optional[str] = None
    conta_id: Optional[uuid.UUID] = None

    @field_validator("parcelas_total")
    @classmethod
    def parcelas_minimo_1(cls, v: int) -> int:
        if v < 1:
            raise ValueError("parcelas_total deve ser >= 1")
        return v

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("valor deve ser > 0")
        return v


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    tipo: str
    grupo: str
    descricao: str
    valor: Decimal
    valor_parcela: Decimal
    data_lancamento: date
    data_vencimento: date
    periodicidade: str
    parcelas_total: int
    parcela_atual: int
    grupo_parcela_id: Optional[uuid.UUID]
    pago: bool
    data_pagamento: Optional[date]
    veiculo_placa: Optional[str]
    funcionario_id: Optional[int]
    fornecedor: Optional[str]
    numero_nota: Optional[str]
    observacao: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ExpensePagarBody(BaseModel):
    data_pagamento: Optional[date] = None  # default = hoje


class ExpenseCalendarioItem(BaseModel):
    dia: date
    total: Decimal
    despesas: List[ExpenseResponse]


class ExpensePorGrupoItem(BaseModel):
    grupo: str
    total: Decimal
    pago: Decimal
    pendente: Decimal


class ProximoVencimento(BaseModel):
    id: uuid.UUID
    tipo: str
    grupo: str
    descricao: str
    valor_parcela: Decimal
    data_vencimento: date
    dias_para_vencer: int
    pago: bool
    veiculo_placa: Optional[str]
