"""Modelo de Carga do Veículo."""
import enum
import uuid
from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.estoque.vehicle_load_item import VehicleLoadItem


class VehicleLoadStatus(str, enum.Enum):
    aberta = "aberta"
    em_rota = "em_rota"
    encerrada = "encerrada"


class VehicleLoad(BaseModel):
    __tablename__ = "vehicle_loads"

    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    load_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=VehicleLoadStatus.aberta.value)
    loaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    items: Mapped[List["VehicleLoadItem"]] = relationship(
        "VehicleLoadItem", lazy="selectin", back_populates="vehicle_load"
    )

    __table_args__ = (
        UniqueConstraint("driver_id", "load_date", name="uq_vehicle_load_driver_date"),
        Index("ix_vehicle_loads_date_status", "load_date", "status"),
    )
