"""
Modelos SQLAlchemy do sistema.
Exporta todos os modelos para facilitar importação.
"""

from app.models.auth_models import User, Conversation, Message, AuditLog, BotInteraction, BotContext
from app.models.base import Base, BaseModel, TimestampMixin, UUIDMixin
from app.models.carga import CargaVeiculo, CargaItem, CargaStatus
from app.models.customer import Customer
from app.models.delivery import Delivery, DeliveryStatus
from app.models.driver import Driver, DriverStatus
from app.models.driver_time_log import DriverTimeLog
from app.models.event_log import ActorTypes, EventLog, EventTypes
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod, TipoOperacao
from app.models.payment import Payment, PaymentMethod as PaymentMethodType, PaymentStatus
from app.models.product import Product
from app.models.tipo_preco import TipoPreco, ProdutoPreco
from app.models.vasilhame import Vasilhame, ClienteVasilhame, MovimentacaoVasilhame

__all__ = [
    # Auth Models
    "User",
    "Conversation",
    "Message",
    "AuditLog",
    "BotInteraction",
    "BotContext",
    # Base
    "Base",
    "BaseModel",
    "TimestampMixin",
    "UUIDMixin",
    # Carga
    "CargaVeiculo",
    "CargaItem",
    "CargaStatus",
    # Customer
    "Customer",
    # Product
    "Product",
    # Tipo Preço
    "TipoPreco",
    "ProdutoPreco",
    # Order
    "Order",
    "OrderItem",
    "OrderStatus",
    "PaymentMethod",
    "TipoOperacao",
    # Payment
    "Payment",
    "PaymentMethodType",
    "PaymentStatus",
    # Delivery
    "Delivery",
    "DeliveryStatus",
    # Driver
    "Driver",
    "DriverStatus",
    "DriverTimeLog",
    # EventLog
    "EventLog",
    "EventTypes",
    "ActorTypes",
    # Vasilhame
    "Vasilhame",
    "ClienteVasilhame",
    "MovimentacaoVasilhame",
]
