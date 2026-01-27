"""
Schemas base Pydantic.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Schema base com configurações comuns."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema com timestamps."""

    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    """Schema com ID UUID."""

    id: UUID


class AddressSchema(BaseSchema):
    """Schema de endereço."""

    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    bairro: Optional[str] = None
    city: Optional[str] = "Curitiba"
    state: Optional[str] = "PR"
    cep: Optional[str] = None

    @property
    def full_address(self) -> str:
        """Retorna endereço formatado."""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.number:
            parts.append(self.number)
        if self.complement:
            parts.append(f"- {self.complement}")
        if self.bairro:
            parts.append(f"- {self.bairro}")
        return ", ".join(parts)


class PaginationParams(BaseSchema):
    """Parâmetros de paginação."""

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseSchema):
    """Resposta paginada genérica."""

    items: list
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int):
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )
