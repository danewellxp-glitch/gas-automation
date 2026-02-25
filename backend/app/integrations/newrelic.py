"""
Integração com New Relic para APM e métricas.

Envia métricas customizadas e traces para New Relic.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

# New Relic SDK
try:
    import newrelic.agent
    NR_ENABLED = True
except ImportError:
    NR_ENABLED = False
    logger.warning("New Relic SDK não instalado. Instale com: pip install newrelic")


class NewRelicIntegration:
    """Integração com New Relic para APM e métricas."""

    def __init__(self):
        self.enabled = False
        self.agent = None

    def initialize(
        self,
        license_key: Optional[str] = None,
        app_name: str = "Gas Automation",
        environment: str = "development",
        config_file: Optional[str] = None,
    ):
        """
        Inicializa integração com New Relic.
        
        Args:
            license_key: New Relic license key
            app_name: Nome da aplicação
            environment: Ambiente (development, staging, production)
            config_file: Caminho para arquivo de configuração (opcional)
        """
        if not NR_ENABLED:
            logger.warning("New Relic SDK não disponível")
            return False

        try:
            # Configurar via variáveis de ambiente ou arquivo
            if license_key:
                os.environ["NEW_RELIC_LICENSE_KEY"] = license_key
            os.environ["NEW_RELIC_APP_NAME"] = app_name
            os.environ["NEW_RELIC_ENVIRONMENT"] = environment

            # Inicializar agente
            if config_file and os.path.exists(config_file):
                newrelic.agent.initialize(config_file)
            else:
                # Configuração mínima
                newrelic.agent.initialize()

            self.agent = newrelic.agent
            self.enabled = True
            logger.info(f"New Relic integração inicializada: app={app_name} env={environment}")
            return True

        except Exception as e:
            logger.error(f"Erro ao inicializar New Relic: {e}")
            return False

    def record_custom_metric(
        self,
        name: str,
        value: float,
        unit: Optional[str] = None,
    ):
        """Registra métrica customizada."""
        if not self.enabled or not self.agent:
            return
        
        try:
            self.agent.record_custom_metric(name, value)
        except Exception as e:
            logger.debug(f"Erro ao registrar métrica New Relic: {e}")

    def record_custom_event(
        self,
        event_type: str,
        params: Dict[str, Any],
    ):
        """Registra evento customizado."""
        if not self.enabled or not self.agent:
            return
        
        try:
            self.agent.record_custom_event(event_type, params)
        except Exception as e:
            logger.debug(f"Erro ao registrar evento New Relic: {e}")

    def add_custom_attribute(
        self,
        key: str,
        value: Any,
    ):
        """Adiciona atributo customizado ao trace atual."""
        if not self.enabled or not self.agent:
            return
        
        try:
            self.agent.add_custom_attribute(key, value)
        except Exception as e:
            logger.debug(f"Erro ao adicionar atributo New Relic: {e}")

    def notice_error(
        self,
        exception: Exception,
        expected: bool = False,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Registra erro."""
        if not self.enabled or not self.agent:
            return
        
        try:
            self.agent.notice_error(exception, expected=expected, attributes=attributes)
        except Exception as e:
            logger.debug(f"Erro ao registrar erro New Relic: {e}")

    def trace(self, name: Optional[str] = None, group: Optional[str] = None):
        """
        Decorator para criar traces.
        
        Usage:
            @newrelic_integration.trace("process_message", "MessageProcessing")
            async def process_message(...):
                ...
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                trace_name = name or f"{func.__module__}.{func.__name__}"
                with self.agent.FunctionTrace(trace_name, group=group):
                    return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                trace_name = name or f"{func.__module__}.{func.__name__}"
                with self.agent.FunctionTrace(trace_name, group=group):
                    return func(*args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator

    def web_transaction(self, name: Optional[str] = None, group: Optional[str] = None):
        """
        Decorator para criar web transactions.
        
        Usage:
            @newrelic_integration.web_transaction("process_webhook", "Webhooks")
            async def webhook_handler(...):
                ...
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                transaction_name = name or f"{func.__module__}.{func.__name__}"
                with self.agent.WebTransaction(name=transaction_name, group=group):
                    return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                transaction_name = name or f"{func.__module__}.{func.__name__}"
                with self.agent.WebTransaction(name=transaction_name, group=group):
                    return func(*args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper


# Instância global
newrelic_integration = NewRelicIntegration()
