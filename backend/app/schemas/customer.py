"""
Schemas de Cliente.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import AddressSchema, BaseSchema, TimestampSchema


class CustomerBase(BaseSchema):
    """Schema base de cliente."""

    phone: str = Field(..., min_length=10, max_length=20, description="Telefone WhatsApp")
    name: Optional[str] = Field(None, max_length=200, description="Nome completo")
    email: Optional[EmailStr] = Field(None, description="Email")
    cpf_cnpj: Optional[str] = Field(None, max_length=20, description="CPF ou CNPJ")
    address: Optional[AddressSchema] = Field(None, description="Endereço")
    notes: Optional[str] = Field(None, description="Observações")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Remove caracteres não numéricos e valida formato."""
        # Remove tudo que não é número
        cleaned = "".join(filter(str.isdigit, v))

        # Adiciona código do país se não tiver
        if len(cleaned) == 11:  # 41999999999
            cleaned = f"55{cleaned}"
        elif len(cleaned) == 10:  # 4199999999 (sem 9)
            cleaned = f"55{cleaned}"

        if len(cleaned) < 12 or len(cleaned) > 13:
            raise ValueError("Telefone deve ter 12 ou 13 dígitos (com código do país)")

        return cleaned

    @field_validator("cpf_cnpj")
    @classmethod
    def validate_cpf_cnpj(cls, v: Optional[str]) -> Optional[str]:
        """Remove caracteres não numéricos."""
        if v is None:
            return None
        return "".join(filter(str.isdigit, v))


class CustomerCreate(CustomerBase):
    """Schema para criar cliente."""
    tipo_preco_id: Optional[UUID] = Field(None, description="Modalidade de preço")


class CustomerUpdate(BaseSchema):
    """Schema para atualizar cliente."""

    name: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    cpf_cnpj: Optional[str] = Field(None, max_length=20)
    address: Optional[AddressSchema] = None
    notes: Optional[str] = None
    tipo_preco_id: Optional[UUID] = Field(None, description="Modalidade de preço")


class CustomerResponse(CustomerBase, TimestampSchema):
    """Schema de resposta de cliente."""

    id: UUID
    firebird_id: Optional[int] = None
    asaas_customer_id: Optional[str] = None
    tipo_preco_id: Optional[UUID] = None
    tipo_preco_codigo: Optional[str] = None

    @property
    def formatted_phone(self) -> str:
        """Telefone formatado."""
        if len(self.phone) == 13:
            return f"({self.phone[2:4]}) {self.phone[4:9]}-{self.phone[9:]}"
        return self.phone


class CustomerBrief(BaseSchema):
    """Schema resumido de cliente (para listas)."""

    id: UUID
    phone: str
    name: Optional[str] = None
    bairro: Optional[str] = None

    @classmethod
    def from_customer(cls, customer) -> "CustomerBrief":
        bairro = None
        if customer.address and isinstance(customer.address, dict):
            bairro = customer.address.get("bairro")
        return cls(
            id=customer.id,
            phone=customer.phone,
            name=customer.name,
            bairro=bairro,
        )
