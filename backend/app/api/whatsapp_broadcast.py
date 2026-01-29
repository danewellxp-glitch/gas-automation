"""
API para Disparo de Mensagens WhatsApp em Massa.

Permite owner/admin enviar mensagens para clientes via WhatsApp.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models.auth_models import User
from app.models.customer import Customer
from app.models.order import Order
from app.api.websocket import UserRole
from app.integrations.waha import waha_client
from app.services.event_publisher import event_publisher

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/broadcast")
async def broadcast_whatsapp_message(
    message: str = Body(..., description="Mensagem a ser enviada"),
    filter_type: str = Body(..., description="Filtro: all, last_week, last_month"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dispara mensagem WhatsApp para clientes.
    
    Filtros disponíveis:
    - all: Todos os clientes
    - last_week: Clientes com pedidos na última semana
    - last_month: Clientes com pedidos no último mês
    
    Apenas owner e admin podem usar.
    """
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode estar vazia")
    
    try:
        # Construir query de clientes baseado no filtro
        query = select(Customer)
        
        if filter_type == "all":
            # Todos os clientes
            pass
        elif filter_type == "last_week":
            # Clientes com pedidos na última semana
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            subquery = select(Order.customer_id).where(
                Order.created_at >= week_ago
            ).distinct()
            query = query.where(Customer.id.in_(subquery))
        elif filter_type == "last_month":
            # Clientes com pedidos no último mês
            month_ago = datetime.now(timezone.utc) - timedelta(days=30)
            subquery = select(Order.customer_id).where(
                Order.created_at >= month_ago
            ).distinct()
            query = query.where(Customer.id.in_(subquery))
        else:
            raise HTTPException(status_code=400, detail=f"Filtro inválido: {filter_type}")
        
        # Executar query
        result = await db.execute(query)
        customers = result.scalars().all()
        
        # Filtrar apenas clientes com telefone
        customers_with_phone = [c for c in customers if c.phone]
        
        if not customers_with_phone:
            return {
                "success": True,
                "message": "Nenhum cliente encontrado com telefone",
                "total_customers": 0,
                "sent": 0,
                "failed": 0,
            }
        
        # Enviar mensagens
        sent = 0
        failed = 0
        errors = []
        
        for customer in customers_with_phone:
            try:
                # Enviar via WAHA
                await waha_client.send_text(
                    phone=customer.phone,
                    text=message.strip(),
                )
                
                # Publicar evento para logs
                await event_publisher.publish_notification(
                    notification_type="whatsapp",
                    recipient_phone=customer.phone,
                    message=message.strip(),
                    template="broadcast",
                    template_data={
                        "filter_type": filter_type,
                        "customer_id": str(customer.id),
                        "sent_by": current_user.id,
                    },
                )
                
                sent += 1
                
            except Exception as e:
                logger.error(f"Erro ao enviar para {customer.phone}: {e}")
                failed += 1
                errors.append({
                    "phone": customer.phone,
                    "error": str(e),
                })
        
        return {
            "success": True,
            "message": f"Mensagens enviadas: {sent} enviadas, {failed} falhas",
            "total_customers": len(customers_with_phone),
            "sent": sent,
            "failed": failed,
            "filter_type": filter_type,
            "errors": errors[:10] if errors else [],  # Limitar a 10 erros
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao disparar mensagens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao disparar mensagens: {str(e)}")


@router.get("/broadcast/stats")
async def get_broadcast_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna estatísticas de clientes para os filtros disponíveis.
    
    Apenas owner e admin podem acessar.
    """
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    try:
        # Total de clientes
        total_result = await db.execute(select(func.count(Customer.id)))
        total_customers = total_result.scalar() or 0
        
        # Clientes com telefone
        customers_with_phone_result = await db.execute(
            select(func.count(Customer.id)).where(Customer.phone.isnot(None))
        )
        customers_with_phone = customers_with_phone_result.scalar() or 0
        
        # Clientes da última semana
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        last_week_subquery = select(Order.customer_id).where(
            Order.created_at >= week_ago
        ).distinct()
        last_week_result = await db.execute(
            select(func.count(Customer.id)).where(Customer.id.in_(last_week_subquery))
        )
        last_week_count = last_week_result.scalar() or 0
        
        # Clientes do último mês
        month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        last_month_subquery = select(Order.customer_id).where(
            Order.created_at >= month_ago
        ).distinct()
        last_month_result = await db.execute(
            select(func.count(Customer.id)).where(Customer.id.in_(last_month_subquery))
        )
        last_month_count = last_month_result.scalar() or 0
        
        return {
            "all": customers_with_phone,
            "last_week": last_week_count,
            "last_month": last_month_count,
            "total_customers": total_customers,
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))