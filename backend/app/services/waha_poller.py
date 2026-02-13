"""
WAHA Message Poller - Alternativa ao webhook quando há bug no WAHA.

Este serviço faz polling periódico das mensagens no WAHA e processa
as novas mensagens que ainda não foram processadas.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Set

from app.config import settings
from app.database import redis_manager

logger = logging.getLogger(__name__)


class WAHAPoller:
    """
    Poller de mensagens do WAHA.

    Verifica periodicamente novas mensagens e as processa
    como se tivessem chegado via webhook.
    """

    def __init__(self, interval_seconds: int = 3):
        self.interval = interval_seconds
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._processed_ids: Set[str] = set()
        self._last_check: Optional[datetime] = None

    async def start(self):
        """Inicia o poller em background."""
        if self.running:
            logger.warning("WAHA Poller já está rodando")
            return

        self.running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"WAHA Poller iniciado (intervalo: {self.interval}s)")

    async def stop(self):
        """Para o poller."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("WAHA Poller parado")

    async def _poll_loop(self):
        """Loop principal de polling."""
        import httpx

        base_url = settings.waha_url.rstrip("/")
        headers = {"X-Api-Key": settings.waha_api_key}

        while self.running:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    # Verificar status da sessão
                    status_resp = await client.get(
                        f"{base_url}/api/sessions/{settings.waha_session_name}",
                        headers=headers
                    )

                    if status_resp.status_code != 200:
                        logger.debug("Sessão WAHA não disponível")
                        await asyncio.sleep(self.interval)
                        continue

                    session_data = status_resp.json()
                    if session_data.get("status") != "WORKING":
                        logger.debug(f"Sessão WAHA não WORKING: {session_data.get('status')}")
                        await asyncio.sleep(self.interval)
                        continue

                    # Buscar chats com mensagens não lidas
                    chats_resp = await client.get(
                        f"{base_url}/api/{settings.waha_session_name}/chats",
                        headers=headers,
                        params={"limit": 20}
                    )

                    if chats_resp.status_code != 200:
                        await asyncio.sleep(self.interval)
                        continue

                    chats = chats_resp.json()
                    
                    total_unread = sum(chat.get("unreadCount", 0) for chat in chats)
                    if total_unread > 0:
                        logger.info(f"[Poller] Encontrados {total_unread} mensagens não lidas em {len(chats)} chats")

                    for chat in chats:
                        chat_id = chat.get("id", {})
                        if isinstance(chat_id, dict):
                            chat_id = chat_id.get("_serialized", "")

                        unread = chat.get("unreadCount", 0)
                        if unread > 0:
                            logger.debug(f"[Poller] Chat {chat_id} tem {unread} mensagens não lidas")
                            await self._process_chat_messages(client, base_url, headers, chat_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no WAHA Poller: {e}")

            await asyncio.sleep(self.interval)

    async def _process_chat_messages(self, client, base_url: str, headers: dict, chat_id: str):
        """Processa mensagens não lidas de um chat."""
        try:
            # Buscar mensagens recentes do chat
            messages_resp = await client.get(
                f"{base_url}/api/{settings.waha_session_name}/chats/{chat_id}/messages",
                headers=headers,
                params={"limit": 10, "downloadMedia": False}
            )

            if messages_resp.status_code != 200:
                logger.warning(f"[Poller] Erro ao buscar mensagens do chat {chat_id}: {messages_resp.status_code}")
                return

            messages = messages_resp.json()
            logger.debug(f"[Poller] Chat {chat_id}: {len(messages)} mensagens retornadas")

            for msg in messages:
                # Extrair message_id corretamente (WAHA pode retornar em diferentes formatos)
                msg_id = msg.get("id", {})
                if isinstance(msg_id, dict):
                    # Formato: {"_serialized": "false_7185547411514@lid_MSGID", "id": "MSGID"}
                    msg_id_str = msg_id.get("_serialized", "") or msg_id.get("id", "")
                    if not msg_id_str and "_data" in msg:
                        # Tentar extrair de _data.key
                        _data = msg.get("_data", {})
                        key = _data.get("id", {})
                        if isinstance(key, dict):
                            msg_id_str = key.get("_serialized", "") or key.get("id", "")
                else:
                    msg_id_str = str(msg_id) if msg_id else ""

                if not msg_id_str:
                    logger.warning(f"[Poller] Mensagem sem ID válido: {msg}")
                    continue

                # Ignorar mensagens já processadas (cache local)
                if msg_id_str in self._processed_ids:
                    continue

                # Ignorar mensagens próprias
                from_me = msg.get("fromMe", False) or (msg.get("_data", {}).get("key", {}).get("fromMe", False))
                if from_me:
                    self._processed_ids.add(msg_id_str)
                    continue

                # Ignorar mensagens antigas (mais de 5 minutos)
                timestamp = msg.get("timestamp", 0) or msg.get("_data", {}).get("t", 0)
                if timestamp:
                    # Timestamp pode estar em segundos ou milissegundos
                    if timestamp > 1e10:  # Milissegundos
                        timestamp = timestamp / 1000
                    try:
                        msg_time = datetime.fromtimestamp(timestamp)
                        if datetime.now() - msg_time > timedelta(minutes=5):
                            self._processed_ids.add(msg_id_str)
                            continue
                    except (ValueError, OSError):
                        pass  # Timestamp inválido, processar mesmo assim

                # ── DEDUP Redis: verificar se webhook já processou ──
                if msg_id_str:
                    try:
                        is_dup = await redis_manager.check_message_processed(msg_id_str)
                        if is_dup:
                            self._processed_ids.add(msg_id_str)
                            logger.debug(f"[Poller] DEDUP Redis: {msg_id_str} já processado")
                            continue
                    except Exception as e:
                        logger.debug(f"[Poller] Redis dedup check falhou: {e}")

                # Processar a mensagem
                logger.info(f"[Poller] Processando mensagem: chat={chat_id} msg_id={msg_id_str} body={msg.get('body', '')[:50]}")
                await self._process_message(msg, chat_id)
                self._processed_ids.add(msg_id_str)

                # Limitar cache de IDs processados
                if len(self._processed_ids) > 1000:
                    self._processed_ids = set(list(self._processed_ids)[-500:])

        except Exception as e:
            logger.error(f"Erro ao processar mensagens do chat {chat_id}: {e}")

    async def _process_message(self, msg: dict, chat_id: str):
        """Processa uma mensagem individual."""
        try:
            from app.api.webhooks import process_whatsapp_message
            from app.schemas.webhook import WAHAMessage

            # Extrair dados da mensagem (WAHA pode retornar em diferentes formatos)
            msg_id = msg.get("id", {})
            if isinstance(msg_id, dict):
                msg_id_str = msg_id.get("_serialized", "") or msg_id.get("id", "")
                if not msg_id_str and "_data" in msg:
                    _data = msg.get("_data", {})
                    key = _data.get("id", {})
                    if isinstance(key, dict):
                        msg_id_str = key.get("_serialized", "") or key.get("id", "")
            else:
                msg_id_str = str(msg_id) if msg_id else ""

            # Extrair body (pode estar em _data.body ou body)
            body = msg.get("body", "") or msg.get("_data", {}).get("body", "")
            
            # Extrair timestamp (pode estar em timestamp ou _data.t)
            timestamp = msg.get("timestamp", 0) or msg.get("_data", {}).get("t", 0)
            if timestamp > 1e10:  # Converter milissegundos para segundos
                timestamp = int(timestamp / 1000)
            
            # Extrair push_name
            push_name = (
                msg.get("_data", {}).get("notifyName", "") 
                or msg.get("notifyName", "")
                or msg.get("pushName", "")
            )

            # Resolver LID para número real se necessário
            original_chat_id = None
            resolved_chat_id = chat_id
            if "@lid" in chat_id:
                original_chat_id = chat_id
                try:
                    from app.integrations.waha import waha_client
                    resolved = await waha_client.resolve_lid(chat_id)
                    if resolved != chat_id:
                        resolved_chat_id = resolved
                        logger.info(f"[Poller] LID resolvido: {chat_id} -> {resolved}")
                except Exception as e:
                    logger.debug(f"[Poller] LID resolve falhou: {e}")

            # Montar objeto WAHAMessage com chat_id resolvido
            key_data = {
                "remoteJid": resolved_chat_id,
                "fromMe": False,
                "id": msg_id_str,
            }

            message = WAHAMessage(
                key=key_data,
                message={"conversation": body} if body else None,
                messageTimestamp=timestamp,
                pushName=push_name,
            )

            # Gerar trace_id único para rastreamento completo do pipeline
            import uuid
            trace_id = f"trace-{uuid.uuid4().hex[:12]}"
            
            logger.info(
                f"[POLLER_MESSAGE_FOUND] trace_id={trace_id} chat={resolved_chat_id} "
                f"msg_id={msg_id_str} body={body[:50] if body else '(vazio)'}",
                extra={
                    "trace_id": trace_id,
                    "chat_id": resolved_chat_id,
                    "message_id": msg_id_str,
                    "step": "poller_message_found"
                }
            )

            # Adicionar mensagem ao Redis Stream em vez de processar diretamente
            # Isso garante que todas as mensagens passem pelo mesmo pipeline
            message_data = {
                "key": key_data,
                "message": {"conversation": body} if body else None,
                "messageTimestamp": timestamp,
                "pushName": push_name,
            }
            
            logger.info(
                f"[POLLER_STREAM_ADD_START] trace_id={trace_id} message_id={msg_id_str} "
                f"phone={resolved_chat_id}",
                extra={
                    "trace_id": trace_id,
                    "message_id": msg_id_str,
                    "phone": resolved_chat_id,
                    "step": "poller_stream_add_start"
                }
            )
            
            stream_message_id = await redis_manager.add_message_to_stream(
                message_data=message_data,
                original_chat_id=original_chat_id,
                trace_id=trace_id,  # Passar trace_id para o stream
            )
            
            if stream_message_id:
                logger.info(
                    f"[POLLER_STREAM_ADDED] trace_id={trace_id} stream_id={stream_message_id} "
                    f"message_id={msg_id_str} phone={resolved_chat_id} success=True",
                    extra={
                        "trace_id": trace_id,
                        "stream_id": stream_message_id,
                        "message_id": msg_id_str,
                        "phone": resolved_chat_id,
                        "step": "poller_stream_added",
                        "success": True
                    }
                )
            else:
                # Fallback: processar diretamente se stream falhar
                logger.warning(
                    f"[POLLER_STREAM_FAILED] trace_id={trace_id} message_id={msg_id_str} "
                    f"phone={resolved_chat_id} using_fallback=True",
                    extra={
                        "trace_id": trace_id,
                        "message_id": msg_id_str,
                        "phone": resolved_chat_id,
                        "step": "poller_stream_failed",
                        "fallback": True
                    }
                )
                # Processar como se fosse webhook (passando original_chat_id para routing)
                await process_whatsapp_message(
                    message,
                    original_chat_id=original_chat_id,
                )

        except Exception as e:
            logger.error(f"Erro ao processar mensagem do poller: {e}", exc_info=True)


# Instância global
waha_poller = WAHAPoller(interval_seconds=3)
