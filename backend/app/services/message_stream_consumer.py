"""
Message Stream Consumer - Processa mensagens WhatsApp via Redis Streams.

Substitui BackgroundTask por Redis Streams com consumer group para garantir
que cada mensagem seja processada por apenas um worker, eliminando race conditions.

Arquitetura:
- Webhook adiciona mensagem ao stream:messages
- Consumer group "gas-workers" distribui mensagens entre workers
- Cada worker processa mensagens e faz XACK após sucesso
- Mensagens que falham são retentadas automaticamente
- Após 3 tentativas, mensagem vai para stream:dlq (dead letter queue)
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import redis.asyncio as redis

from app.config import settings
from app.database import redis_manager
from app.utils.structured_logging import (
    get_structured_logger,
    MessageContextManager,
)

logger = get_structured_logger(__name__)

# Importar métricas Prometheus
try:
    from app.metrics import (
        stream_messages_processed_total,
        stream_messages_dlq_total,
        stream_processing_duration_seconds,
        stream_lag,
        stream_retry_count,
        stream_consumer_running,
    )
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    logger.warning("[StreamConsumer] Métricas Prometheus não disponíveis")

# Configuração do Stream
STREAM_NAME = "stream:messages"
DLQ_STREAM_NAME = "stream:dlq"
CONSUMER_GROUP = "gas-workers"
MAX_RETRIES = 3
BLOCK_TIME = 5000  # 5 segundos em ms
BATCH_SIZE = 10


class MessageStreamConsumer:
    """
    Consumer de mensagens WhatsApp via Redis Streams.
    
    Garante processamento atômico e distribuído entre múltiplos workers.
    """

    def __init__(self, consumer_name: Optional[str] = None):
        """
        Inicializa o consumer.
        
        Args:
            consumer_name: Nome único do consumer (default: worker-{uuid})
        """
        self.consumer_name = consumer_name or f"worker-{uuid.uuid4().hex[:8]}"
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def connect(self):
        """Conecta ao Redis e cria consumer group se necessário."""
        try:
            # Usar o mesmo Redis do redis_manager
            redis_url = settings.redis_url
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False,  # Redis Streams precisa de bytes
            )
            logger.info(f"[StreamConsumer] Conectado ao Redis: {redis_url}")

            # Criar consumer group se não existir
            try:
                await self.redis_client.xgroup_create(
                    name=STREAM_NAME,
                    groupname=CONSUMER_GROUP,
                    id="0",  # Começar do início do stream
                    mkstream=True,  # Criar stream se não existir
                )
                logger.info(
                    f"[StreamConsumer] Consumer group criado: {STREAM_NAME}/{CONSUMER_GROUP}"
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.debug(
                        f"[StreamConsumer] Consumer group já existe: {CONSUMER_GROUP}"
                    )
                else:
                    logger.warning(f"[StreamConsumer] Erro ao criar consumer group: {e}")

            # Criar DLQ stream se não existir (não precisa de consumer group)
            try:
                await self.redis_client.xinfo_stream(DLQ_STREAM_NAME)
            except redis.ResponseError:
                # Stream não existe, criar vazio
                await self.redis_client.xadd(DLQ_STREAM_NAME, {"init": "true"})
                await self.redis_client.xtrim(DLQ_STREAM_NAME, maxlen=0)
                logger.info(f"[StreamConsumer] DLQ stream criado: {DLQ_STREAM_NAME}")

        except Exception as e:
            logger.error(f"[StreamConsumer] Erro ao conectar: {e}", exc_info=True)
            raise

    async def disconnect(self):
        """Desconecta do Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def process_message(self, message_id: str, data: Dict[str, Any]) -> bool:
        """
        Processa uma mensagem do stream.
        
        Args:
            message_id: ID da mensagem no stream
            data: Dados da mensagem (deserializados)
            
        Returns:
            True se processado com sucesso, False caso contrário
        """
        start_time = time.time()
        try:
            # Extrair dados da mensagem
            message_data_raw = data.get("message", {})
            if isinstance(message_data_raw, str):
                try:
                    message_data = json.loads(message_data_raw)
                except json.JSONDecodeError:
                    logger.error(f"[StreamConsumer] Erro ao fazer parse de message_data: {message_data_raw[:100]}")
                    return False
            else:
                message_data = message_data_raw
            
            original_chat_id = data.get("original_chat_id") or ""
            
            # Importar aqui para evitar circular imports
            from app.api.webhooks import process_whatsapp_message
            from app.schemas.webhook import WAHAMessage, WAHAMessageKey

            # Reconstruir objeto WAHAMessage
            key_data = message_data.get("key", {})
            message = WAHAMessage(
                key=WAHAMessageKey(**key_data),
                message=message_data.get("message"),
                messageTimestamp=message_data.get("messageTimestamp"),
                pushName=message_data.get("pushName"),
            )

            # Definir contexto de mensagem para logging estruturado
            msg_id = key_data.get("id", "")
            # Extrair trace_id dos dados do stream (pode estar em data ou message_data)
            trace_id = data.get("trace_id") or message_data.get("trace_id")
            if not trace_id:
                # Gerar trace_id baseado em message_id se não encontrado
                trace_id = f"trace-{msg_id[:8]}" if msg_id else f"trace-{message_id[:8]}"
            
            # Usar trace_id extraído dos dados do stream
            with MessageContextManager(message_id=msg_id, phone=message.phone, trace_id=trace_id):
                logger.info(
                    f"[PROCESSING_STREAM_START] trace_id={trace_id} stream_msg_id={message_id} "
                    f"phone={message.phone} consumer={self.consumer_name}",
                    extra={
                        "trace_id": trace_id,
                        "stream_message_id": message_id,
                        "consumer": self.consumer_name,
                        "step": "processing_stream_start"
                    }
                )

                # Processar mensagem (mesma função que BackgroundTask usava)
                await process_whatsapp_message(
                    message=message,
                    original_chat_id=original_chat_id,
                )

            duration = time.time() - start_time
            
            # Métricas
            if METRICS_ENABLED:
                stream_messages_processed_total.labels(
                    status="success",
                    consumer=self.consumer_name,
                    instance_id=getattr(redis_manager, 'instance_id', 'unknown')
                ).inc()
                stream_processing_duration_seconds.labels(
                    consumer=self.consumer_name,
                    instance_id=getattr(redis_manager, 'instance_id', 'unknown')
                ).observe(duration)

            logger.info(
                f"[StreamConsumer] Mensagem processada com sucesso: {message_id} "
                f"(duration={duration:.2f}s)"
            )
            return True

        except Exception as e:
            duration = time.time() - start_time
            
            # Métricas
            if METRICS_ENABLED:
                stream_messages_processed_total.labels(
                    status="error",
                    consumer=self.consumer_name,
                    instance_id=getattr(redis_manager, 'instance_id', 'unknown')
                ).inc()
                stream_processing_duration_seconds.labels(
                    consumer=self.consumer_name,
                    instance_id=getattr(redis_manager, 'instance_id', 'unknown')
                ).observe(duration)

            logger.error(
                f"[StreamConsumer] Erro ao processar mensagem {message_id}: {e}",
                exc_info=True,
            )
            return False

    async def _move_to_dlq(self, message_id: str, data: Dict[str, Any], error: str, retry_count: int = 3):
        """
        Move mensagem para Dead Letter Queue após múltiplas falhas.
        
        Args:
            message_id: ID da mensagem no stream original
            data: Dados da mensagem
            error: Mensagem de erro
            retry_count: Número de tentativas antes de ir para DLQ
        """
        try:
            dlq_data = {
                "original_stream": STREAM_NAME,
                "original_message_id": message_id,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error": error,
                "message_data": json.dumps(data),
                "consumer": self.consumer_name,
                "retry_count": str(retry_count),
            }
            await self.redis_client.xadd(DLQ_STREAM_NAME, dlq_data, maxlen=10000)
            
            # Métricas
            if METRICS_ENABLED:
                stream_messages_dlq_total.labels(
                    instance_id=getattr(redis_manager, 'instance_id', 'unknown')
                ).inc()
            
            # Enviar alerta (se DLQ alerter estiver disponível)
            try:
                from app.services.dlq_alerter import dlq_alerter
                if dlq_alerter:
                    await dlq_alerter.send_alert(
                        message_id=message_id,
                        error=error,
                        message_data=data,
                        retry_count=retry_count,
                    )
            except Exception as e:
                logger.debug(f"[StreamConsumer] Erro ao enviar alerta DLQ: {e}")
            
            logger.warning(
                f"[StreamConsumer] Mensagem movida para DLQ: {message_id} "
                f"erro={error} retry_count={retry_count}",
                extra={
                    "message_id": message_id,
                    "error": error,
                    "retry_count": retry_count,
                    "dlq": True,
                }
            )
        except Exception as e:
            logger.error(f"[StreamConsumer] Erro ao mover para DLQ: {e}")

    async def _update_lag_metrics(self):
        """Atualiza métricas de lag do stream."""
        if not METRICS_ENABLED:
            return
        
        try:
            # Obter informações do consumer group
            group_info = await self.redis_client.xinfo_groups(STREAM_NAME)
            for group in group_info:
                if group.get("name", b"").decode() == CONSUMER_GROUP:
                    pending = group.get("pending", 0)
                    stream_lag.labels(
                        stream=STREAM_NAME,
                        consumer_group=CONSUMER_GROUP,
                        instance_id=getattr(redis_manager, 'instance_id', 'unknown')
                    ).set(pending)
                    break
        except Exception as e:
            logger.debug(f"[StreamConsumer] Erro ao atualizar lag metrics: {e}")

    async def consume(self):
        """
        Loop principal de consumo de mensagens.
        
        Usa XREADGROUP para ler mensagens pendentes e novas do consumer group.
        """
        self.running = True
        logger.info(
            f"[StreamConsumer] Iniciando consumer: {self.consumer_name} "
            f"group={CONSUMER_GROUP} stream={STREAM_NAME}"
        )
        
        last_lag_update = 0

        while self.running:
            try:
                # Atualizar métricas de lag a cada 30 segundos
                current_time = time.time()
                if current_time - last_lag_update > 30:
                    await self._update_lag_metrics()
                    last_lag_update = current_time
                
                # Primeiro: processar mensagens pendentes (PENDING) deste consumer
                # Isso garante retry de mensagens que falharam anteriormente
                try:
                    logger.debug(
                        f"[CONSUMER_READ_START] consumer={self.consumer_name} type=pending block_ms=0",
                        extra={
                            "consumer": self.consumer_name,
                            "read_type": "pending",
                            "block_ms": 0,
                            "step": "consumer_read_start"
                        }
                    )
                    pending_events = await self.redis_client.xreadgroup(
                        groupname=CONSUMER_GROUP,
                        consumername=self.consumer_name,
                        streams={STREAM_NAME: "0"},  # "0" = mensagens pendentes
                        count=BATCH_SIZE,
                        block=0,  # Não bloquear para pending
                    )
                    if pending_events:
                        pending_count = len(pending_events[0][1])
                        logger.info(
                            f"[CONSUMER_PENDING_RECEIVED] consumer={self.consumer_name} count={pending_count}",
                            extra={
                                "consumer": self.consumer_name,
                                "pending_count": pending_count,
                                "step": "consumer_pending_received"
                            }
                        )
                        for stream, messages in pending_events:
                            await self._process_batch(stream, messages)
                except Exception as e:
                    # Não há mensagens pendentes ou erro - continuar
                    logger.debug(
                        f"[CONSUMER_NO_PENDING] consumer={self.consumer_name} error={e}",
                        extra={
                            "consumer": self.consumer_name,
                            "step": "consumer_no_pending"
                        }
                    )

                # Depois: ler mensagens novas do stream
                streams = {STREAM_NAME: ">"}  # ">" = apenas mensagens novas não entregues

                logger.debug(
                    f"[CONSUMER_READ_START] consumer={self.consumer_name} type=new block_ms={BLOCK_TIME}",
                    extra={
                        "consumer": self.consumer_name,
                        "read_type": "new",
                        "block_ms": BLOCK_TIME,
                        "step": "consumer_read_start"
                    }
                )

                events = await self.redis_client.xreadgroup(
                    groupname=CONSUMER_GROUP,
                    consumername=self.consumer_name,
                    streams=streams,
                    count=BATCH_SIZE,
                    block=BLOCK_TIME,
                )

                if not events:
                    # Timeout - continuar loop
                    continue

                new_count = len(events[0][1]) if events else 0
                logger.info(
                    f"[CONSUMER_NEW_RECEIVED] consumer={self.consumer_name} count={new_count}",
                    extra={
                        "consumer": self.consumer_name,
                        "new_count": new_count,
                        "step": "consumer_new_received"
                    }
                )

                # Processar batch de mensagens novas
                for stream, messages in events:
                    await self._process_batch(stream, messages)

            except redis.ConnectionError as e:
                logger.error(f"[StreamConsumer] Conexão Redis perdida: {e}")
                await asyncio.sleep(5)
                await self.connect()

            except asyncio.CancelledError:
                logger.info(f"[StreamConsumer] Consumer cancelado: {self.consumer_name}")
                break

            except Exception as e:
                logger.error(f"[StreamConsumer] Erro no consumer loop: {e}", exc_info=True)
                await asyncio.sleep(1)

        logger.info(f"[StreamConsumer] Consumer parado: {self.consumer_name}")

    async def _process_batch(self, stream, messages):
        """Processa um batch de mensagens."""
        stream_name = stream.decode() if isinstance(stream, bytes) else stream

        for event_id, event_data in messages:
            event_id_str = (
                event_id.decode() if isinstance(event_id, bytes) else event_id
            )
            
            # Gerar trace_id se não existir nos dados
            trace_id = None
            phone = None
            msg_id = None
            
            # Deserializar dados
            try:
                # Redis retorna bytes, converter para dict
                data = {}
                for key, value in event_data.items():
                    key_str = key.decode() if isinstance(key, bytes) else key
                    value_str = (
                        value.decode() if isinstance(value, bytes) else value
                    )
                    
                    # Tentar parse JSON se for string JSON
                    if isinstance(value_str, str) and (
                        value_str.startswith("{") or value_str.startswith("[")
                    ):
                        try:
                            data[key_str] = json.loads(value_str)
                        except (json.JSONDecodeError, TypeError):
                            data[key_str] = value_str
                    else:
                        data[key_str] = value_str

                # Extrair phone, message_id e trace_id para contexto
                # Inicializar variáveis com valores padrão para evitar NameError
                trace_id = None
                phone = ""
                msg_id = ""
                
                try:
                    # Primeiro tentar obter trace_id dos dados do stream
                    trace_id = data.get("trace_id")
                    
                    message_data_raw = data.get("message", {})
                    if isinstance(message_data_raw, str):
                        message_data = json.loads(message_data_raw)
                    else:
                        message_data = message_data_raw
                    key_data = message_data.get("key", {})
                    phone = key_data.get("remoteJid", "").replace("@c.us", "").replace("@lid", "")
                    msg_id = key_data.get("id", "")
                    
                    # Se trace_id não veio do stream, gerar novo
                    if not trace_id:
                        trace_id = f"trace-{msg_id[:8]}" if msg_id else f"trace-{event_id_str[:8]}"
                        logger.warning(
                            f"[TRACE_ID_MISSING] stream_id={event_id_str} message_id={msg_id} "
                            f"generated_new_trace_id={trace_id}",
                            extra={
                                "stream_id": event_id_str,
                                "message_id": msg_id,
                                "generated_trace_id": trace_id,
                                "step": "trace_id_missing"
                            }
                        )
                except Exception as e:
                    logger.error(
                        f"[EXTRACT_CONTEXT_ERROR] stream_id={event_id_str} error={e}",
                        exc_info=True,
                        extra={
                            "stream_id": event_id_str,
                            "step": "extract_context_error"
                        }
                    )
                    # Garantir que trace_id tenha um valor mesmo em caso de erro
                    if not trace_id:
                        trace_id = f"trace-{event_id_str[:8]}" if event_id_str else "trace-unknown"
                    trace_id = f"trace-{event_id_str[:8]}"
                    phone = None
                    msg_id = None
                
                logger.info(
                    f"[CONSUMER_MESSAGE_RECEIVED] trace_id={trace_id} stream_id={event_id_str} "
                    f"consumer={self.consumer_name} phone={phone} message_id={msg_id}",
                    extra={
                        "trace_id": trace_id,
                        "stream_id": event_id_str,
                        "consumer": self.consumer_name,
                        "phone": phone,
                        "message_id": msg_id,
                        "step": "consumer_message_received"
                    }
                )
                
                # Definir contexto de mensagem
                with MessageContextManager(message_id=msg_id, phone=phone, trace_id=trace_id):
                    # Processar mensagem
                    success = await self.process_message(event_id_str, data)

                    if success:
                        # Confirmar processamento (XACK)
                        logger.info(
                            f"[XACK_BEFORE] trace_id={trace_id} stream_id={event_id_str} "
                            f"consumer={self.consumer_name} success=True",
                            extra={
                                "trace_id": trace_id,
                                "stream_id": event_id_str,
                                "consumer": self.consumer_name,
                                "success": True,
                                "step": "xack_before"
                            }
                        )
                        await self.redis_client.xack(
                            STREAM_NAME, CONSUMER_GROUP, event_id_str
                        )
                        logger.debug(
                            f"[XACK_COMPLETE] trace_id={trace_id} stream_id={event_id_str} "
                            f"consumer={self.consumer_name}",
                            extra={
                                "trace_id": trace_id,
                                "stream_id": event_id_str,
                                "consumer": self.consumer_name,
                                "step": "xack_complete"
                            }
                        )
                    else:
                        # Processamento falhou - verificar tentativas
                        # Contar tentativas via XPENDING
                        try:
                            pending_info = await self.redis_client.xpending_range(
                                STREAM_NAME,
                                CONSUMER_GROUP,
                                min="-",
                                max="+",
                                count=1000,
                            )
                            
                            # Encontrar esta mensagem no pending
                            retry_count = 1  # Esta é a primeira tentativa
                            for pending in pending_info:
                                pending_id = (
                                    pending["message_id"].decode()
                                    if isinstance(pending["message_id"], bytes)
                                    else pending["message_id"]
                                )
                                if pending_id == event_id_str:
                                    retry_count = pending.get("times_delivered", 1) + 1
                                    break

                            if retry_count >= MAX_RETRIES:
                                # Mover para DLQ
                                await self._move_to_dlq(
                                    event_id_str,
                                    data,
                                    f"Max retries exceeded ({retry_count})",
                                    retry_count=retry_count,
                                )
                                # Remover do stream original (XACK para confirmar que "processamos")
                                await self.redis_client.xack(
                                    STREAM_NAME, CONSUMER_GROUP, event_id_str
                                )
                                logger.error(
                                    f"[DLQ_MOVED] trace_id={trace_id} stream_id={event_id_str} "
                                    f"retry_count={retry_count}",
                                    extra={
                                        "trace_id": trace_id,
                                        "stream_id": event_id_str,
                                        "retry_count": retry_count,
                                        "step": "dlq_moved"
                                    }
                                )
                            else:
                                # Métricas de retry
                                if METRICS_ENABLED:
                                    stream_retry_count.labels(
                                        consumer=self.consumer_name,
                                        instance_id=getattr(redis_manager, 'instance_id', 'unknown')
                                    ).observe(retry_count)
                                
                                # Deixar pendente para retry automático
                                # Redis vai redeliver após PEL timeout (default 1min)
                                logger.warning(
                                    f"[RETRY_PENDING] trace_id={trace_id} stream_id={event_id_str} "
                                    f"retry_count={retry_count}/{MAX_RETRIES} - será retentada",
                                    extra={
                                        "trace_id": trace_id,
                                        "stream_id": event_id_str,
                                        "retry_count": retry_count,
                                        "step": "retry_pending"
                                    }
                                )
                                # Não fazer XACK - deixar pendente para retry
                        except Exception as e:
                            logger.error(
                                f"[RETRY_CHECK_ERROR] trace_id={trace_id} stream_id={event_id_str} "
                                f"consumer={self.consumer_name} error={e}",
                                exc_info=True,
                                extra={
                                    "trace_id": trace_id,
                                    "stream_id": event_id_str,
                                    "consumer": self.consumer_name,
                                    "step": "retry_check_error"
                                }
                            )
                            # ❌ NÃO fazer XACK - deixar mensagem pendente para retry manual ou DLQ
                            # Se XPENDING falhou, não sabemos quantas tentativas já foram feitas
                            # É mais seguro deixar pendente do que perder a mensagem
                            logger.warning(
                                f"[RETRY_CHECK_FAILED] trace_id={trace_id} stream_id={event_id_str} "
                                f"consumer={self.consumer_name} message left in PENDING for manual inspection",
                                extra={
                                    "trace_id": trace_id,
                                    "stream_id": event_id_str,
                                    "consumer": self.consumer_name,
                                    "step": "retry_check_failed"
                                }
                            )
                            # Não fazer XACK - mensagem ficará pendente até timeout ou retry manual

            except Exception as e:
                logger.error(
                    f"[CONSUMER_DESERIALIZE_ERROR] stream_id={event_id_str} consumer={self.consumer_name} error={e}",
                    exc_info=True,
                    extra={
                        "stream_id": event_id_str,
                        "consumer": self.consumer_name,
                        "step": "consumer_deserialize_error"
                    }
                )
                # ❌ NÃO fazer XACK - deixar mensagem pendente para inspeção manual
                # Se deserialização falhou, mensagem está corrompida
                # Melhor deixar pendente do que perder
                logger.warning(
                    f"[DESERIALIZE_FAILED] stream_id={event_id_str} consumer={self.consumer_name} "
                    f"message left in PENDING - corrupted data",
                    extra={
                        "stream_id": event_id_str,
                        "consumer": self.consumer_name,
                        "step": "deserialize_failed"
                    }
                )

            except redis.ConnectionError as e:
                logger.error(f"[StreamConsumer] Conexão Redis perdida: {e}")
                await asyncio.sleep(5)
                await self.connect()

            except asyncio.CancelledError:
                logger.info(f"[StreamConsumer] Consumer cancelado: {self.consumer_name}")
                break

            except Exception as e:
                logger.error(f"[StreamConsumer] Erro no consumer loop: {e}", exc_info=True)
                await asyncio.sleep(1)

        logger.info(f"[StreamConsumer] Consumer parado: {self.consumer_name}")

    async def start(self):
        """Inicia o consumer em background."""
        if self.running:
            logger.warning("[StreamConsumer] Consumer já está rodando")
            return

        await self.connect()
        self._task = asyncio.create_task(self.consume())
        
        # Métricas
        if METRICS_ENABLED:
            stream_consumer_running.labels(
                consumer=self.consumer_name,
                instance_id=getattr(redis_manager, 'instance_id', 'unknown')
            ).set(1)
        
        logger.info(f"[StreamConsumer] Consumer iniciado: {self.consumer_name}")

    async def stop(self):
        """Para o consumer."""
        self.running = False
        
        # Métricas
        if METRICS_ENABLED:
            stream_consumer_running.labels(
                consumer=self.consumer_name,
                instance_id=getattr(redis_manager, 'instance_id', 'unknown')
            ).set(0)
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.disconnect()
        logger.info(f"[StreamConsumer] Consumer parado: {self.consumer_name}")


# Instância global (será inicializada no main.py)
message_stream_consumer: Optional[MessageStreamConsumer] = None

# Exportar para uso em outros módulos
__all__ = ["MessageStreamConsumer", "message_stream_consumer"]
