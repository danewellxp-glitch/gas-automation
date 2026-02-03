"""
Módulo de logging seguro com sanitização automática de dados sensíveis.

Este módulo fornece funcionalidades para:
- Mascarar API keys, tokens, senhas em mensagens de log
- Mascarar números de cartão de crédito e CVV
- Mascarar CPF/CNPJ
- Controlar exposição de detalhes de exceção em produção
"""

import logging
import re
from typing import Optional

from app.config import settings


# Padrões de dados sensíveis para mascarar
# Cada tupla contém (regex_pattern, replacement)
SENSITIVE_PATTERNS = [
    # API Keys e tokens (formatos comuns)
    (r'(api[_-]?key|apikey|access[_-]?token|bearer|authorization|secret[_-]?key|token)["\']?\s*[:=]\s*["\']?([^\s"\'&,\}]{8,})', r'\1=***REDACTED***'),

    # Senhas
    (r'(password|passwd|pwd|senha)["\']?\s*[:=]\s*["\']?([^\s"\'&,\}]+)', r'\1=***REDACTED***'),

    # Números de cartão de crédito (13-19 dígitos, com ou sem separadores)
    (r'\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{1,4}[\s\-]?\d{0,3})\b', '***CARD-REDACTED***'),

    # CVV/CVC (3-4 dígitos precedidos por cvv/cvc/ccv)
    (r'(cvv|cvc|ccv)["\']?\s*[:=]\s*["\']?(\d{3,4})', r'\1=***'),

    # CPF (com ou sem formatação)
    (r'\b(\d{3}\.?\d{3}\.?\d{3}[-.]?\d{2})\b', '***CPF-REDACTED***'),

    # CNPJ (com ou sem formatação)
    (r'\b(\d{2}\.?\d{3}\.?\d{3}[/.]?\d{4}[-.]?\d{2})\b', '***CNPJ-REDACTED***'),

    # Tokens JWT (formato header.payload.signature)
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '***JWT-REDACTED***'),

    # Chaves Asaas (começam com $ ou ak_)
    (r'(\$aas_[a-zA-Z0-9]+|ak_[a-zA-Z0-9]+)', '***ASAAS-KEY***'),
]


def sanitize_message(message: str) -> str:
    """
    Remove/mascara dados sensíveis de mensagens de log.

    Args:
        message: Mensagem original que pode conter dados sensíveis

    Returns:
        Mensagem com dados sensíveis mascarados

    Examples:
        >>> sanitize_message("api_key=sk-1234567890abcdef")
        'api_key=***REDACTED***'

        >>> sanitize_message("Cartão: 4111-1111-1111-1111")
        'Cartão: ***CARD-REDACTED***'
    """
    if not message:
        return message

    result = str(message)
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def sanitize_exception(exc: Exception) -> str:
    """
    Retorna mensagem de exceção sanitizada.

    Args:
        exc: Exceção a sanitizar

    Returns:
        String da exceção com dados sensíveis mascarados
    """
    return sanitize_message(str(exc))


class SecureLogger:
    """
    Logger que automaticamente sanitiza mensagens antes de registrar.

    Em produção, detalhes de exceção são omitidos para evitar vazamento
    de informações sensíveis em stack traces.

    Usage:
        from app.core.secure_logging import get_secure_logger

        logger = get_secure_logger(__name__)
        logger.error("Falha na API", exc=exception)
    """

    def __init__(self, name: str):
        """
        Inicializa o logger seguro.

        Args:
            name: Nome do logger (normalmente __name__ do módulo)
        """
        self.logger = logging.getLogger(name)
        self._is_production = settings.is_production

    def _should_include_details(self) -> bool:
        """
        Determina se detalhes de exceção devem ser incluídos.
        Em produção, detalhes são omitidos para segurança.
        """
        return not self._is_production

    def error(self, msg: str, exc: Optional[Exception] = None, **kwargs):
        """
        Registra erro com sanitização automática.

        Args:
            msg: Mensagem de erro
            exc: Exceção opcional (detalhes omitidos em produção)
            **kwargs: Argumentos extras para o logger
        """
        # Remover exc_info se estiver em kwargs para controlar manualmente
        kwargs.pop('exc_info', None)

        sanitized_msg = sanitize_message(msg)

        if exc and self._should_include_details():
            self.logger.error(f"{sanitized_msg}: {sanitize_exception(exc)}", **kwargs)
        else:
            self.logger.error(sanitized_msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        """Registra warning com sanitização automática."""
        kwargs.pop('exc_info', None)
        self.logger.warning(sanitize_message(msg), **kwargs)

    def info(self, msg: str, **kwargs):
        """Registra info com sanitização automática."""
        self.logger.info(sanitize_message(msg), **kwargs)

    def debug(self, msg: str, **kwargs):
        """
        Registra debug com sanitização automática.
        Em produção, mensagens debug são suprimidas.
        """
        if self._should_include_details():
            self.logger.debug(sanitize_message(msg), **kwargs)

    def critical(self, msg: str, exc: Optional[Exception] = None, **kwargs):
        """Registra critical com sanitização automática."""
        kwargs.pop('exc_info', None)

        sanitized_msg = sanitize_message(msg)

        if exc and self._should_include_details():
            self.logger.critical(f"{sanitized_msg}: {sanitize_exception(exc)}", **kwargs)
        else:
            self.logger.critical(sanitized_msg, **kwargs)


def get_secure_logger(name: str) -> SecureLogger:
    """
    Factory para criar loggers seguros.

    Args:
        name: Nome do logger (normalmente __name__ do módulo)

    Returns:
        Instância de SecureLogger configurada

    Usage:
        logger = get_secure_logger(__name__)
        logger.info("Operação concluída")
        logger.error("Falha na operação", exc=exception)
    """
    return SecureLogger(name)


# Logger padrão para uso rápido
secure_logger = get_secure_logger("app")
