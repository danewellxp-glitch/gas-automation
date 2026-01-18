"""
Integrações externas do sistema.
"""

from app.integrations.asaas import (
    AsaasClient,
    AsaasError,
    asaas_client,
    check_payment_status,
    create_pix_payment,
)
from app.integrations.firebird import (
    FirebirdClient,
    FirebirdError,
    firebird_client,
    get_customer_from_legacy,
    get_products_from_legacy,
    is_firebird_available,
)
from app.integrations.ollama import (
    IntentAnalysis,
    OllamaClient,
    OllamaError,
    analyze_message,
    get_ai_response,
    is_ai_available,
    ollama_client,
)
from app.integrations.waha import (
    WAHAClient,
    send_buttons,
    send_image,
    send_message,
    waha_client,
)

__all__ = [
    # WAHA
    "WAHAClient",
    "waha_client",
    "send_message",
    "send_buttons",
    "send_image",
    # Asaas
    "AsaasClient",
    "AsaasError",
    "asaas_client",
    "create_pix_payment",
    "check_payment_status",
    # Firebird
    "FirebirdClient",
    "FirebirdError",
    "firebird_client",
    "get_products_from_legacy",
    "get_customer_from_legacy",
    "is_firebird_available",
    # Ollama
    "OllamaClient",
    "OllamaError",
    "IntentAnalysis",
    "ollama_client",
    "analyze_message",
    "get_ai_response",
    "is_ai_available",
]
