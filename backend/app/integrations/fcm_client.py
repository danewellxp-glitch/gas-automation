"""
Cliente FCM (Firebase Cloud Messaging) para push notifications.

Usa Firebase Admin SDK com FCM V1 API.
Autenticação via service account JSON.

Import opcional: se firebase-admin não estiver instalado, o módulo carrega
normalmente e as funções de push retornam False (push desabilitado).
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_initialized = False
_firebase_available: Optional[bool] = None


def _check_firebase_available() -> bool:
    """Verifica se firebase-admin está instalado (import opcional)."""
    global _firebase_available
    if _firebase_available is not None:
        return _firebase_available
    try:
        import firebase_admin  # noqa: F401
        _firebase_available = True
        return True
    except ImportError:
        logger.warning(
            "firebase-admin não instalado. Push notifications desabilitadas. "
            "Para habilitar: pip install firebase-admin"
        )
        _firebase_available = False
        return False


def _init_firebase():
    """Inicializa Firebase Admin SDK se ainda não foi."""
    global _initialized
    if _initialized:
        return True

    if not _check_firebase_available():
        return False

    import firebase_admin
    from firebase_admin import credentials
    import glob

    cred_path = os.environ.get("FIREBASE_CREDENTIALS")
    if cred_path:
        if not os.path.exists(cred_path):
            logger.warning(f"FIREBASE_CREDENTIALS aponta para arquivo inexistente: {cred_path}. Push desabilitado.")
            return False
    elif os.path.exists("/app/firebase-credentials.json"):
        cred_path = "/app/firebase-credentials.json"  # Docker
    elif os.path.exists("firebase-credentials.json"):
        cred_path = os.path.abspath("firebase-credentials.json")  # CWD local
    else:
        # Fallback: buscar service account pelo nome padrão (gas-driver-*-firebase-adminsdk-*.json)
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        for base in ["/app", backend_dir]:
            if os.path.isdir(base):
                candidates = glob.glob(os.path.join(base, "gas-driver-*-firebase-adminsdk-*.json"))
                if candidates:
                    cred_path = candidates[0]
                    logger.info(f"Usando credenciais Firebase: {cred_path}")
                    break
        if not cred_path or not os.path.exists(cred_path):
            logger.warning("Firebase credentials não encontrado. Push desabilitado.")
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

    from firebase_admin import messaging

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
