"""
Cliente FCM (Firebase Cloud Messaging) para push notifications.

Usa Firebase Admin SDK com FCM V1 API.
Autenticação via service account JSON.
"""

import logging
from typing import Optional

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_initialized = False


def _init_firebase():
    """Inicializa Firebase Admin SDK se ainda não foi."""
    global _initialized
    if _initialized:
        return True

    import os
    cred_path = os.environ.get("FIREBASE_CREDENTIALS", "/app/firebase-credentials.json")

    if not os.path.exists(cred_path):
        logger.warning(f"Firebase credentials não encontrado em {cred_path}. Push desabilitado.")
        return False

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("Firebase Admin SDK inicializado com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar Firebase: {e}")
        return False


async def send_push_notification(
    push_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> bool:
    """
    Envia push notification via FCM V1 API.

    Args:
        push_token: FCM device token do destinatário
        title: Título da notificação
        body: Corpo da mensagem
        data: Dados extras (ex: delivery_id para navegação)

    Returns:
        True se enviou com sucesso
    """
    if not _init_firebase():
        return False

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                sound="default",
                click_action="FCM_PLUGIN_ACTIVITY",
            ),
        ),
        data=data or {},
        token=push_token,
    )

    try:
        response = messaging.send(message)
        logger.info(f"Push enviado: {response}")
        return True
    except messaging.UnregisteredError:
        logger.warning(f"Token inválido/expirado: {push_token[:20]}...")
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
