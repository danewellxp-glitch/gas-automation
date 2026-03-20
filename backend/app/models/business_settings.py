"""
Model: BusinessSettings
Tabela singleton para persistência das configurações de negócio.

Destino: app/models/business_settings.py
"""

from sqlalchemy import Column, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


DEFAULT_OPERATING_HOURS = {
    "monday":    {"open": "08:00", "close": "18:00", "enabled": True},
    "tuesday":   {"open": "08:00", "close": "18:00", "enabled": True},
    "wednesday": {"open": "08:00", "close": "18:00", "enabled": True},
    "thursday":  {"open": "08:00", "close": "18:00", "enabled": True},
    "friday":    {"open": "08:00", "close": "18:00", "enabled": True},
    "saturday":  {"open": "08:00", "close": "18:00", "enabled": True},
    "sunday":    {"open": "08:00", "close": "18:00", "enabled": False},
}

DEFAULT_MONTHLY_GOALS = {
    "revenue": 0.0,
    "orders": 0.0,
    "new_customers": 0.0,
}


class BusinessSettings(Base):
    """
    Configurações de negócio — tabela singleton (sempre id=1).

    Campos dinâmicos armazenados como JSONB para flexibilidade futura
    sem necessidade de novas migrações.
    """

    __tablename__ = "business_settings"

    # Singleton: id fixo = 1, nunca haverá mais de uma linha
    id = Column(Integer, primary_key=True, default=1)

    # Horário de funcionamento por dia da semana
    # Formato: {"monday": {"open": "08:00", "close": "18:00", "enabled": true}, ...}
    operating_hours = Column(
        JSONB,
        nullable=False,
        default=DEFAULT_OPERATING_HOURS,
        server_default='{}',
    )

    # Metas mensais do negócio
    # Formato: {"revenue": 50000.0, "orders": 300, "new_customers": 50}
    monthly_goals = Column(
        JSONB,
        nullable=False,
        default=DEFAULT_MONTHLY_GOALS,
        server_default='{}',
    )

    # Lista de bairros habilitados para entrega
    # Formato: ["Centro", "Boa Vista", ...]
    enabled_bairros = Column(
        JSONB,
        nullable=False,
        default=list,
        server_default='[]',
    )

    # Promoções ativas
    # Formato: [{"id": "...", "name": "...", "discount": 10, "active": true}, ...]
    promotions = Column(
        JSONB,
        nullable=False,
        default=list,
        server_default='[]',
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BusinessSettings id={self.id} updated_at={self.updated_at}>"
