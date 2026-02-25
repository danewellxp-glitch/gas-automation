"""
Integração com Datadog para métricas e traces.

Envia métricas customizadas e traces para Datadog APM.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Datadog SDK
try:
    from datadog import initialize, api, statsd
    from ddtrace import patch, tracer
    DD_ENABLED = True
except ImportError:
    DD_ENABLED = False
    logger.warning("Datadog SDK não instalado. Instale com: pip install datadog ddtrace")


class DatadogIntegration:
    """Integração com Datadog para métricas e APM."""

    def __init__(self):
        self.enabled = False
        self.statsd_client = None
        self.tracer = None

    def initialize(
        self,
        api_key: Optional[str] = None,
        app_key: Optional[str] = None,
        host: str = "localhost",
        port: int = 8125,
        env: str = "development",
        service: str = "gas-automation",
        version: str = "1.0.0",
    ):
        """
        Inicializa integração com Datadog.
        
        Args:
            api_key: Datadog API key
            app_key: Datadog App key (opcional)
            host: StatsD host
            port: StatsD port
            env: Ambiente (development, staging, production)
            service: Nome do serviço
            version: Versão do serviço
        """
        if not DD_ENABLED:
            logger.warning("Datadog SDK não disponível")
            return False

        try:
            # Inicializar API client (para eventos/custom metrics)
            if api_key:
                initialize(
                    api_key=api_key,
                    app_key=app_key,
                )

            # Inicializar StatsD client (para métricas customizadas)
            self.statsd_client = statsd
            statsd.host = host
            statsd.port = port
            statsd.namespace = f"{service}."

            # Configurar tracer (APM)
            tracer.configure(
                hostname=host,
                port=8126,  # APM agent port
                env=env,
                service=service,
                version=version,
            )

            # Patch de bibliotecas comuns
            patch(httpx=True)
            patch(redis=True)
            patch(sqlalchemy=True)
            patch(fastapi=True)

            self.enabled = True
            logger.info(f"Datadog integração inicializada: service={service} env={env}")
            return True

        except Exception as e:
            logger.error(f"Erro ao inicializar Datadog: {e}")
            return False

    def increment(
        self,
        metric: str,
        value: float = 1,
        tags: Optional[list] = None,
    ):
        """Incrementa métrica."""
        if not self.enabled or not self.statsd_client:
            return
        
        try:
            self.statsd_client.increment(
                metric,
                value=value,
                tags=tags or [],
            )
        except Exception as e:
            logger.debug(f"Erro ao enviar métrica Datadog: {e}")

    def gauge(
        self,
        metric: str,
        value: float,
        tags: Optional[list] = None,
    ):
        """Define gauge."""
        if not self.enabled or not self.statsd_client:
            return
        
        try:
            self.statsd_client.gauge(
                metric,
                value=value,
                tags=tags or [],
            )
        except Exception as e:
            logger.debug(f"Erro ao enviar gauge Datadog: {e}")

    def histogram(
        self,
        metric: str,
        value: float,
        tags: Optional[list] = None,
    ):
        """Envia histogram."""
        if not self.enabled or not self.statsd_client:
            return
        
        try:
            self.statsd_client.histogram(
                metric,
                value=value,
                tags=tags or [],
            )
        except Exception as e:
            logger.debug(f"Erro ao enviar histogram Datadog: {e}")

    def event(
        self,
        title: str,
        text: str,
        alert_type: str = "info",
        tags: Optional[list] = None,
        aggregation_key: Optional[str] = None,
    ):
        """Envia evento para Datadog."""
        if not self.enabled:
            return
        
        try:
            api.Event.create(
                title=title,
                text=text,
                alert_type=alert_type,
                tags=tags or [],
                aggregation_key=aggregation_key,
            )
        except Exception as e:
            logger.debug(f"Erro ao enviar evento Datadog: {e}")

    def trace(self, service: str, resource: str, operation: str = "web.request"):
        """
        Decorator para criar traces.
        
        Usage:
            @datadog_integration.trace("gas-automation", "process_message")
            async def process_message(...):
                ...
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                
                with tracer.trace(operation, service=service, resource=resource):
                    return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                with tracer.trace(operation, service=service, resource=resource):
                    return func(*args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator


# Instância global
datadog_integration = DatadogIntegration()
