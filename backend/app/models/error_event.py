"""
ErrorEvent

Tabela de agregação de erros para o painel Admin (Central de Logs & Erros).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ErrorEvent(Base):
    __tablename__ = "error_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    error_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    message: Mapped[str] = mapped_column(String(500), nullable=False)
    details_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    known_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    incident_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    incident_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_error_events_service_type", "service", "error_type"),
        Index("ix_error_events_status_last_seen", "status", "last_seen"),
    )

