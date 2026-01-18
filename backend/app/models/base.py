"""
Modelo base com campos comuns para todas as entidades.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Classe base para todos os modelos SQLAlchemy."""

    # Configuração de tipo para anotações
    type_annotation_map = {
        uuid.UUID: UUID(as_uuid=True),
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    """Mixin para adicionar campos de timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin para adicionar ID UUID como chave primária."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """
    Modelo base completo com UUID e timestamps.
    Usar como base para a maioria das entidades.
    """

    __abstract__ = True

    def to_dict(self) -> dict[str, Any]:
        """Converte modelo para dicionário."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
