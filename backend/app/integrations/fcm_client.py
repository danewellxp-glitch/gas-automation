"""
Cliente FCM (Firebase Cloud Messaging) para push notifications.

Usa a FCM Legacy HTTP API para enviar notificações.
A server key é obtida no Firebase Console > Project Settings > Cloud Messaging.
"""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FCM_URL = "https://fcm.googleapis.com/fcm/send"


async def send_push_notification(
    push_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> bool:
    """
    Envia push notification via FCM.

    Args:
        push_token: FCM device token do destinatário
        title: Título da notificação
        body: Corpo da mensagem
        data: Dados extras (ex: delivery_id para navegação)

    Returns:
        True se enviou com sucesso
    """
    server_key = getattr(settings, 'fcm_server_key', None)
    if not server_key:
        logger.warning("FCM server_key não configurada. Push não enviado.")
        return False

    payload = {
        "to": push_token,
        "notification": {
            "title": title,
            "body": body,
            "sound": "default",
            "click_action": "FCM_PLUGIN_ACTIVITY",
        },
    }

    if data:
        payload["data"] = data

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                FCM_URL,
                json=payload,
                headers={
                    "Authorization": f"key={server_key}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )

        if response.status_code == 200:
            result = response.json()
            if result.get("success", 0) > 0:
                logger.info(f"Push enviado com sucesso para token {push_token[:20]}...")
                return True
            else:
                logger.warning(f"FCM retornou falha: {result}")
                return False
        else:
            logger.error(f"FCM HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Erro ao enviar push: {e}")
        return False


async def notify_driver_new_delivery(
    push_token: str,
    delivery_id: str,
    bairro: str,
    order_number: str,
) -> bool:
    """
    Notifica motorista de nova entrega atribuída.
    """
    return await send_push_notification(
        push_token=push_token,
        title="Nova entrega!",
        body=f"Pedido #{order_number} - {bairro}",
        data={
            "delivery_id": delivery_id,
            "type": "new_delivery",
        },
    )
