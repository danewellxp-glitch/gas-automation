"""Modelo de Item da Carga do Veículo."""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.estoque.vehicle_load import VehicleLoad


class VehicleLoadItem(BaseModel):
    __tablename__ = "vehicle_load_items"

    vehicle_load_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicle_loads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stock_products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity_loaded: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_delivered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_returned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    vehicle_load: Mapped["VehicleLoad"] = relationship("VehicleLoad", back_populates="items")
