"""
Cliente Twilio para envio de SMS.
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Twilio SDK é opcional
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio SDK não instalado")


def get_twilio_client() -> Optional["TwilioClient"]:
    """Retorna cliente Twilio se disponível e configurado."""
    if not TWILIO_AVAILABLE:
        return None

    if not settings.twilio_enabled:
        logger.warning("Twilio não configurado")
        return None

    return TwilioClient(
        settings.twilio_account_sid,
        settings.twilio_auth_token,
    )


async def send_sms(
    phone: str,
    message: str,
) -> Optional[str]:
    """
    Envia SMS via Twilio.

    Args:
        phone: Número de telefone (formato: +5541999999999)
        message: Mensagem a enviar

    Returns:
        SID da mensagem ou None se falhar
    """
    client = get_twilio_client()
    if not client:
        logger.warning(f"SMS não enviado (Twilio desabilitado): {phone}")
        return None

    try:
        # Formatar número se necessário
        if not phone.startswith("+"):
            phone = f"+55{phone}"

        # Enviar SMS
        msg = client.messages.create(
            body=message,
            from_=settings.twilio_phone_number,
            to=phone,
        )

        logger.info(f"SMS enviado: {msg.sid} -> {phone}")
        return msg.sid

    except TwilioRestException as e:
        logger.error(f"Erro Twilio ao enviar SMS: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao enviar SMS: {e}")
        return None


async def send_whatsapp(
    phone: str,
    message: str,
) -> Optional[str]:
    """
    Envia mensagem WhatsApp via Twilio.

    Nota: Requer número Twilio com WhatsApp habilitado.

    Args:
        phone: Número de telefone WhatsApp
        message: Mensagem a enviar

    Returns:
        SID da mensagem ou None
    """
    client = get_twilio_client()
    if not client:
        return None

    try:
        if not phone.startswith("+"):
            phone = f"+55{phone}"

        msg = client.messages.create(
            body=message,
            from_=f"whatsapp:{settings.twilio_phone_number}",
            to=f"whatsapp:{phone}",
        )

        logger.info(f"WhatsApp enviado via Twilio: {msg.sid}")
        return msg.sid

    except Exception as e:
        logger.error(f"Erro ao enviar WhatsApp via Twilio: {e}")
        return None
