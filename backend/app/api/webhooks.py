"""
Webhook handlers para WAHA (WhatsApp) e Asaas (Pagamentos).
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, redis_manager, AsyncSessionLocal
from app.models.event_log import EventLog
from app.schemas.webhook import (
    AsaasWebhookPayload,
    WAHAMessage,
    WAHAWebhookPayload,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== WAHA (WhatsApp) Webhooks ====================

@router.post("/waha")
async def waha_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Recebe webhooks do WAHA (WhatsApp HTTP API).

    Eventos suportados:
    - message: Nova mensagem recebida
    - message.ack: Confirmação de entrega
    - session.status: Status da sessão WhatsApp
    """
    try:
        body = await request.json()
        # DEBUG: Mostrar payload completo
        import json
        print(f"=== WAHA WEBHOOK RAW ===")
        print(json.dumps(body, indent=2, default=str))
        print(f"========================")

        event = body.get("event", "")
        session = body.get("session", "")
        payload = body.get("payload", {})

        # Processar apenas mensagens recebidas
        if event == "message":
            # Ignorar mensagens enviadas por nós
            from_me = payload.get("fromMe", False)
            if from_me:
                return {"status": "ignored", "reason": "own_message"}

            # WAHA usa LID (Linked ID) - manter o chatId completo para responder
            # from: "7185547411514@lid" ou "5541999999999@c.us"
            chat_id = payload.get("from", "")  # Usar completo para enviar resposta

            # Extrair dados
            key_data = {
                "remoteJid": chat_id,
                "fromMe": from_me,
                "id": payload.get("id", "").split("_")[-1] if payload.get("id") else "",
            }

            # Corpo da mensagem
            message_body = payload.get("body", "")
            sender_name = payload.get("_data", {}).get("notifyName", "")

            # Extrair dados da mensagem
            message = WAHAMessage(
                key=key_data,
                message={"conversation": message_body} if message_body else None,
                messageTimestamp=payload.get("timestamp"),
                pushName=sender_name or payload.get("pushName"),
            )

            print(f"=== Processando mensagem ===")
            print(f"ChatID: {chat_id}")
            print(f"Sender: {sender_name}")
            print(f"Body: {message_body}")
            print(f"==============================")

            # Processar em background para não bloquear
            background_tasks.add_task(
                process_whatsapp_message,
                message=message,
            )

            return {"status": "processing"}

        elif event == "session.status":
            status = payload.get("status", "")
            logger.info(f"Status da sessão WAHA: {status}")
            return {"status": "received", "session_status": status}

        elif event == "message.ack":
            # Confirmação de entrega - apenas log
            ack = payload.get("ack", 0)
            logger.debug(f"Message ACK: {ack}")
            return {"status": "received"}

        return {"status": "ignored", "reason": "unknown_event"}

    except Exception as e:
        logger.error(f"Erro no webhook WAHA: {e}")
        # Retornar 200 para evitar retry do WAHA
        return {"status": "error", "message": str(e)}


async def process_whatsapp_message(message: WAHAMessage):
    """
    Processa mensagem do WhatsApp em background.

    Esta função é chamada em background para não bloquear o webhook.
    """
    try:
        phone = message.phone
        text = message.text
        button_id = message.button_id
        message_id = message.key.id if message.key else None

        # Usar button_id se não tiver texto (clique em botão)
        content = text or button_id or ""

        if not content:
            logger.warning(f"Mensagem sem conteúdo de {phone}")
            return

        logger.info(f"Processando mensagem de {phone}: {content[:50]}")

        # Salvar mensagem recebida no EventLog
        async with AsyncSessionLocal() as db:
            event = EventLog(
                event_type="message_received",
                entity_type="chat",
                payload={"phone": phone, "message": content}
            )
            db.add(event)
            await db.commit()

        # Importar aqui para evitar import circular
        from app.core.flow_engine import flow_engine

        # Processar mensagem pelo flow engine
        result = await flow_engine.process_message(
            phone=phone,
            message=content,
            message_id=message_id,
        )

        # Enviar respostas
        if result.responses:
            await flow_engine.send_responses(phone, result.responses)

        logger.info(
            f"Mensagem processada: {phone} | "
            f"Estado: {result.context.state} -> {result.new_state}"
        )

        # Emitir evento WebSocket
        try:
            from app.api.websocket import emit_new_message
            await emit_new_message(phone, content, "incoming")
        except Exception:
            pass  # WebSocket é opcional

    except Exception as e:
        logger.error(f"Erro ao processar mensagem WhatsApp: {e}", exc_info=True)
        # Tentar enviar mensagem de erro ao usuário
        try:
            from app.integrations.waha import waha_client
            await waha_client.send_text(
                message.phone,
                "Desculpe, ocorreu um erro. Digite *menu* para recomeçar."
            )
        except Exception:
            pass


# ==================== Asaas (Pagamentos) Webhooks ====================

@router.post("/asaas")
async def asaas_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Recebe webhooks do Asaas (Gateway de Pagamentos).

    Eventos suportados:
    - PAYMENT_CONFIRMED: Pagamento confirmado
    - PAYMENT_RECEIVED: Pagamento recebido (boleto)
    - PAYMENT_OVERDUE: Pagamento vencido
    - PAYMENT_REFUNDED: Pagamento estornado
    """
    try:
        body = await request.json()
        logger.info(f"Webhook Asaas recebido: {body.get('event')}")

        # Validar token se configurado
        if settings.asaas_webhook_token:
            token = request.headers.get("asaas-access-token")
            if token != settings.asaas_webhook_token:
                logger.warning("Token de webhook Asaas inválido")
                raise HTTPException(status_code=401, detail="Invalid webhook token")

        event = body.get("event", "")
        payment = body.get("payment", {})

        if not payment:
            return {"status": "ignored", "reason": "no_payment_data"}

        # Processar em background
        background_tasks.add_task(
            process_payment_webhook,
            event=event,
            payment=payment,
        )

        return {"status": "processing"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no webhook Asaas: {e}")
        return {"status": "error", "message": str(e)}


async def process_payment_webhook(event: str, payment: dict):
    """
    Processa webhook de pagamento em background.
    """
    try:
        payment_id = payment.get("id")
        external_ref = payment.get("externalReference")  # Nosso order_id
        status = payment.get("status")
        value = payment.get("value")

        logger.info(
            f"Processando pagamento: {payment_id} - {event} - "
            f"Status: {status} - Valor: {value} - Order: {external_ref}"
        )

        # Importar aqui para evitar import circular
        from app.services.payment_service import payment_service

        if event in ["PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"]:
            # Pagamento aprovado
            await payment_service.handle_payment_confirmed(
                asaas_payment_id=payment_id,
                order_id=external_ref,
                payment_data=payment,
            )

        elif event == "PAYMENT_OVERDUE":
            # Pagamento vencido
            await payment_service.handle_payment_overdue(
                asaas_payment_id=payment_id,
                order_id=external_ref,
            )

        elif event == "PAYMENT_REFUNDED":
            # Pagamento estornado
            await payment_service.handle_payment_refunded(
                asaas_payment_id=payment_id,
                order_id=external_ref,
            )

        else:
            logger.info(f"Evento de pagamento ignorado: {event}")

    except Exception as e:
        logger.error(f"Erro ao processar webhook de pagamento: {e}")


# ==================== Health Check ====================

@router.get("/health")
async def webhooks_health():
    """Verifica se os webhooks estão funcionando."""
    return {
        "status": "healthy",
        "waha_webhook": "/webhooks/waha",
        "asaas_webhook": "/webhooks/asaas",
    }
