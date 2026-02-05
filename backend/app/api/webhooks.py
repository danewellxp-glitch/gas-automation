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
from app.core.webhook_security import verify_waha_signature

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

    Segurança:
    - Requer header X-WAHA-Signature com HMAC-SHA256 (quando WAHA_WEBHOOK_SECRET configurado)
    """
    # Validar assinatura HMAC (se secret configurado)
    await verify_waha_signature(request)

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

    Fluxo otimizado para UX:
    1. Verificar duplicata (evitar processar 2x)
    2. Marcar como lida imediatamente (✓✓)
    3. Mostrar "digitando..." (feedback visual)
    4. Emitir WebSocket (painel operador)
    5. Processar no flow engine
    6. Enviar resposta
    """
    phone = message.phone
    text = message.text
    button_id = message.button_id
    location = message.location
    message_id = message.key.id if message.key else None

    # =========== ETAPA 1: DEDUPLICAÇÃO ===========
    # Evita processar a mesma mensagem 2x (retry do WAHA)
    if message_id:
        is_duplicate = await _check_message_duplicate(message_id)
        if is_duplicate:
            logger.info(f"[DEDUP] Mensagem duplicada ignorada: {message_id}")
            return

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

    logger.info(f"[MSG] {phone} | {content[:50]}")

    # =========== ETAPA 2: FEEDBACK IMEDIATO ===========
    # Mostrar que recebemos a mensagem (melhora UX)
    try:
        from app.integrations.waha import waha_client

        # Marcar como lida IMEDIATAMENTE (✓✓ azul)
        if message_id:
            await waha_client.mark_as_read(phone, message_id)
            logger.debug(f"[READ] Mensagem marcada como lida: {message_id}")

        # Mostrar "digitando..." (feedback visual para o cliente)
        await waha_client.send_typing(phone, True)
        logger.debug(f"[TYPING] Iniciado para {phone}")

    except Exception as e:
        logger.warning(f"[FEEDBACK] Erro ao enviar feedback: {e}")

    # =========== ETAPA 3: NOTIFICAR PAINEL ===========
    # Emitir WebSocket para operador ver em tempo real
    try:
        from app.api.websocket import emit_new_message
        await emit_new_message(phone, content, "incoming")
    except Exception as e:
        logger.error(f"[WS] Erro ao emitir WebSocket: {e}")

    # =========== ETAPA 4: SALVAR LOG ===========
    try:
        async with AsyncSessionLocal() as db:
            event = EventLog(
                event_type="message_received",
                entity_type="chat",
                payload={"phone": phone, "message": content, "message_id": message_id}
            )
            db.add(event)
            await db.commit()
    except Exception as e:
        logger.warning(f"[LOG] Erro ao salvar EventLog: {e}")

    # =========== ETAPA 5: PROCESSAR MENSAGEM ===========
    try:
        from app.core.flow_engine import flow_engine

        # Processar mensagem pelo flow engine
        result = await flow_engine.process_message(
            phone=phone,
            message=content,
            message_id=message_id,
        )

        # =========== ETAPA 6: ENVIAR RESPOSTA ===========
        # Parar "digitando..." e enviar resposta
        try:
            from app.integrations.waha import waha_client
            await waha_client.send_typing(phone, False)
        except Exception:
            pass  # Ignorar erro ao parar typing

        if result.responses:
            await flow_engine.send_responses(phone, result.responses)

        logger.info(f"[OK] {phone} | {result.context.state.value} -> {result.new_state.value}")

    except Exception as e:
        logger.error(f"[ERRO] {phone} | {e}", exc_info=True)

        # Parar "digitando..." em caso de erro
        try:
            from app.integrations.waha import waha_client
            await waha_client.send_typing(phone, False)
            await waha_client.send_text(
                phone,
                "Desculpe, ocorreu um erro. Digite *menu* para recomeçar."
            )
        except Exception as send_error:
            logger.warning(f"[ERRO] Não foi possível enviar erro para {phone}: {send_error}")


async def _check_message_duplicate(message_id: str) -> bool:
    """
    Verifica se a mensagem já foi processada (deduplicação).

    Usa Redis SET com TTL de 1 hora para evitar processar a mesma
    mensagem 2x (por exemplo, em caso de retry do WAHA).

    Returns:
        True se já foi processada (duplicata), False se é nova
    """
    if not message_id:
        return False

    try:
        key = f"msg_processed:{message_id}"

        # Tentar setar a chave com NX (só seta se não existir)
        # Se retornar True, é a primeira vez (nova mensagem)
        # Se retornar False/None, já existe (duplicata)
        was_set = await redis_manager.client.set(
            key,
            "1",
            nx=True,  # Só seta se não existir
            ex=3600   # TTL de 1 hora
        )

        if was_set:
            logger.debug(f"[DEDUP] Nova mensagem registrada: {message_id}")
            return False  # Nova mensagem
        else:
            logger.debug(f"[DEDUP] Mensagem já existe: {message_id}")
            return True  # Duplicata

    except Exception as e:
        logger.warning(f"[DEDUP] Erro ao verificar duplicata: {e}")
        return False  # Em caso de erro, processa a mensagem


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
