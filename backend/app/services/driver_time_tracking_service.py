"""
Service para tracking de tempo dos drivers.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict
import uuid

from app.models.driver_time_log import DriverTimeLog
from app.models.driver import Driver
from app.models.delivery import Delivery


class DriverTimeTrackingService:
    """Service para tracking de tempo dos drivers."""
    
    @staticmethod
    async def start_time_log(
        db: AsyncSession,
        driver_id: uuid.UUID,
        status: str
    ) -> DriverTimeLog:
        """
        Inicia um novo log de tempo.
        Finaliza o log anterior se houver um em aberto.
        """
        # Finalizar log anterior se existir
        await DriverTimeTrackingService.end_current_time_log(db, driver_id)
        
        # Criar novo log
        log = DriverTimeLog(
            driver_id=driver_id,
            status=status,
            started_at=datetime.now(timezone.utc),
            date=date.today()
        )
        
        db.add(log)
        await db.commit()
        await db.refresh(log)
        
        return log
    
    @staticmethod
    async def end_current_time_log(
        db: AsyncSession,
        driver_id: uuid.UUID
    ) -> Optional[DriverTimeLog]:
        """Finaliza o log de tempo atual do driver."""
        result = await db.execute(
            select(DriverTimeLog)
            .where(
                and_(
                    DriverTimeLog.driver_id == driver_id,
                    DriverTimeLog.ended_at.is_(None)
                )
            )
        )
        log = result.scalar_one_or_none()
        
        if log:
            log.finalize()
            await db.commit()
            await db.refresh(log)
        
        return log
    
    @staticmethod
    async def get_driver_time_summary(
        db: AsyncSession,
        driver_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Retorna resumo de tempo trabalhado por status.
        """
        result = await db.execute(
            select(
                DriverTimeLog.status,
                func.sum(DriverTimeLog.duration_minutes).label('total_minutes'),
                func.count(DriverTimeLog.id).label('count')
            )
            .where(
                and_(
                    DriverTimeLog.driver_id == driver_id,
                    DriverTimeLog.date >= start_date,
                    DriverTimeLog.date <= end_date,
                    DriverTimeLog.duration_minutes.isnot(None)
                )
            )
            .group_by(DriverTimeLog.status)
        )
        
        rows = result.all()
        
        summary = {
            'driver_id': str(driver_id),
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'by_status': {},
            'total_minutes': 0
        }
        
        for row in rows:
            status = row.status
            minutes = int(row.total_minutes or 0)
            summary['by_status'][status] = {
                'minutes': minutes,
                'hours': round(minutes / 60, 2),
                'count': row.count
            }
            summary['total_minutes'] += minutes
        
        summary['total_hours'] = round(summary['total_minutes'] / 60, 2)
        
        return summary
    
    @staticmethod
    async def get_daily_ranking(
        db: AsyncSession,
        target_date: date = None
    ) -> List[Dict]:
        """
        Retorna ranking de entregas do dia.
        """
        if not target_date:
            target_date = date.today()
        
        # Query para contar entregas entregues no dia
        result = await db.execute(
            select(
                Driver.id,
                Driver.name,
                Driver.rating,
                Driver.vehicle_type,
                func.count(Delivery.id).label('deliveries_count')
            )
            .join(Delivery, Driver.id == Delivery.driver_id)
            .where(
                and_(
                    func.date(Delivery.delivered_at) == target_date,
                    Delivery.status == 'delivered'
                )
            )
            .group_by(Driver.id, Driver.name, Driver.rating, Driver.vehicle_type)
            .order_by(desc('deliveries_count'))
        )
        
        rows = result.all()
        
        ranking = []
        for idx, row in enumerate(rows, start=1):
            ranking.append({
                'position': idx,
                'driver_id': str(row.id),
                'driver_name': row.name,
                'rating': float(row.rating) if row.rating is not None else 0.0,
                'vehicle_type': row.vehicle_type or '',
                'deliveries_count': row.deliveries_count
            })
        
        return ranking
    
    @staticmethod
    async def get_all_drivers_time_summary(
        db: AsyncSession,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Retorna resumo de tempo de todos os drivers.
        """
        result = await db.execute(
            select(Driver.id, Driver.name, Driver.status, Driver.rating)
            .where(Driver.is_active == True)
            .order_by(Driver.name)
        )
        
        drivers = result.all()
        
        summaries = []
        for driver in drivers:
            summary = await DriverTimeTrackingService.get_driver_time_summary(
                db, driver.id, start_date, end_date
            )
            summary['driver_id'] = str(driver.id)  # Adicionar ID para identificar duplicatas
            summary['driver_name'] = driver.name
            summary['current_status'] = driver.status
            summary['rating'] = float(driver.rating) if driver.rating is not None else 0.0
            summaries.append(summary)
        
        return summaries
