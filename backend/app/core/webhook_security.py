"""
Módulo de segurança para validação de webhooks.

Implementa validação HMAC-SHA256 para webhooks WAHA e Asaas,
garantindo que requisições vêm de fontes autorizadas.
"""

import hashlib
import hmac
from typing import Optional

from fastapi import HTTPException, Request

from app.config import settings
from app.core.secure_logging import get_secure_logger

logger = get_secure_logger(__name__)


async def verify_waha_signature(request: Request) -> bool:
    """
    Verifica assinatura HMAC-SHA256 do webhook WAHA.

    A validação só é ativada quando WAHA_WEBHOOK_SECRET está configurado.
    Em desenvolvimento (sem secret), permite todas as requisições.

    Args:
        request: Request FastAPI contendo o webhook

    Returns:
        True se assinatura válida ou se validação está desabilitada

    Raises:
        HTTPException 401 se assinatura ausente ou inválida
    """
    # Obter secret configurado
    secret = getattr(settings, 'waha_webhook_secret', None)

    # Se não há secret configurado, permitir (desenvolvimento)
    if not secret:
        logger.debug("WAHA webhook: validação de signature desabilitada (sem secret)")
        return True

    # Obter signature do header
    signature = request.headers.get('X-WAHA-Signature')
    if not signature:
        logger.warning("WAHA webhook: requisição sem header X-WAHA-Signature")
        raise HTTPException(
            status_code=401,
            detail="Missing webhook signature"
        )

    # Calcular HMAC do body
    body = await request.body()
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()

    # Comparação time-safe para evitar timing attacks
    if not hmac.compare_digest(signature.lower(), expected_signature.lower()):
        logger.warning("WAHA webhook: assinatura inválida")
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature"
        )

    logger.debug("WAHA webhook: assinatura verificada com sucesso")
    return True


async def verify_asaas_signature(request: Request) -> bool:
    """
    Verifica assinatura do webhook Asaas.

    O Asaas usa um token de webhook que pode ser verificado
    via header ou validação de IP.

    Args:
        request: Request FastAPI contendo o webhook

    Returns:
        True se assinatura válida ou se validação está desabilitada

    Raises:
        HTTPException 401 se assinatura inválida
    """
    # Obter token configurado
    token = getattr(settings, 'asaas_webhook_token', None)

    # Se não há token configurado, permitir (desenvolvimento)
    if not token:
        logger.debug("Asaas webhook: validação de token desabilitada")
        return True

    # Asaas envia token no header asaas-access-token
    received_token = request.headers.get('asaas-access-token')
    if not received_token:
        logger.warning("Asaas webhook: requisição sem header asaas-access-token")
        raise HTTPException(
            status_code=401,
            detail="Missing webhook token"
        )

    # Comparação time-safe
    if not hmac.compare_digest(received_token, token):
        logger.warning("Asaas webhook: token inválido")
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook token"
        )

    logger.debug("Asaas webhook: token verificado com sucesso")
    return True


def generate_webhook_secret(length: int = 32) -> str:
    """
    Gera um secret seguro para uso em webhooks.

    Útil para configuração inicial.

    Args:
        length: Comprimento do secret em bytes (default 32)

    Returns:
        String hexadecimal do secret gerado
    """
    import secrets
    return secrets.token_hex(length)
