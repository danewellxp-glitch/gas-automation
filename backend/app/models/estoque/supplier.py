"""Modelo de Fornecedor."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Supplier(BaseModel):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    cnpj: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
