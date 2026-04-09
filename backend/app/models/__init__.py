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
from app.models.promotion import Promotion
from app.models.conversation_snapshot import ConversationSnapshot

# Módulo Financeiro
from app.models.financeiro.account import Account, AccountType
from app.models.financeiro.transaction import Transaction, TransactionType, TransactionCategory
from app.models.financeiro.receivable import Receivable, ReceivableStatus
from app.models.financeiro.payable import Payable, PayableStatus
from app.models.financeiro.cost_center import CostCenter
from app.models.financeiro.cash_flow_entry import CashFlowEntry

# Módulo Estoque
from app.models.estoque.supplier import Supplier
from app.models.estoque.stock_product import StockProduct
from app.models.estoque.stock_movement import StockMovement, MovementType
from app.models.estoque.stock_balance import StockBalance
from app.models.estoque.vehicle_load import VehicleLoad, VehicleLoadStatus
from app.models.estoque.vehicle_load_item import VehicleLoadItem
from app.models.estoque.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.estoque.purchase_order_item import PurchaseOrderItem

# Módulo Financeiro — lucratividade e fiado
from app.models.financeiro.customer_financial import CustomerFinancial
from app.models.financeiro.order_profit import OrderProfit
from app.models.financeiro.fiado_entry import FiadoEntry, FiadoPagamento
from app.models.financeiro.nota_fiscal import NotaFiscal
from app.models.financeiro.pix_conciliation import PixConciliationRun, PixConciliationItem
from app.models.financeiro.vasilhame_estoque import VasilhameEstoque, VasilhameMovimento

# Módulo de Despesas
from app.models.expense import Expense, ExpenseTipo, ExpenseTipoGrupo, Periodicidade

# Acerto de Turno
from app.models.driver_turno import DriverTurno, AcertoItemEntrega, TurnoStatus

# Comodato
from app.models.comodato import Comodato, ComodatoStatus

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
    # Promotion
    "Promotion",
    # Conversation Snapshot
    "ConversationSnapshot",
    # Financeiro
    "Account", "AccountType",
    "Transaction", "TransactionType", "TransactionCategory",
    "Receivable", "ReceivableStatus",
    "Payable", "PayableStatus",
    "CostCenter",
    "CashFlowEntry",
    # Estoque
    "Supplier",
    "StockProduct",
    "StockMovement", "MovementType",
    "StockBalance",
    "VehicleLoad", "VehicleLoadStatus",
    "VehicleLoadItem",
    "PurchaseOrder", "PurchaseOrderStatus",
    "PurchaseOrderItem",
    # Financeiro — lucratividade e fiado
    "CustomerFinancial",
    "OrderProfit",
    "FiadoEntry",
    "FiadoPagamento",
    "NotaFiscal",
    "PixConciliationRun",
    "PixConciliationItem",
    "VasilhameEstoque",
    "VasilhameMovimento",
    # Despesas
    "Expense",
    "ExpenseTipo",
    "ExpenseTipoGrupo",
    "Periodicidade",
    # Acerto de Turno
    "DriverTurno",
    "AcertoItemEntrega",
    "TurnoStatus",
    # Comodato
    "Comodato",
    "ComodatoStatus",
]
