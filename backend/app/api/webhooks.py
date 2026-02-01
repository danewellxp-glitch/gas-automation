"""
Webhook handlers para WAHA (WhatsApp).

Nota: integração Asaas/Pix foi descontinuada (não utilizada).
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, redis_manager, AsyncSessionLocal
from app.models.event_log import EventLog
from app.schemas.webhook import (
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

        # Log estruturado em vez de print
        logger.debug(f"WAHA Webhook recebido: {body.get('event', 'unknown')}")

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

            logger.info(f"Processando mensagem - ChatID: {chat_id}, Sender: {sender_name}")

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
    Suporta: texto, botões e localização.
    """
    phone = message.phone
    text = message.text
    button_id = message.button_id
    location = message.location
    message_id = message.key.id if message.key else None

    # Processar localização se presente
    if location:
        logger.info(f"Localização recebida de {phone}: {location}")
        await process_location_message(phone, location, message_id)
        return

    # Usar button_id se não tiver texto (clique em botão)
    content = text or button_id or ""

    if not content:
        logger.warning(f"Mensagem sem conteúdo de {phone}")
        return

    logger.info(f"Processando mensagem de {phone}: {content[:50]}")

    # EMITIR WEBSOCKET IMEDIATAMENTE (antes de qualquer processamento complexo)
    try:
        from app.api.websocket import emit_new_message
        await emit_new_message(phone, content, "incoming")
        logger.info(f"WebSocket emitido para {phone}: {content[:50]}")
    except Exception as e:
        logger.error(f"Erro ao emitir WebSocket: {e}", exc_info=True)

    # Salvar mensagem recebida no EventLog
    try:
        async with AsyncSessionLocal() as db:
            event = EventLog(
                event_type="message_received",
                entity_type="chat",
                payload={"phone": phone, "message": content}
            )
            db.add(event)
            await db.commit()
    except Exception as e:
        logger.warning(f"Erro ao salvar EventLog: {e}")

    # Processar mensagem pelo flow engine
    try:
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
    except Exception as e:
        logger.error(f"Erro ao processar mensagem no flow engine: {e}", exc_info=True)
        # Tentar enviar mensagem de erro ao usuário
        try:
            from app.integrations.waha import waha_client
            await waha_client.send_text(
                message.phone,
                "Desculpe, ocorreu um erro. Digite *menu* para recomeçar."
            )
        except Exception as e:
            logger.warning(f"Não foi possível enviar mensagem de erro para {message.phone}: {e}")


async def process_location_message(phone: str, location: dict, message_id: str = None):
    """
    Processa mensagem de localização do WhatsApp.

    Salva as coordenadas no contexto da conversa e notifica via WebSocket.
    """
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    address = location.get("address", "")
    name = location.get("name", "")

    logger.info(f"Processando localização: lat={latitude}, lng={longitude}, addr={address}")

    # Emitir via WebSocket para o operador ver
    try:
        from app.api.websocket import emit_new_message
        location_text = f"📍 Localização recebida: {name or address or f'{latitude}, {longitude}'}"
        await emit_new_message(phone, location_text, "incoming")
    except Exception as e:
        logger.error(f"Erro ao emitir WebSocket de localização: {e}")

    # Salvar no EventLog
    try:
        async with AsyncSessionLocal() as db:
            event = EventLog(
                event_type="location_received",
                entity_type="chat",
                payload={
                    "phone": phone,
                    "latitude": latitude,
                    "longitude": longitude,
                    "address": address,
                    "name": name,
                }
            )
            db.add(event)
            await db.commit()
    except Exception as e:
        logger.warning(f"Erro ao salvar EventLog de localização: {e}")

    # Atualizar contexto da conversa com a localização
    try:
        from app.core.flow_engine import flow_engine

        # Buscar contexto atual
        context = await flow_engine.get_context(phone)
        if context:
            # Salvar localização no contexto (campo address)
            context.address = context.address or {}
            context.address["location"] = {
                "latitude": latitude,
                "longitude": longitude,
            }
            if address:
                context.address["formatted"] = address
            if name:
                context.address["name"] = name
            await flow_engine.save_context(context)
            logger.info(f"Localização salva no contexto de {phone}")

        # Enviar confirmação ao cliente
        from app.integrations.waha import waha_client
        await waha_client.send_text(
            phone,
            f"📍 Localização recebida!\n"
            f"Coordenadas: {latitude:.6f}, {longitude:.6f}\n"
            f"{f'Endereço: {address}' if address else ''}\n\n"
            f"Vamos usar esta localização para a entrega."
        )
    except Exception as e:
        logger.error(f"Erro ao processar localização no flow: {e}", exc_info=True)


# ==================== Health Check ====================

@router.get("/health")
async def webhooks_health():
    """Verifica se os webhooks estão funcionando."""
    return {
        "status": "healthy",
        "waha_webhook": "/webhooks/waha",
    }
