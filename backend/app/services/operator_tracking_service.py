"""
Operator Tracking Service.

Rastreia tempo de resposta e métricas de operadores usando EventLog.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy import func, select, and_, or_
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_log import EventLog, EventTypes, ActorTypes
from app.models.order import Order
from app.models.auth_models import User

logger = logging.getLogger(__name__)


class OperatorTrackingService:
    """Serviço para rastrear métricas de operadores."""
    
    async def log_operator_response(
        self,
        db: AsyncSession,
        operator_id: int,
        conversation_id: Optional[int] = None,
        order_id: Optional[UUID] = None,
        response_time_seconds: Optional[float] = None,
    ) -> None:
        """
        Registra resposta de operador no EventLog.
        
        Args:
            db: Sessão do banco de dados
            operator_id: ID do operador
            conversation_id: ID da conversa (opcional)
            order_id: ID do pedido relacionado (opcional)
            response_time_seconds: Tempo de resposta em segundos (opcional)
        """
        try:
            event = EventLog(
                event_type="operator.response",
                entity_type="conversation" if conversation_id else "order",
                entity_id=order_id,
                actor_type=ActorTypes.OPERATOR,
                actor_id=str(operator_id),
                payload={
                    "conversation_id": conversation_id,
                    "order_id": str(order_id) if order_id else None,
                    "response_time_seconds": response_time_seconds,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            
            db.add(event)
            await db.commit()
            
            logger.debug(f"Resposta de operador registrada: operator_id={operator_id}, response_time={response_time_seconds}s")
            
        except Exception as e:
            logger.error(f"Erro ao registrar resposta de operador: {e}", exc_info=True)
            await db.rollback()
    
    async def log_order_approval(
        self,
        db: AsyncSession,
        operator_id: int,
        order_id: UUID,
        approval_time_seconds: Optional[float] = None,
    ) -> None:
        """
        Registra aprovação de pedido por operador.
        
        Args:
            db: Sessão do banco de dados
            operator_id: ID do operador
            order_id: ID do pedido
            approval_time_seconds: Tempo desde criação até aprovação em segundos
        """
        try:
            event = EventLog(
                event_type="operator.order_approved",
                entity_type="order",
                entity_id=order_id,
                actor_type=ActorTypes.OPERATOR,
                actor_id=str(operator_id),
                payload={
                    "order_id": str(order_id),
                    "approval_time_seconds": approval_time_seconds,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            
            db.add(event)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Erro ao registrar aprovação: {e}", exc_info=True)
            await db.rollback()
    
    async def get_operator_metrics(
        self,
        db: AsyncSession,
        operator_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calcula métricas de operadores.
        
        Args:
            db: Sessão do banco de dados
            operator_id: ID do operador (None para todos)
            date_from: Data inicial
            date_to: Data final
            
        Returns:
            Dicionário com métricas
        """
        try:
            # Filtros base
            filters = []
            
            if operator_id:
                filters.append(EventLog.actor_id == str(operator_id))
            
            filters.append(EventLog.actor_type == ActorTypes.OPERATOR)
            
            if date_from:
                filters.append(EventLog.created_at >= date_from)
            
            if date_to:
                filters.append(EventLog.created_at <= date_to)
            
            # Tempo médio de resposta
            response_times_query = select(
                func.avg(
                    func.cast(EventLog.payload['response_time_seconds'], sa.Float)
                )
            ).where(
                and_(*filters),
                EventLog.event_type == "operator.response",
                EventLog.payload['response_time_seconds'].isnot(None),
            )
            
            avg_response_time_result = await db.execute(response_times_query)
            avg_response_time = avg_response_time_result.scalar()
            
            if avg_response_time:
                avg_response_time_minutes = avg_response_time / 60
            else:
                avg_response_time_minutes = None
            
            # Total de respostas
            total_responses_query = select(func.count(EventLog.id)).where(
                and_(*filters),
                EventLog.event_type == "operator.response",
            )
            total_responses_result = await db.execute(total_responses_query)
            total_responses = total_responses_result.scalar() or 0
            
            # Total de aprovações
            total_approvals_query = select(func.count(EventLog.id)).where(
                and_(*filters),
                EventLog.event_type == "operator.order_approved",
            )
            total_approvals_result = await db.execute(total_approvals_query)
            total_approvals = total_approvals_result.scalar() or 0
            
            # Tempo médio de aprovação
            approval_times_query = select(
                func.avg(
                    func.cast(EventLog.payload['approval_time_seconds'], sa.Float)
                )
            ).where(
                and_(*filters),
                EventLog.event_type == "operator.order_approved",
                EventLog.payload['approval_time_seconds'].isnot(None),
            )
            
            avg_approval_time_result = await db.execute(approval_times_query)
            avg_approval_time = avg_approval_time_result.scalar()
            
            if avg_approval_time:
                avg_approval_time_minutes = avg_approval_time / 60
            else:
                avg_approval_time_minutes = None
            
            return {
                "operator_id": operator_id,
                "avg_response_time_minutes": round(avg_response_time_minutes, 2) if avg_response_time_minutes else None,
                "total_responses": total_responses,
                "total_approvals": total_approvals,
                "avg_approval_time_minutes": round(avg_approval_time_minutes, 2) if avg_approval_time_minutes else None,
                "period": {
                    "from": date_from.isoformat() if date_from else None,
                    "to": date_to.isoformat() if date_to else None,
                },
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular métricas de operador: {e}", exc_info=True)
            return {
                "operator_id": operator_id,
                "avg_response_time_minutes": None,
                "total_responses": 0,
                "total_approvals": 0,
                "avg_approval_time_minutes": None,
            }
    
    async def get_all_operators_metrics(
        self,
        db: AsyncSession,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Calcula métricas de todos os operadores.
        
        Args:
            db: Sessão do banco de dados
            date_from: Data inicial
            date_to: Data final
            
        Returns:
            Lista de métricas por operador
        """
        # Buscar todos os operadores únicos que responderam
        operators_query = select(
            EventLog.actor_id.distinct()
        ).where(
            EventLog.actor_type == ActorTypes.OPERATOR,
            or_(
                EventLog.event_type == "operator.response",
                EventLog.event_type == "operator.order_approved",
            ),
        )
        
        if date_from:
            operators_query = operators_query.where(EventLog.created_at >= date_from)
        if date_to:
            operators_query = operators_query.where(EventLog.created_at <= date_to)
        
        operators_result = await db.execute(operators_query)
        operator_ids = [int(row[0]) for row in operators_result.fetchall() if row[0]]
        
        # Calcular métricas para cada operador
        metrics = []
        for operator_id in operator_ids:
            operator_metrics = await self.get_operator_metrics(
                db,
                operator_id=operator_id,
                date_from=date_from,
                date_to=date_to,
            )
            metrics.append(operator_metrics)
        
        return metrics


# Instância global
operator_tracking_service = OperatorTrackingService()