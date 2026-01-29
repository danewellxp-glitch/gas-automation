"""
Event Publisher Service - Publica eventos para Redis Streams.

Integra com notification-service para enviar notificações automáticas.
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import redis.asyncio as redis

from app.config import settings
from app.database import redis_manager

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publica eventos para Redis Streams para consumo pelo notification-service."""
    
    # Streams Redis para diferentes tipos de eventos
    STREAMS = {
        "orders": "orders:events",
        "payments": "payments:events",
        "notifications": "notifications:queue",
    }
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Obtém cliente Redis."""
        if not self._redis:
            self._redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=False,  # Redis Streams precisa de bytes
            )
        return self._redis
    
    async def publish_order_event(
        self,
        event_type: str,
        order_id: str,
        order_number: int,
        customer_id: str,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        status: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publica evento relacionado a pedidos.
        
        Args:
            event_type: Tipo do evento (order.created, order.paid, order.dispatched, etc.)
            order_id: UUID do pedido
            order_number: Número do pedido
            customer_id: UUID do cliente
            customer_phone: Telefone do cliente (para WhatsApp)
            customer_email: Email do cliente
            status: Status atual do pedido
            extra_data: Dados extras
            
        Returns:
            True se publicado com sucesso, False caso contrário
        """
        try:
            r = await self._get_redis()
            
            payload = {
                "order_id": str(order_id),
                "order_number": order_number,
                "customer_id": str(customer_id),
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            if customer_phone:
                payload["customer_phone"] = customer_phone
            if customer_email:
                payload["customer_email"] = customer_email
            if extra_data:
                payload.update(extra_data)
            
            # Publicar no stream Redis
            await r.xadd(
                self.STREAMS["orders"],
                {
                    "type": event_type,
                    "payload": json.dumps(payload, default=str),
                },
                maxlen=10000,  # Manter apenas últimos 10k eventos
            )
            
            logger.info(f"Evento publicado: {event_type} para pedido {order_number}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao publicar evento de pedido: {e}", exc_info=True)
            return False
    
    async def publish_payment_event(
        self,
        event_type: str,
        payment_id: str,
        order_id: str,
        order_number: int,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        amount: Optional[float] = None,
        status: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publica evento relacionado a pagamentos.
        
        Args:
            event_type: Tipo do evento (payment.confirmed, payment.failed, etc.)
            payment_id: UUID do pagamento
            order_id: UUID do pedido
            order_number: Número do pedido
            customer_phone: Telefone do cliente
            customer_email: Email do cliente
            amount: Valor do pagamento
            status: Status do pagamento
            extra_data: Dados extras
            
        Returns:
            True se publicado com sucesso, False caso contrário
        """
        try:
            r = await self._get_redis()
            
            payload = {
                "payment_id": str(payment_id),
                "order_id": str(order_id),
                "order_number": order_number,
                "amount": amount,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            if customer_phone:
                payload["customer_phone"] = customer_phone
            if customer_email:
                payload["customer_email"] = customer_email
            if extra_data:
                payload.update(extra_data)
            
            await r.xadd(
                self.STREAMS["payments"],
                {
                    "type": event_type,
                    "payload": json.dumps(payload, default=str),
                },
                maxlen=10000,
            )
            
            logger.info(f"Evento publicado: {event_type} para pagamento {payment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao publicar evento de pagamento: {e}", exc_info=True)
            return False
    
    async def publish_notification(
        self,
        notification_type: str,
        recipient_phone: Optional[str] = None,
        recipient_email: Optional[str] = None,
        message: Optional[str] = None,
        subject: Optional[str] = None,
        template: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publica notificação direta (SMS/Email).
        
        Args:
            notification_type: Tipo (sms, email, whatsapp)
            recipient_phone: Telefone do destinatário
            recipient_email: Email do destinatário
            message: Mensagem (para SMS/WhatsApp)
            subject: Assunto (para Email)
            template: Template a usar (opcional)
            template_data: Dados para o template
            
        Returns:
            True se publicado com sucesso, False caso contrário
        """
        try:
            r = await self._get_redis()
            
            payload = {
                "type": notification_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            if recipient_phone:
                payload["recipient_phone"] = recipient_phone
            if recipient_email:
                payload["recipient_email"] = recipient_email
            if message:
                payload["message"] = message
            if subject:
                payload["subject"] = subject
            if template:
                payload["template"] = template
            if template_data:
                payload["template_data"] = template_data
            
            await r.xadd(
                self.STREAMS["notifications"],
                {
                    "type": notification_type,
                    "payload": json.dumps(payload, default=str),
                },
                maxlen=10000,
            )
            
            logger.info(f"Notificação publicada: {notification_type}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao publicar notificação: {e}", exc_info=True)
            return False
    
    async def close(self):
        """Fecha conexão Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Instância global
event_publisher = EventPublisher()