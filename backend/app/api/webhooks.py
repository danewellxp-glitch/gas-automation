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
        event = body.get("event", "")
        session = body.get("session", "")
        payload = body.get("payload", {})
        # Log em INFO para diagnóstico: ver se o WAHA está chamando o backend
        logger.info(
            f"WAHA Webhook recebido: event={event} session={session} "
            f"payload_keys={list(payload.keys()) if isinstance(payload, dict) else 'n/a'}"
        )

        # Processar apenas mensagens recebidas
        if event == "message":
            # Ignorar mensagens enviadas por nós
            from_me = payload.get("fromMe", False)
            if from_me:
                logger.info("WAHA: ignorando mensagem própria (fromMe=true)")
                return {"status": "ignored", "reason": "own_message"}

            # WAHA usa LID (Linked ID) - resolver para @c.us quando possível
            # from: "7185547411514@lid" ou "5541999999999@c.us"
            raw_from = payload.get("from")
            chat_id = (str(raw_from).strip() if raw_from is not None and raw_from != "" else "")

            # Se @lid, tentar resolver para @c.us usando campos do payload
            if chat_id and "@lid" in chat_id:
                resolved = None
                # Fonte 1: campo 'id' do payload (formato: "false_5541999999@c.us_MSGID")
                raw_id = payload.get("id", "")
                if raw_id and "@c.us" in raw_id:
                    parts = raw_id.split("_")
                    for part in parts:
                        if "@c.us" in part:
                            resolved = part
                            break
                # Fonte 2: _data.key.participant ou _data.participant
                if not resolved:
                    _data = payload.get("_data", {}) or {}
                    participant = (
                        (_data.get("key", {}) or {}).get("participant", "")
                        or _data.get("participant", "")
                    )
                    if participant and "@c.us" in str(participant):
                        resolved = str(participant)
                # Fonte 3: WAHA resolve_lid via API
                if not resolved:
                    try:
                        from app.integrations.waha import waha_client
                        resolved_lid = await waha_client.resolve_lid(chat_id)
                        if resolved_lid and "@c.us" in resolved_lid:
                            resolved = resolved_lid
                    except Exception as e:
                        logger.debug(f"Resolve LID via API falhou: {e}")

                if resolved:
                    logger.info(f"LID resolvido no webhook: {chat_id} -> {resolved}")
                    chat_id = resolved
                else:
                    logger.warning(f"Não foi possível resolver LID {chat_id} - mantendo formato original")
            if not chat_id:
                logger.warning(
                    "WAHA Webhook: ignorando mensagem com chat_id vazio (payload.from ausente ou vazio)"
                )
                return {"status": "ignored", "reason": "empty_chat_id"}

            # Extrair dados
            key_data = {
                "remoteJid": chat_id,
                "fromMe": from_me,
                "id": payload.get("id", "").split("_")[-1] if payload.get("id") else "",
            }

            # Corpo da mensagem: WAHA pode enviar body no topo ou em _data
            message_body = (
                payload.get("body")
                or (payload.get("_data") or {}).get("body")
                or (payload.get("_data") or {}).get("content")
                or ""
            )
            if isinstance(message_body, dict):
                message_body = message_body.get("text") or message_body.get("body") or ""
            message_body = (message_body or "").strip()
            sender_name = (payload.get("_data") or {}).get("notifyName") or payload.get("pushName") or ""

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

    Fluxo otimizado (FLUXO_BOT_IDEAL):
    1. Deduplicação por message_id (Redis SET NX)
    2. Feedback imediato: typing + mark as read
    3. Processamento: WebSocket → EventLog → Flow Engine
    4. Resposta: stop typing → enviar mensagens
    """
    phone = message.phone
    text = message.text
    button_id = message.button_id
    location = message.location
    message_id = message.key.id if message.key else None

    # ── ETAPA 1: Deduplicação (< 100ms) ──
    if message_id:
        try:
            is_duplicate = await redis_manager.check_message_processed(message_id)
            if is_duplicate:
                logger.info(f"Mensagem duplicada ignorada: message_id={message_id} phone={phone}")
                return
        except Exception as e:
            logger.warning(f"Dedup check falhou (processando mesmo assim): {e}")

    # ── ETAPA 2: Feedback imediato (< 500ms) ──
    from app.integrations.waha import waha_client

    try:
        await waha_client.start_typing(phone)
    except Exception:
        pass

    if message_id:
        try:
            await waha_client.mark_as_read(phone, message_id)
        except Exception:
            pass

    # ── ETAPA 3: Processar mensagem ──
    try:
        # Processar localização se presente
        if location:
            logger.info(f"Localização recebida de {phone}: {location}")
            try:
                await waha_client.stop_typing(phone)
            except Exception:
                pass
            await process_location_message(phone, location, message_id)
            return

        # Usar button_id se não tiver texto (clique em botão)
        content = (text or button_id or "").strip()

        # Mensagem vazia (ex.: só mídia): tratar como "menu" para o bot sempre responder
        if not content:
            logger.info(f"Mensagem sem texto de {phone}; tratando como menu")
            content = "menu"

        logger.info(f"Processando mensagem de {phone}: {content[:50]}")

        # Emitir WebSocket para painel do operador
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
        from app.core.flow_engine import flow_engine

        result = await flow_engine.process_message(
            phone=phone,
            message=content,
            message_id=message_id,
        )

        # ── ETAPA 4: Resposta ──
        try:
            await waha_client.stop_typing(phone)
        except Exception:
            pass

        # Enviar respostas
        if result.responses:
            await flow_engine.send_responses(phone, result.responses)

        logger.info(
            f"Mensagem processada: {phone} | "
            f"Estado: {result.context.state} -> {result.new_state}"
        )

    except Exception as e:
        logger.error(f"Erro ao processar mensagem no flow engine: {e}", exc_info=True)
        try:
            await waha_client.stop_typing(phone)
        except Exception:
            pass
        # Tentar enviar mensagem de erro ao usuário
        try:
            await waha_client.send_text(
                phone,
                "Desculpe, ocorreu um erro. Digite *menu* para recomeçar."
            )
        except Exception as send_err:
            logger.warning(f"Não foi possível enviar mensagem de erro para {message.phone}: {send_err}")


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
