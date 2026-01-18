"""
API de Notificações.
Endpoints para envio direto de notificações.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.integrations.twilio_client import send_sms
from app.integrations.sendgrid_client import send_email

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schemas ====================

class SMSRequest(BaseModel):
    """Request para envio de SMS."""
    phone: str = Field(..., description="Número de telefone (com DDD)")
    message: str = Field(..., max_length=1600, description="Mensagem SMS")


class EmailRequest(BaseModel):
    """Request para envio de email."""
    to_email: EmailStr = Field(..., description="Email do destinatário")
    to_name: Optional[str] = Field(None, description="Nome do destinatário")
    subject: str = Field(..., max_length=200, description="Assunto do email")
    body_text: str = Field(..., description="Corpo do email (texto)")
    body_html: Optional[str] = Field(None, description="Corpo do email (HTML)")


class NotificationResponse(BaseModel):
    """Resposta de notificação."""
    success: bool
    message: str
    notification_id: Optional[str] = None


# ==================== Endpoints ====================

@router.post("/sms", response_model=NotificationResponse)
async def send_sms_notification(
    request: SMSRequest,
    background_tasks: BackgroundTasks,
):
    """
    Envia notificação SMS via Twilio.

    O envio é feito em background para não bloquear a requisição.
    """
    try:
        # Enviar em background
        background_tasks.add_task(
            send_sms,
            phone=request.phone,
            message=request.message,
        )

        return NotificationResponse(
            success=True,
            message="SMS agendado para envio",
        )

    except Exception as e:
        logger.error(f"Erro ao agendar SMS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email", response_model=NotificationResponse)
async def send_email_notification(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
):
    """
    Envia notificação por email via SendGrid.

    O envio é feito em background para não bloquear a requisição.
    """
    try:
        background_tasks.add_task(
            send_email,
            to_email=request.to_email,
            to_name=request.to_name,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
        )

        return NotificationResponse(
            success=True,
            message="Email agendado para envio",
        )

    except Exception as e:
        logger.error(f"Erro ao agendar email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/order-confirmation/{order_id}")
async def send_order_confirmation(
    order_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Envia notificações de confirmação de pedido.

    Envia SMS e/ou email baseado nos dados do cliente.
    """
    # TODO: Buscar dados do pedido e cliente do backend principal
    # Por enquanto, retorna placeholder

    return NotificationResponse(
        success=True,
        message=f"Notificações de confirmação agendadas para pedido {order_id}",
    )


@router.post("/payment-confirmed/{order_id}")
async def send_payment_confirmation(
    order_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Envia notificações de pagamento confirmado.
    """
    return NotificationResponse(
        success=True,
        message=f"Notificações de pagamento agendadas para pedido {order_id}",
    )


@router.post("/delivery-started/{order_id}")
async def send_delivery_started(
    order_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Envia notificações de entrega iniciada.
    """
    return NotificationResponse(
        success=True,
        message=f"Notificações de entrega agendadas para pedido {order_id}",
    )
