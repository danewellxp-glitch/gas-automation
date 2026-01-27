"""
Modelo de log de tempo dos entregadores.
"""

from datetime import datetime, date, timezone
from typing import Optional
import uuid as uuid_pkg

from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DriverTimeLog(Base):
    """
    Log de tempo dos entregadores por status.
    Cada mudança de status cria um novo registro.
    """
    __tablename__ = "driver_time_logs"

    id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    
    driver_id: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Status do período
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Status: available, offline, busy, break"
    )
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Duração calculada (em minutos)
    duration_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # Data do log (para facilitar queries)
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    
    # Metadados extras
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        name="metadata"  # Nome na tabela continua metadata
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relacionamento
    driver: Mapped["Driver"] = relationship(
        "Driver",
        back_populates="time_logs"
    )
    
    def finalize(self):
        """
        Finaliza o log calculando a duração.
        Limita duração máxima a 16h (960min) para prevenir métricas infladas.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.ended_at:
            self.ended_at = datetime.now(timezone.utc)
        
        delta = self.ended_at - self.started_at
        duration_minutes = int(delta.total_seconds() / 60)
        
        # Limitar a 16 horas (960 minutos)
        MAX_DURATION = 960
        if duration_minutes > MAX_DURATION:
            logger.warning(
                f"Time log {self.id} excede {MAX_DURATION}min "
                f"(duração: {duration_minutes}min). Limitando para prevenir métricas infladas."
            )
            duration_minutes = MAX_DURATION
        
        self.duration_minutes = duration_minutes
    
    def __repr__(self):
        return f"<DriverTimeLog {self.driver_id} {self.status} {self.date}>"
