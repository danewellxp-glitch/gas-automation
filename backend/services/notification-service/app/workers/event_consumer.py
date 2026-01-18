"""
Consumer de eventos via Redis Streams.

Consome eventos de notificação publicados pelo backend principal.
"""

import asyncio
import json
import logging
from typing import Optional

import redis.asyncio as redis

from app.config import settings
from app.integrations.twilio_client import send_sms
from app.integrations.sendgrid_client import send_email, EmailTemplates

logger = logging.getLogger(__name__)

# Nome do consumer group
CONSUMER_GROUP = "notification-service"
CONSUMER_NAME = "worker-1"

# Streams para consumir
STREAMS = {
    "notifications:queue": "$",
    "orders:events": "$",
    "payments:events": "$",
}


class EventConsumer:
    """Consumer de eventos Redis Streams."""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.running = False

    async def connect(self):
        """Conecta ao Redis."""
        self.redis = redis.from_url(settings.redis_url)
        logger.info(f"Conectado ao Redis: {settings.redis_url}")

        # Criar consumer groups se não existirem
        for stream in STREAMS.keys():
            try:
                await self.redis.xgroup_create(
                    name=stream,
                    groupname=CONSUMER_GROUP,
                    id="0",
                    mkstream=True,
                )
                logger.info(f"Consumer group criado: {stream}/{CONSUMER_GROUP}")
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.warning(f"Erro ao criar consumer group: {e}")

    async def disconnect(self):
        """Desconecta do Redis."""
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def process_event(self, stream: str, event_id: str, data: dict):
        """
        Processa um evento recebido.

        Args:
            stream: Nome do stream de origem
            event_id: ID do evento
            data: Dados do evento
        """
        try:
            event_type = data.get("type", data.get(b"type", b"").decode())
            payload_raw = data.get("payload", data.get(b"payload", b"{}"))

            if isinstance(payload_raw, bytes):
                payload_raw = payload_raw.decode()
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw

            logger.info(f"Processando evento: {stream}/{event_type} - {event_id}")

            # Rotear baseado no tipo de evento
            if event_type == "sms":
                await self._handle_sms(payload)

            elif event_type == "email":
                await self._handle_email(payload)

            elif event_type == "order.created":
                await self._handle_order_created(payload)

            elif event_type == "order.paid":
                await self._handle_order_paid(payload)

            elif event_type == "payment.confirmed":
                await self._handle_payment_confirmed(payload)

            elif event_type == "delivery.started":
                await self._handle_delivery_started(payload)

            elif event_type == "delivery.completed":
                await self._handle_delivery_completed(payload)

            else:
                logger.debug(f"Evento ignorado: {event_type}")

            # Confirmar processamento
            await self.redis.xack(stream, CONSUMER_GROUP, event_id)

        except Exception as e:
            logger.error(f"Erro ao processar evento {event_id}: {e}")

    async def _handle_sms(self, payload: dict):
        """Processa evento de SMS."""
        phone = payload.get("phone")
        message = payload.get("message")

        if phone and message:
            await send_sms(phone, message)

    async def _handle_email(self, payload: dict):
        """Processa evento de email."""
        to_email = payload.get("email")
        subject = payload.get("subject")
        body = payload.get("body")

        if to_email and subject and body:
            await send_email(to_email, subject, body)

    async def _handle_order_created(self, payload: dict):
        """Notifica criação de pedido."""
        customer_email = payload.get("customer_email")
        customer_name = payload.get("customer_name", "Cliente")
        order_number = payload.get("order_number")
        items = payload.get("items", [])
        total = payload.get("total", 0)
        address = payload.get("delivery_address", "")

        if customer_email:
            subject, body_text, body_html = EmailTemplates.order_confirmation(
                customer_name=customer_name,
                order_number=order_number,
                items=items,
                total=total,
                delivery_address=address,
            )
            await send_email(customer_email, subject, body_text, body_html)

    async def _handle_order_paid(self, payload: dict):
        """Notifica pagamento de pedido."""
        await self._handle_payment_confirmed(payload)

    async def _handle_payment_confirmed(self, payload: dict):
        """Notifica confirmação de pagamento."""
        customer_email = payload.get("customer_email")
        customer_phone = payload.get("customer_phone")
        customer_name = payload.get("customer_name", "Cliente")
        order_number = payload.get("order_number")
        amount = payload.get("amount", 0)
        payment_method = payload.get("payment_method", "Pix")

        # Email
        if customer_email:
            subject, body_text, body_html = EmailTemplates.payment_confirmed(
                customer_name=customer_name,
                order_number=order_number,
                amount=amount,
                payment_method=payment_method,
            )
            await send_email(customer_email, subject, body_text, body_html)

        # SMS
        if customer_phone:
            sms_message = (
                f"Gas Automation: Pagamento confirmado! "
                f"Pedido #{order_number} - R${amount:.2f}. "
                f"Estamos preparando sua entrega!"
            )
            await send_sms(customer_phone, sms_message)

    async def _handle_delivery_started(self, payload: dict):
        """Notifica início de entrega."""
        customer_phone = payload.get("customer_phone")
        order_number = payload.get("order_number")
        driver_name = payload.get("driver_name", "Entregador")
        eta_minutes = payload.get("eta_minutes", 40)

        if customer_phone:
            message = (
                f"Gas Automation: Seu pedido #{order_number} saiu para entrega! "
                f"Entregador: {driver_name}. "
                f"Previsão: {eta_minutes} minutos."
            )
            await send_sms(customer_phone, message)

    async def _handle_delivery_completed(self, payload: dict):
        """Notifica entrega concluída."""
        customer_phone = payload.get("customer_phone")
        customer_email = payload.get("customer_email")
        order_number = payload.get("order_number")

        if customer_phone:
            message = (
                f"Gas Automation: Pedido #{order_number} entregue! "
                f"Obrigado pela preferencia. "
                f"Avalie nosso atendimento!"
            )
            await send_sms(customer_phone, message)

    async def consume(self):
        """Loop principal de consumo de eventos."""
        self.running = True

        while self.running:
            try:
                # Ler eventos de todos os streams
                events = await self.redis.xreadgroup(
                    groupname=CONSUMER_GROUP,
                    consumername=CONSUMER_NAME,
                    streams=STREAMS,
                    count=10,
                    block=5000,  # 5 segundos de timeout
                )

                for stream, messages in events:
                    stream_name = stream.decode() if isinstance(stream, bytes) else stream

                    for event_id, data in messages:
                        event_id = event_id.decode() if isinstance(event_id, bytes) else event_id
                        await self.process_event(stream_name, event_id, data)

            except redis.ConnectionError as e:
                logger.error(f"Conexão Redis perdida: {e}")
                await asyncio.sleep(5)
                await self.connect()

            except asyncio.CancelledError:
                logger.info("Consumer cancelado")
                break

            except Exception as e:
                logger.error(f"Erro no consumer: {e}")
                await asyncio.sleep(1)

    def stop(self):
        """Para o consumer."""
        self.running = False


# Instância global
consumer = EventConsumer()


async def start_consumer():
    """Inicia o consumer de eventos."""
    await consumer.connect()
    await consumer.consume()
    await consumer.disconnect()
