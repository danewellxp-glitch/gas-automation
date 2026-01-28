"""
API Routes do sistema.
"""

from app.api import orders, products, webhooks, customers, test_flow, websocket, locations, exports

__all__ = [
    "webhooks",
    "products",
    "orders",
    "customers",
    "test_flow",
    "websocket",
    "locations",
    "exports",
]
