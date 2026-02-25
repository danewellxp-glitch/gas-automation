"""
Utilitário de Logging Estruturado com message_id e trace_id.

Permite correlação de logs através de message_id e trace_id para debugging
e rastreamento de mensagens através de todo o pipeline de processamento.
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any
import json

# Context variables para rastreamento de mensagens
message_id_context: ContextVar[Optional[str]] = ContextVar("message_id", default=None)
trace_id_context: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
phone_context: ContextVar[Optional[str]] = ContextVar("phone", default=None)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Adapter para logging estruturado que adiciona message_id, trace_id e phone
    automaticamente aos logs.
    """

    def process(self, msg, kwargs):
        """
        Adiciona campos estruturados ao log.
        """
        extra = kwargs.setdefault("extra", {})
        
        # Adicionar message_id se disponível no contexto
        msg_id = message_id_context.get()
        if msg_id:
            extra["message_id"] = msg_id
        
        # Adicionar trace_id se disponível no contexto
        trace_id = trace_id_context.get()
        if trace_id:
            extra["trace_id"] = trace_id
        
        # Adicionar phone se disponível no contexto
        phone = phone_context.get()
        if phone:
            extra["phone"] = phone
        
        # Formatar mensagem com campos estruturados
        if extra:
            # Criar string estruturada para logs legíveis
            structured_fields = []
            if "message_id" in extra:
                structured_fields.append(f"msg_id={extra['message_id']}")
            if "trace_id" in extra:
                structured_fields.append(f"trace_id={extra['trace_id']}")
            if "phone" in extra:
                structured_fields.append(f"phone={extra['phone']}")
            
            if structured_fields:
                msg = f"[{' '.join(structured_fields)}] {msg}"
        
        return msg, kwargs


def get_structured_logger(name: str) -> StructuredLoggerAdapter:
    """
    Obtém um logger estruturado.
    
    Args:
        name: Nome do logger (geralmente __name__)
        
    Returns:
        Logger estruturado
    """
    base_logger = logging.getLogger(name)
    return StructuredLoggerAdapter(base_logger, {})


def set_message_context(
    message_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    phone: Optional[str] = None,
) -> None:
    """
    Define o contexto de mensagem para logs estruturados.
    
    Args:
        message_id: ID da mensagem WhatsApp
        trace_id: ID de rastreamento (gerado automaticamente se None)
        phone: Número de telefone do cliente
    """
    if message_id:
        message_id_context.set(message_id)
    
    if trace_id:
        trace_id_context.set(trace_id)
    elif message_id:
        # Gerar trace_id baseado no message_id se não fornecido
        trace_id_context.set(f"trace-{message_id[:8]}")
    
    if phone:
        phone_context.set(phone)


def clear_message_context() -> None:
    """Limpa o contexto de mensagem."""
    message_id_context.set(None)
    trace_id_context.set(None)
    phone_context.set(None)


def get_message_context() -> Dict[str, Optional[str]]:
    """
    Obtém o contexto atual de mensagem.
    
    Returns:
        Dict com message_id, trace_id e phone
    """
    return {
        "message_id": message_id_context.get(),
        "trace_id": trace_id_context.get(),
        "phone": phone_context.get(),
    }


class MessageContextManager:
    """
    Context manager para definir contexto de mensagem temporariamente.
    
    Usage:
        with MessageContextManager(message_id="123", phone="5511999999999"):
            logger.info("Esta mensagem terá message_id e phone no log")
    """

    def __init__(
        self,
        message_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        phone: Optional[str] = None,
    ):
        self.message_id = message_id
        self.trace_id = trace_id or (f"trace-{message_id[:8]}" if message_id else None)
        self.phone = phone
        self.old_message_id = None
        self.old_trace_id = None
        self.old_phone = None

    def __enter__(self):
        self.old_message_id = message_id_context.get()
        self.old_trace_id = trace_id_context.get()
        self.old_phone = phone_context.get()
        
        set_message_context(
            message_id=self.message_id,
            trace_id=self.trace_id,
            phone=self.phone,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        message_id_context.set(self.old_message_id)
        trace_id_context.set(self.old_trace_id)
        phone_context.set(self.old_phone)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    message_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    phone: Optional[str] = None,
    **kwargs
) -> None:
    """
    Loga uma mensagem com contexto estruturado.
    
    Args:
        logger: Logger a usar
        level: Nível de log (logging.INFO, logging.ERROR, etc)
        message: Mensagem a logar
        message_id: ID da mensagem
        trace_id: ID de rastreamento
        phone: Número de telefone
        **kwargs: Campos extras para adicionar ao log
    """
    extra = kwargs.setdefault("extra", {})
    
    if message_id:
        extra["message_id"] = message_id
    if trace_id:
        extra["trace_id"] = trace_id
    if phone:
        extra["phone"] = phone
    
    logger.log(level, message, **kwargs)
