"""
Webhook handlers para WAHA (WhatsApp).

Nota: integração Asaas/Pix foi descontinuada (não utilizada).
"""

import asyncio
import logging
import time
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
from app.utils.structured_logging import (
    get_structured_logger,
    MessageContextManager,
    set_message_context,
)

logger = get_structured_logger(__name__)

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
    # Gerar trace_id único ANTES de qualquer processamento
    import uuid
    trace_id = f"trace-{uuid.uuid4().hex[:12]}"
    
    try:
        logger.info(
            f"[WEBHOOK_RECEIVED] trace_id={trace_id} method={request.method} "
            f"headers={dict(request.headers)}",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "step": "webhook_received"
            }
        )
        
        # Ler body uma vez para validação e processamento
        body_bytes = await request.body()
        
        logger.debug(
            f"[WEBHOOK_BODY_READ] trace_id={trace_id} body_size={len(body_bytes)}",
            extra={
                "trace_id": trace_id,
                "body_size": len(body_bytes),
                "step": "webhook_body_read"
            }
        )
        
        # Validar assinatura HMAC (se secret configurado)
        # Criar um request temporário para validação que usa o body_bytes já lido
        class TempRequest:
            def __init__(self, headers, body_bytes):
                self.headers = headers
                self._body = body_bytes
            async def body(self):
                return self._body
        
        temp_req = TempRequest(request.headers, body_bytes)
        
        logger.debug(
            f"[WEBHOOK_SIGNATURE_CHECK_START] trace_id={trace_id}",
            extra={
                "trace_id": trace_id,
                "step": "webhook_signature_check_start"
            }
        )
        
        try:
            await verify_waha_signature(temp_req)
            logger.debug(
                f"[WEBHOOK_SIGNATURE_VALID] trace_id={trace_id}",
                extra={
                    "trace_id": trace_id,
                    "step": "webhook_signature_valid"
                }
            )
        except HTTPException as sig_err:
            logger.error(
                f"[WEBHOOK_SIGNATURE_INVALID] trace_id={trace_id} status_code={sig_err.status_code} "
                f"detail={sig_err.detail}",
                extra={
                    "trace_id": trace_id,
                    "status_code": sig_err.status_code,
                    "detail": sig_err.detail,
                    "step": "webhook_signature_invalid"
                }
            )
            raise
        
        # Parse do JSON
        import json
        try:
            body = json.loads(body_bytes.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do JSON do webhook: {e}")
            return {"status": "error", "message": "Invalid JSON"}
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

            # WAHA usa LID (Linked ID) - resolver para número real quando possível
            # from: "7185547411514@lid" ou "5541999999999@c.us"
            raw_from = payload.get("from")
            original_chat_id = (str(raw_from).strip() if raw_from is not None and raw_from != "" else "")
            chat_id = original_chat_id

            if chat_id and "@lid" in chat_id:
                # Resolução rápida via campos do próprio payload (sem API call)
                resolved = None
                # Fonte 1: campo 'id' (formato: "false_5541999999@c.us_MSGID")
                raw_id = payload.get("id", "")
                if raw_id and "@c.us" in raw_id:
                    for part in raw_id.split("_"):
                        if "@c.us" in part:
                            resolved = part
                            break
                # Fonte 2: _data.key.participant
                if not resolved:
                    _data = payload.get("_data", {}) or {}
                    participant = (
                        (_data.get("key", {}) or {}).get("participant", "")
                        or _data.get("participant", "")
                    )
                    if participant and "@c.us" in str(participant):
                        resolved = str(participant)
                # Fonte 3: WAHA /api/contacts (resolve_lid com cache Redis)
                if not resolved:
                    try:
                        from app.integrations.waha import waha_client
                        resolved = await waha_client.resolve_lid(chat_id)
                        if resolved == chat_id:
                            resolved = None  # Não conseguiu resolver
                    except Exception as e:
                        logger.debug(f"resolve_lid API falhou: {e}")

                if resolved:
                    logger.info(f"LID resolvido: {chat_id} -> {resolved}")
                    chat_id = resolved
                else:
                    logger.warning(f"LID não resolvido: {chat_id}")

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

            # ── DEDUP: Verificar se mensagem já foi processada ANTES de adicionar ao stream ──
            message_id = key_data.get("id", "")
            
            # Gerar trace_id único para rastreamento completo do pipeline
            import uuid
            trace_id = f"trace-{uuid.uuid4().hex[:12]}"
            
            # Definir contexto de mensagem para logging estruturado
            with MessageContextManager(message_id=message_id, phone=chat_id, trace_id=trace_id):
                logger.info(
                    f"[WEBHOOK_ENTRY] trace_id={trace_id} message_id={message_id} phone={chat_id} "
                    f"sender={sender_name}",
                    extra={
                        "trace_id": trace_id,
                        "message_id": message_id,
                        "phone": chat_id,
                        "step": "webhook_entry"
                    }
                )
                
                # ── FEEDBACK IMEDIATO: Marcar como lida e mostrar "digitando..." ──
                # Isso melhora muito a UX, dando feedback imediato ao cliente
                if message_id and not from_me:
                    try:
                        # 1. Marcar como lida IMEDIATAMENTE (✓✓ azul)
                        from app.integrations.waha import waha_client
                        await waha_client.mark_as_read(chat_id, message_id)
                        logger.info(
                            f"[MARK_AS_READ] trace_id={trace_id} message_id={message_id} phone={chat_id}",
                            extra={
                                "trace_id": trace_id,
                                "message_id": message_id,
                                "phone": chat_id,
                                "step": "mark_as_read"
                            }
                        )
                        
                        # 2. Iniciar "digitando..." para humanizar a experiência
                        await waha_client.start_typing(chat_id)
                        logger.info(
                            f"[TYPING_START] trace_id={trace_id} phone={chat_id}",
                            extra={
                                "trace_id": trace_id,
                                "phone": chat_id,
                                "step": "typing_start"
                            }
                        )
                    except Exception as e:
                        # Não é crítico se falhar - não deve bloquear o processamento
                        logger.debug(
                            f"[FEEDBACK_ERROR] trace_id={trace_id} message_id={message_id} error={e}",
                            extra={
                                "trace_id": trace_id,
                                "message_id": message_id,
                                "step": "feedback_error"
                            }
                        )
                
                if message_id:
                    try:
                        is_duplicate = await redis_manager.check_message_processed(message_id)
                        logger.info(
                            f"[DEDUP_RESULT] trace_id={trace_id} message_id={message_id} "
                            f"is_duplicate={is_duplicate}",
                            extra={
                                "trace_id": trace_id,
                                "message_id": message_id,
                                "is_duplicate": is_duplicate,
                                "step": "dedup_result"
                            }
                        )
                        if is_duplicate:
                            # Parar typing se mensagem for duplicada
                            if not from_me:
                                try:
                                    await waha_client.stop_typing(chat_id)
                                except:
                                    pass
                            return {"status": "duplicate", "message_id": message_id, "trace_id": trace_id}
                    except Exception as e:
                        logger.warning(
                            f"[DEDUP_ERROR] trace_id={trace_id} message_id={message_id} error={e}",
                            exc_info=True,
                            extra={
                                "trace_id": trace_id,
                                "message_id": message_id,
                                "step": "dedup_error"
                            }
                        )

            # Adicionar mensagem ao Redis Stream para processamento distribuído
            # Isso substitui BackgroundTask e garante que apenas um worker processe cada mensagem
            message_data = {
                "key": key_data,
                "message": {"conversation": message_body} if message_body else None,
                "messageTimestamp": payload.get("timestamp"),
                "pushName": sender_name or payload.get("pushName"),
            }
            
            logger.info(
                f"[STREAM_ADD_START] trace_id={trace_id} message_id={message_id} phone={chat_id}",
                extra={
                    "trace_id": trace_id,
                    "message_id": message_id,
                    "phone": chat_id,
                    "step": "stream_add_start"
                }
            )
            
            stream_message_id = await redis_manager.add_message_to_stream(
                message_data=message_data,
                original_chat_id=original_chat_id if original_chat_id != chat_id else None,
                trace_id=trace_id,  # Passar trace_id para o stream
            )
            
            if stream_message_id:
                logger.info(
                    f"[STREAM_ADDED] trace_id={trace_id} stream_id={stream_message_id} "
                    f"message_id={message_id} phone={chat_id} success=True",
                    extra={
                        "trace_id": trace_id,
                        "stream_id": stream_message_id,
                        "message_id": message_id,
                        "phone": chat_id,
                        "step": "stream_added",
                        "success": True
                    }
                )
                return {"status": "queued", "stream_id": stream_message_id, "trace_id": trace_id}
            else:
                # Fallback: se stream falhar, usar BackgroundTask (compatibilidade)
                logger.warning(
                    f"[STREAM_FAILED] trace_id={trace_id} message_id={message_id} "
                    f"phone={chat_id} using_fallback=True",
                    extra={
                        "trace_id": trace_id,
                        "message_id": message_id,
                        "phone": chat_id,
                        "step": "stream_failed",
                        "fallback": True
                    }
                )
                background_tasks.add_task(
                    process_whatsapp_message,
                    message=message,
                    original_chat_id=original_chat_id if original_chat_id != chat_id else None,
                )
                return {"status": "processing", "fallback": "background_task", "trace_id": trace_id}

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

    except HTTPException:
        # Re-raise HTTPException (401, etc) para retornar status code correto
        raise
    except Exception as e:
        logger.error(
            f"[WEBHOOK_ERROR] trace_id={trace_id} error={e}",
            exc_info=True,
            extra={
                "trace_id": trace_id,
                "step": "webhook_error"
            }
        )
        # Retornar 200 para evitar retry do WAHA
        return {"status": "error", "message": str(e), "trace_id": trace_id}


async def process_whatsapp_message(
    message: WAHAMessage,
    original_chat_id: str = None,
):
    """
    Processa mensagem do WhatsApp em background.

    Fluxo otimizado:
    1. Deduplicação por message_id (Redis SET NX)
    2. Lock distribuído por telefone (impede processamento concorrente)
    3. Feedback imediato: typing + mark as read
    4. Processamento: WebSocket → EventLog → Flow Engine
    5. Resposta: stop typing → enviar mensagens
    6. Release lock
    """
    phone = message.phone
    text = message.text
    button_id = message.button_id
    location = message.location
    message_id = message.key.id if message.key else None
    
    # Obter trace_id do contexto ou gerar novo
    from app.utils.structured_logging import get_message_context
    context_data = get_message_context()
    trace_id = context_data.get("trace_id") or (f"trace-{message_id[:8]}" if message_id else None)
    
    # Definir contexto de mensagem para logging estruturado
    with MessageContextManager(message_id=message_id, phone=phone, trace_id=trace_id):
        # ── ETAPA 1: Deduplicação (< 100ms) ──
        # NOTA: Dedup já foi feito no webhook ANTES de adicionar ao stream
        # Este dedup aqui é redundante e pode causar problemas se mensagem já foi processada antes
        # REMOVIDO: Dedup duplicado causa mensagens serem descartadas incorretamente
        # Se mensagem chegou aqui via stream, já passou pelo dedup do webhook
        # Se chegou via Poller direto (fallback), dedup pode estar marcando como duplicada incorretamente
        
        # Log apenas para debug, mas não descartar mensagem
        if message_id:
            try:
                is_duplicate = await redis_manager.check_message_processed(message_id)
                logger.info(
                    f"[DEDUP_CHECK_STREAM] trace_id={trace_id} message_id={message_id} "
                    f"phone={phone} is_duplicate={is_duplicate} (não descartando - já passou pelo dedup do webhook)",
                    extra={
                        "trace_id": trace_id,
                        "message_id": message_id,
                        "phone": phone,
                        "is_duplicate": is_duplicate,
                        "step": "dedup_check_stream"
                    }
                )
                # ❌ NÃO descartar aqui - mensagem já passou pelo dedup do webhook
                # Se chegou aqui via stream, é porque não era duplicada no webhook
                # Se chegou aqui via Poller direto (fallback), pode estar marcada como duplicada incorretamente
                # Melhor processar mesmo assim para garantir que mensagem não seja perdida
                if is_duplicate:
                    logger.warning(
                        f"[DEDUP_WARNING] trace_id={trace_id} message_id={message_id} phone={phone} "
                        f"marcada como duplicada mas processando mesmo assim (pode ser processamento anterior)",
                        extra={
                            "trace_id": trace_id,
                            "message_id": message_id,
                            "phone": phone,
                            "step": "dedup_warning"
                        }
                    )
                    # Não retornar - processar mesmo assim
            except Exception as e:
                logger.warning(
                    f"[DEDUP_ERROR] trace_id={trace_id} message_id={message_id} phone={phone} error={e}",
                    exc_info=True,
                    extra={
                        "trace_id": trace_id,
                        "message_id": message_id,
                        "phone": phone,
                        "step": "dedup_error"
                    }
                )
        else:
            logger.warning(
                f"[DEDUP_NO_ID] trace_id={trace_id} phone={phone} - dedup impossível",
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "step": "dedup_no_id"
                }
            )

        # ── ETAPA 2: Lock distribuído por telefone ──
        from app.integrations.waha import waha_client

        # Normalizar phone para chave de lock consistente
        normalized_phone = phone.split("@")[0] if "@" in phone else phone
        lock_id = f"{message_id or 'no_id'}:{time.time()}"
        lock_acquired = False

        logger.info(
            f"[LOCK_ACQUIRE_START] trace_id={trace_id} phone={normalized_phone} "
            f"message_id={message_id} lock_id={lock_id}",
            extra={
                "trace_id": trace_id,
                "phone": normalized_phone,
                "message_id": message_id,
                "lock_id": lock_id,
                "step": "lock_acquire_start"
            }
        )

        try:
            lock_acquired = await redis_manager.acquire_phone_lock(
                normalized_phone, lock_id, ttl=30
            )
            if not lock_acquired:
                logger.warning(
                    f"[LOCK_CONTENTION] trace_id={trace_id} phone={normalized_phone} "
                    f"message_id={message_id} attempt=1",
                    extra={
                        "trace_id": trace_id,
                        "phone": normalized_phone,
                        "message_id": message_id,
                        "attempt": 1,
                        "step": "lock_contention"
                    }
                )
                # Esperar e tentar uma vez
                await asyncio.sleep(1.5)
                lock_acquired = await redis_manager.acquire_phone_lock(
                    normalized_phone, lock_id, ttl=30
                )
                if not lock_acquired:
                    logger.error(
                        f"[LOCK_FAILED] trace_id={trace_id} phone={normalized_phone} "
                        f"message_id={message_id} attempt=2 - re-queuing to stream",
                        extra={
                            "trace_id": trace_id,
                            "phone": normalized_phone,
                            "message_id": message_id,
                            "attempt": 2,
                            "step": "lock_failed"
                        }
                    )
                    # ❌ NÃO descartar - re-adicionar ao stream para retry
                    # Isso evita perder mensagens em caso de alta concorrência
                    message_data = {
                        "key": message.key.__dict__ if message.key else {},
                        "message": message.message,
                        "messageTimestamp": message.messageTimestamp,
                        "pushName": message.pushName,
                    }
                    await asyncio.sleep(2)  # Pequeno delay antes de re-queue
                    retry_stream_id = await redis_manager.add_message_to_stream(
                        message_data=message_data,
                        original_chat_id=original_chat_id,
                    )
                    if retry_stream_id:
                        logger.info(
                            f"[LOCK_REQUEUED] trace_id={trace_id} phone={normalized_phone} "
                            f"message_id={message_id} retry_stream_id={retry_stream_id}",
                            extra={
                                "trace_id": trace_id,
                                "phone": normalized_phone,
                                "message_id": message_id,
                                "retry_stream_id": retry_stream_id,
                                "step": "lock_requeued"
                            }
                        )
                    return
            else:
                logger.info(
                    f"[LOCK_ACQUIRED] trace_id={trace_id} phone={normalized_phone} "
                    f"message_id={message_id} lock_id={lock_id} success=True",
                    extra={
                        "trace_id": trace_id,
                        "phone": normalized_phone,
                        "message_id": message_id,
                        "lock_id": lock_id,
                        "step": "lock_acquired",
                        "success": True
                    }
                )
        except Exception as e:
            logger.warning(
                f"[LOCK_ERROR] trace_id={trace_id} phone={normalized_phone} "
                f"message_id={message_id} error={e} - processing anyway",
                exc_info=True,
                extra={
                    "trace_id": trace_id,
                    "phone": normalized_phone,
                    "message_id": message_id,
                    "step": "lock_error"
                }
            )
            lock_acquired = False  # fail-open

        try:
            # ── ETAPA 3: Feedback imediato (< 500ms) ──
            try:
                await waha_client.start_typing(phone)
            except Exception:
                pass

            if message_id:
                try:
                    await waha_client.mark_as_read(phone, message_id)
                except Exception:
                    pass

            # ── ETAPA 4: Processar mensagem ──
            # Processar localização se presente
            if location:
                logger.info(
                    f"[LOCATION_RECEIVED] trace_id={trace_id} phone={phone} message_id={message_id}",
                    extra={
                        "trace_id": trace_id,
                        "phone": phone,
                        "message_id": message_id,
                        "step": "location_received"
                    }
                )
                try:
                    await waha_client.stop_typing(phone)
                except Exception:
                    pass
                await process_location_message(phone, location, message_id)
                return

            # Usar button_id se não tiver texto (clique em botão)
            content = (text or button_id or "").strip()

            # Mensagem vazia (ex.: só mídia): tratar como "menu"
            if not content:
                logger.info(
                    f"[EMPTY_MESSAGE] trace_id={trace_id} phone={phone} treating_as_menu",
                    extra={
                        "trace_id": trace_id,
                        "phone": phone,
                        "step": "empty_message"
                    }
                )
                content = "menu"

            logger.info(
                f"[PROCESSING_START] trace_id={trace_id} phone={phone} message_id={message_id} "
                f"content={content[:50]}",
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "message_id": message_id,
                    "content": content[:50],
                    "step": "processing_start"
                }
            )

            # Emitir WebSocket para painel do operador
            try:
                from app.api.websocket import emit_new_message
                logger.info(
                    f"[WEBSOCKET_EMIT_START] trace_id={trace_id} phone={phone} event_type=new_message",
                    extra={
                        "trace_id": trace_id,
                        "phone": phone,
                        "event_type": "new_message",
                        "step": "websocket_emit_start"
                    }
                )
                await emit_new_message(phone, content, "incoming")
                logger.info(
                    f"[WEBSOCKET_EMIT_COMPLETE] trace_id={trace_id} phone={phone} success=True",
                    extra={
                        "trace_id": trace_id,
                        "phone": phone,
                        "step": "websocket_emit_complete",
                        "success": True
                    }
                )
            except Exception as e:
                logger.error(
                    f"[WEBSOCKET_EMIT_ERROR] trace_id={trace_id} phone={phone} error={e}",
                    exc_info=True,
                    extra={
                        "trace_id": trace_id,
                        "phone": phone,
                        "step": "websocket_emit_error"
                    }
                )

            # Salvar mensagem recebida no EventLog
            try:
                async with AsyncSessionLocal() as db:
                    event = EventLog(
                        event_type="message_received",
                        entity_type="chat",
                        payload={
                            "phone": phone,
                            "message": content,
                            "message_id": message_id,
                        }
                    )
                    db.add(event)
                    await db.commit()
            except Exception as e:
                logger.warning(
                    f"[EVENTLOG_ERROR] trace_id={trace_id} phone={phone} error={e}",
                    extra={
                        "trace_id": trace_id,
                        "phone": phone,
                        "step": "eventlog_error"
                    }
                )

            # Processar mensagem pelo flow engine
            from app.core.flow_engine import flow_engine

            logger.info(
                f"[FLOW_ENGINE_START] trace_id={trace_id} phone={phone} message_id={message_id} "
                f"content={content[:50]}",
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "message_id": message_id,
                    "step": "flow_engine_start"
                }
            )

            result = await flow_engine.process_message(
                phone=phone,
                message=content,
                message_id=message_id,
                waha_chat_id=original_chat_id or (phone if "@" in phone else None),
            )

            logger.info(
                f"[FLOW_ENGINE_COMPLETE] trace_id={trace_id} phone={phone} message_id={message_id} "
                f"new_state={result.new_state.value} responses_count={len(result.responses)} "
                f"success={result.success}",
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "message_id": message_id,
                    "new_state": result.new_state.value,
                    "responses_count": len(result.responses),
                    "success": result.success,
                    "step": "flow_engine_complete"
                }
            )

            # ── ETAPA 5: Resposta ──
            try:
                await waha_client.stop_typing(phone)
            except Exception:
                pass

            # Enviar respostas (usa waha_chat_id do contexto para rotear)
            if result.responses:
                send_to = result.context.waha_chat_id or phone
                logger.info(
                    f"[WAHA_SEND_START] trace_id={trace_id} phone={send_to} "
                    f"responses_count={len(result.responses)}",
                    extra={
                        "trace_id": trace_id,
                        "phone": send_to,
                        "responses_count": len(result.responses),
                        "step": "waha_send_start"
                    }
                )
                try:
                    send_results = await flow_engine.send_responses(send_to, result.responses, trace_id=trace_id)
                    logger.info(
                        f"[WAHA_SEND_COMPLETE] trace_id={trace_id} phone={send_to} "
                        f"sent={send_results.get('sent', 0)} failed={send_results.get('failed', 0)}",
                        extra={
                            "trace_id": trace_id,
                            "phone": send_to,
                            "sent": send_results.get("sent", 0),
                            "failed": send_results.get("failed", 0),
                            "step": "waha_send_complete"
                        }
                    )
                except Exception as send_err:
                    logger.error(
                        f"[WAHA_SEND_ERROR] trace_id={trace_id} phone={send_to} error={send_err}",
                        exc_info=True,
                        extra={
                            "trace_id": trace_id,
                            "phone": send_to,
                            "step": "waha_send_error"
                        }
                    )
                    # Tentar enviar mensagem de erro genérica
                    try:
                        await waha_client.send_text(
                            send_to,
                            "Desculpe, ocorreu um erro ao processar sua mensagem. "
                            "Digite *menu* para recomeçar."
                        )
                    except Exception:
                        pass

            logger.info(
                f"[PROCESSING_COMPLETE] trace_id={trace_id} phone={phone} message_id={message_id} | "
                f"Estado: {result.context.state.value} -> {result.new_state.value}",
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "message_id": message_id,
                    "old_state": result.context.state.value,
                    "new_state": result.new_state.value,
                    "step": "processing_complete"
                }
            )

        except Exception as e:
            logger.error(
                f"[PROCESSING_ERROR] trace_id={trace_id} phone={phone} message_id={message_id} error={e}",
                exc_info=True,
                extra={
                    "trace_id": trace_id,
                    "phone": phone,
                    "message_id": message_id,
                    "step": "processing_error"
                }
            )
            try:
                await waha_client.stop_typing(phone)
            except Exception:
                pass
            try:
                await waha_client.send_text(
                    phone,
                    "Desculpe, ocorreu um erro. Digite *menu* para recomeçar."
                )
            except Exception as send_err:
                logger.warning(
                    f"[ERROR_MSG_SEND_FAILED] trace_id={trace_id} phone={phone} error={send_err}",
                    extra={
                        "trace_id": trace_id,
                        "phone": phone,
                        "step": "error_msg_send_failed"
                    }
                )
        finally:
            # ── ETAPA 6: Liberar lock ──
            if lock_acquired:
                try:
                    logger.info(
                        f"[LOCK_RELEASE_START] trace_id={trace_id} phone={normalized_phone} lock_id={lock_id}",
                        extra={
                            "trace_id": trace_id,
                            "phone": normalized_phone,
                            "lock_id": lock_id,
                            "step": "lock_release_start"
                        }
                    )
                    released = await redis_manager.release_phone_lock(normalized_phone, lock_id)
                    logger.info(
                        f"[LOCK_RELEASE_COMPLETE] trace_id={trace_id} phone={normalized_phone} "
                        f"lock_id={lock_id} success={released}",
                        extra={
                            "trace_id": trace_id,
                            "phone": normalized_phone,
                            "lock_id": lock_id,
                            "success": released,
                            "step": "lock_release_complete"
                        }
                    )
                except Exception as release_err:
                    logger.error(
                        f"[LOCK_RELEASE_ERROR] trace_id={trace_id} phone={normalized_phone} "
                        f"lock_id={lock_id} error={release_err}",
                        exc_info=True,
                        extra={
                            "trace_id": trace_id,
                            "phone": normalized_phone,
                            "lock_id": lock_id,
                            "step": "lock_release_error"
                        }
                    )


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
