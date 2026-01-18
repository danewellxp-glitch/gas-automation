"""
Métricas Prometheus para o backend.

Expõe métricas de:
- Requisições HTTP
- Latência
- Pedidos
- Pagamentos
- Entregas
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)


# ==================== Métricas de Requisições ====================

# Contador de requisições HTTP
http_requests_total = Counter(
    "http_requests_total",
    "Total de requisições HTTP",
    ["method", "endpoint", "status"],
)

# Histograma de latência das requisições
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Duração das requisições HTTP em segundos",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Requisições em andamento
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Número de requisições HTTP em andamento",
    ["method"],
)


# ==================== Métricas de Negócio ====================

# Pedidos
orders_total = Counter(
    "orders_total",
    "Total de pedidos criados",
    ["status", "payment_method"],
)

orders_current = Gauge(
    "orders_current",
    "Pedidos por status",
    ["status"],
)

# Pagamentos
payments_total = Counter(
    "payments_total",
    "Total de pagamentos processados",
    ["method", "status"],
)

payment_amount_total = Counter(
    "payment_amount_total",
    "Valor total de pagamentos",
    ["method"],
)

# Entregas
deliveries_total = Counter(
    "deliveries_total",
    "Total de entregas",
    ["status"],
)

delivery_duration_seconds = Histogram(
    "delivery_duration_seconds",
    "Tempo de entrega em segundos",
    buckets=[300, 600, 1200, 1800, 2400, 3000, 3600],  # 5min a 1h
)

# WhatsApp
whatsapp_messages_total = Counter(
    "whatsapp_messages_total",
    "Total de mensagens WhatsApp",
    ["direction", "type"],  # direction: in/out, type: text/image/button
)

# IA/Ollama
ai_requests_total = Counter(
    "ai_requests_total",
    "Total de requisições ao Ollama",
    ["model", "status"],
)

ai_request_duration_seconds = Histogram(
    "ai_request_duration_seconds",
    "Tempo de resposta do Ollama",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Asaas
asaas_requests_total = Counter(
    "asaas_requests_total",
    "Total de requisições à API Asaas",
    ["endpoint", "status"],
)

# ==================== Info da aplicação ====================

app_info = Info(
    "gas_automation_app",
    "Informações da aplicação Gas Automation",
)
app_info.info({
    "version": "1.0.0",
    "environment": "development",
})


# ==================== Middleware de Métricas ====================

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware para coletar métricas de requisições HTTP."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        path = request.url.path

        # Simplificar path para evitar cardinalidade alta
        endpoint = self._normalize_path(path)

        # Incrementar requisições em andamento
        http_requests_in_progress.labels(method=method).inc()

        # Medir tempo de resposta
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            # Calcular duração
            duration = time.perf_counter() - start_time

            # Registrar métricas
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status,
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            # Decrementar requisições em andamento
            http_requests_in_progress.labels(method=method).dec()

        return response

    def _normalize_path(self, path: str) -> str:
        """
        Normaliza path para evitar cardinalidade alta.

        Exemplo: /api/orders/123 -> /api/orders/{id}
        """
        parts = path.split("/")
        normalized = []

        for part in parts:
            # Detectar UUIDs ou IDs numéricos
            if self._is_id(part):
                normalized.append("{id}")
            else:
                normalized.append(part)

        return "/".join(normalized)

    def _is_id(self, part: str) -> bool:
        """Verifica se parte do path parece ser um ID."""
        if not part:
            return False

        # UUID
        if len(part) == 36 and part.count("-") == 4:
            return True

        # Numérico
        if part.isdigit():
            return True

        # UUID sem hífens
        if len(part) == 32 and all(c in "0123456789abcdef" for c in part.lower()):
            return True

        return False


# ==================== Endpoint de Métricas ====================

async def metrics_endpoint():
    """Endpoint que expõe métricas para o Prometheus."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


# ==================== Funções de Registro ====================

def record_order_created(status: str, payment_method: str):
    """Registra criação de pedido."""
    orders_total.labels(status=status, payment_method=payment_method).inc()


def record_payment_processed(method: str, status: str, amount: float):
    """Registra processamento de pagamento."""
    payments_total.labels(method=method, status=status).inc()
    if status == "confirmed":
        payment_amount_total.labels(method=method).inc(amount)


def record_delivery_completed(duration_seconds: float):
    """Registra entrega concluída."""
    deliveries_total.labels(status="completed").inc()
    delivery_duration_seconds.observe(duration_seconds)


def record_whatsapp_message(direction: str, msg_type: str = "text"):
    """Registra mensagem WhatsApp."""
    whatsapp_messages_total.labels(direction=direction, type=msg_type).inc()


def record_ai_request(model: str, status: str, duration: float):
    """Registra requisição ao Ollama."""
    ai_requests_total.labels(model=model, status=status).inc()
    ai_request_duration_seconds.observe(duration)


def record_asaas_request(endpoint: str, status: str):
    """Registra requisição à API Asaas."""
    asaas_requests_total.labels(endpoint=endpoint, status=status).inc()


def update_orders_gauge(pending: int, paid: int, delivered: int, cancelled: int):
    """Atualiza gauge de pedidos por status."""
    orders_current.labels(status="pending").set(pending)
    orders_current.labels(status="paid").set(paid)
    orders_current.labels(status="delivered").set(delivered)
    orders_current.labels(status="cancelled").set(cancelled)
