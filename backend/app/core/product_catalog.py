"""
Catálogo de Produtos GLP - Flow Engine 2.0
Configuração centralizada de produtos, operações e pagamentos.

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md - Parte 3
"""

from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict


# ═══════════════════════════════════════════════════════════════════════
# PRODUTOS
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Product:
    """Produto disponível para venda (gás ou água)."""

    # Identificação
    code: str              # Código interno (ex: "P13", "G20L")
    name: str              # Nome para exibição
    description: str       # Descrição curta

    # Especificações
    weight_kg: float       # Peso em kg (0 para produtos de água)

    # Preços
    price_exchange: Decimal  # Preço na TROCA (com vasilhame vazio)
    price_sale: Decimal      # Preço na VENDA (sem vasilhame)
    deposit_value: Decimal   # Valor do vasilhame (caução)

    # Controle de estoque
    stock: int             # Quantidade em estoque
    min_quantity: int      # Quantidade mínima por pedido
    max_quantity: int      # Quantidade máxima por pedido

    # Flags
    is_active: bool        # Se está disponível para venda
    is_commercial: bool    # Se é produto comercial (PJ)

    # Exibição
    emoji: str             # Emoji para WhatsApp
    sort_order: int        # Ordem de exibição

    # Especificação para UX (residencial/industrial)
    usage_label: str = ""  # Ex: "Residencial", "Industrial"

    # Categoria
    categoria: str = "gas"         # "gas" ou "agua"
    volume_litros: Optional[int] = None  # Para galões: 20


# Preços oficiais GÁSMASTER (atualizado 13/02/2026)
# P-13 Gás de cozinha: R$ 110 | P-45 Doméstico/Industrial: R$ 430 | P-20 Industrial empilhadeiras: R$ 210
PRODUCTS_CATALOG = {
    "P13": Product(
        code="P13",
        name="Botijão P13",
        description="Botijão residencial 13kg",
        weight_kg=13.0,
        price_exchange=Decimal("110.00"),   # Gás de cozinha (site)
        price_sale=Decimal("110.00"),       # Mesmo valor (site)
        deposit_value=Decimal("100.00"),
        stock=100,
        min_quantity=1,
        max_quantity=10,
        is_active=True,
        is_commercial=False,
        emoji="⛽",
        sort_order=1,
        usage_label="Residencial",
    ),
    "P20": Product(
        code="P20",
        name="Botijão P20",
        description="Botijão industrial 20kg",
        weight_kg=20.0,
        price_exchange=Decimal("210.00"),   # Gás industrial empilhadeiras (site)
        price_sale=Decimal("210.00"),       # Mesmo valor (site)
        deposit_value=Decimal("130.00"),
        stock=50,
        min_quantity=1,
        max_quantity=5,
        is_active=True,
        is_commercial=False,
        emoji="🔥",
        sort_order=2,
        usage_label="Residencial",
    ),
    "P45": Product(
        code="P45",
        name="Botijão P45",
        description="Botijão doméstico/industrial 45kg",
        weight_kg=45.0,
        price_exchange=Decimal("430.00"),   # Gás doméstico e industrial (site)
        price_sale=Decimal("430.00"),       # Mesmo valor (site)
        deposit_value=Decimal("200.00"),
        stock=30,
        min_quantity=1,
        max_quantity=3,
        is_active=True,
        is_commercial=True,
        emoji="🏭",
        sort_order=3,
        usage_label="Industrial",
    ),
    "G20L": Product(
        code="G20L",
        name="Galão de Água 20L",
        description="Galão de água mineral/potável 20 litros",
        weight_kg=0.0,
        price_exchange=Decimal("0.00"),   # PREENCHER: preço de troca (galão vazio → cheio)
        price_sale=Decimal("0.00"),       # PREENCHER: preço de venda (sem vasilhame)
        deposit_value=Decimal("0.00"),    # PREENCHER: valor do depósito se cobrado
        stock=0,
        min_quantity=1,
        max_quantity=20,
        is_active=True,
        is_commercial=False,
        emoji="💧",
        sort_order=4,
        usage_label="Residencial",
        categoria="agua",
        volume_litros=20,
    ),
}


# ═══════════════════════════════════════════════════════════════════════
# TIPOS DE OPERAÇÃO
# ═══════════════════════════════════════════════════════════════════════

class OperationType(Enum):
    """Tipos de operação disponíveis."""
    
    EXCHANGE = "exchange"    # TROCA - Cliente entrega vasilhame vazio
    SALE = "sale"            # VENDA - Cliente compra gás + vasilhame
    PICKUP = "pickup"        # RETIRA - Cliente busca na loja


@dataclass
class OperationConfig:
    """Configuração de tipo de operação."""
    
    code: str
    name: str
    description: str
    emoji: str
    requires_delivery: bool
    requires_empty_bottle: bool
    price_type: str  # "exchange" ou "sale"


OPERATION_TYPES = {
    "exchange": OperationConfig(
        code="exchange",
        name="Troca",
        description="Cliente entrega vasilhame VAZIO e recebe CHEIO",
        emoji="🔄",
        requires_delivery=True,
        requires_empty_bottle=True,
        price_type="exchange"
    ),
    "sale": OperationConfig(
        code="sale",
        name="Venda",
        description="Cliente compra gás + vasilhame (primeira compra)",
        emoji="🆕",
        requires_delivery=True,
        requires_empty_bottle=False,
        price_type="sale"
    ),
    "pickup": OperationConfig(
        code="pickup",
        name="Retira",
        description="Cliente busca na loja (sem entrega)",
        emoji="🏪",
        requires_delivery=False,
        requires_empty_bottle=False,
        price_type="exchange"  # Mesmo preço, mas sem taxa de entrega
    ),
}


# ═══════════════════════════════════════════════════════════════════════
# MÉTODOS DE PAGAMENTO
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class PaymentMethod:
    """Configuração de método de pagamento."""
    
    code: str                    # Código interno
    name: str                    # Nome para exibição
    description: str             # Descrição
    emoji: str                   # Emoji para WhatsApp
    
    # Disponibilidade
    is_active: bool
    available_for: List[str]     # ["pf", "pj"] ou ambos
    
    # Configuração
    requires_confirmation: bool   # Se precisa confirmar recebimento
    requires_change: bool         # Se precisa perguntar troco
    
    # Limites
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None


PAYMENT_METHODS = {
    "cash": PaymentMethod(
        code="cash",
        name="Dinheiro",
        description="Paga ao entregador na entrega",
        emoji="💵",
        is_active=True,
        available_for=["pf", "pj"],
        requires_confirmation=True,
        requires_change=True,
        min_value=None,
        max_value=Decimal("500.00")  # Limite de segurança
    ),
    "credit_card": PaymentMethod(
        code="credit_card",
        name="Cartão de Crédito",
        description="Máquina do entregador",
        emoji="💳",
        is_active=True,
        available_for=["pf", "pj"],
        requires_confirmation=False,
        requires_change=False,
        min_value=None,
        max_value=None
    ),
    "debit_card": PaymentMethod(
        code="debit_card",
        name="Cartão de Débito",
        description="Máquina do entregador",
        emoji="💳",
        is_active=True,
        available_for=["pf", "pj"],
        requires_confirmation=False,
        requires_change=False,
        min_value=None,
        max_value=None
    ),
    "pix": PaymentMethod(
        code="pix",
        name="PIX",
        description="Pagamento instantâneo",
        emoji="📱",
        is_active=True,
        available_for=["pf", "pj"],
        requires_confirmation=True,
        requires_change=False,
        min_value=None,
        max_value=None
    ),
    "invoice": PaymentMethod(
        code="invoice",
        name="Boleto / Faturado",
        description="Apenas para Pessoa Jurídica com cadastro",
        emoji="📄",
        is_active=True,
        available_for=["pj"],  # Apenas PJ
        requires_confirmation=False,
        requires_change=False,
        min_value=Decimal("200.00"),
        max_value=None
    ),
}


# ═══════════════════════════════════════════════════════════════════════
# ÁREA DE COBERTURA
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class CoverageArea:
    """Configuração de área de cobertura."""
    
    bairro: str
    delivery_fee: Decimal
    delivery_time_min: int  # minutos
    delivery_time_max: int  # minutos
    min_order_value: Optional[Decimal] = None
    is_active: bool = True


COVERAGE_AREAS = {
    "Alto Boqueirão": CoverageArea(
        bairro="Alto Boqueirão",
        delivery_fee=Decimal("0.00"),
        delivery_time_min=30,
        delivery_time_max=60,
        min_order_value=None,
        is_active=True
    ),
    "Boqueirão": CoverageArea(
        bairro="Boqueirão",
        delivery_fee=Decimal("0.00"),
        delivery_time_min=25,
        delivery_time_max=45,
        min_order_value=None,
        is_active=True
    ),
    "Ganchinho": CoverageArea(
        bairro="Ganchinho",
        delivery_fee=Decimal("5.00"),
        delivery_time_min=40,
        delivery_time_max=70,
        min_order_value=Decimal("100.00"),
        is_active=True
    ),
    "Hauer": CoverageArea(
        bairro="Hauer",
        delivery_fee=Decimal("0.00"),
        delivery_time_min=20,
        delivery_time_max=40,
        min_order_value=None,
        is_active=True
    ),
    "Sítio Cercado": CoverageArea(
        bairro="Sítio Cercado",
        delivery_fee=Decimal("5.00"),
        delivery_time_min=35,
        delivery_time_max=60,
        min_order_value=Decimal("80.00"),
        is_active=True
    ),
    "Umbará": CoverageArea(
        bairro="Umbará",
        delivery_fee=Decimal("8.00"),
        delivery_time_min=45,
        delivery_time_max=90,
        min_order_value=Decimal("100.00"),
        is_active=True
    ),
    "Xaxim": CoverageArea(
        bairro="Xaxim",
        delivery_fee=Decimal("0.00"),
        delivery_time_min=20,
        delivery_time_max=40,
        min_order_value=None,
        is_active=True
    ),
}


# ═══════════════════════════════════════════════════════════════════════
# HORÁRIO DE FUNCIONAMENTO
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class BusinessHours:
    """Horário de funcionamento por dia da semana."""
    
    day_of_week: int  # 0=Segunda, 6=Domingo
    is_open: bool
    open_time: Optional[str] = None  # "08:00"
    close_time: Optional[str] = None  # "18:00"
    delivery_start: Optional[str] = None  # "08:30"
    delivery_end: Optional[str] = None  # "17:30"


BUSINESS_HOURS = {
    0: BusinessHours(day_of_week=0, is_open=True, open_time="08:00", close_time="18:00", 
                     delivery_start="08:30", delivery_end="17:30"),  # Segunda
    1: BusinessHours(day_of_week=1, is_open=True, open_time="08:00", close_time="18:00",
                     delivery_start="08:30", delivery_end="17:30"),  # Terça
    2: BusinessHours(day_of_week=2, is_open=True, open_time="08:00", close_time="18:00",
                     delivery_start="08:30", delivery_end="17:30"),  # Quarta
    3: BusinessHours(day_of_week=3, is_open=True, open_time="08:00", close_time="18:00",
                     delivery_start="08:30", delivery_end="17:30"),  # Quinta
    4: BusinessHours(day_of_week=4, is_open=True, open_time="08:00", close_time="18:00",
                     delivery_start="08:30", delivery_end="17:30"),  # Sexta
    5: BusinessHours(day_of_week=5, is_open=True, open_time="08:00", close_time="12:00",
                     delivery_start="08:30", delivery_end="11:30"),  # Sábado
    6: BusinessHours(day_of_week=6, is_open=False),  # Domingo
}


STORE_ADDRESS = "Rua Principal, 1000 - Boqueirão"


# ═══════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════

def get_product(code: str) -> Optional[Product]:
    """Busca produto pelo código."""
    return PRODUCTS_CATALOG.get(code.upper())


def get_active_products() -> List[Product]:
    """Retorna lista de produtos ativos ordenados."""
    products = [p for p in PRODUCTS_CATALOG.values() if p.is_active]
    return sorted(products, key=lambda p: p.sort_order)


def get_coverage_area(bairro: str) -> Optional[CoverageArea]:
    """Busca área de cobertura pelo bairro."""
    # Normalizar nome do bairro
    for key, area in COVERAGE_AREAS.items():
        if key.lower() == bairro.lower():
            return area
    return None


def is_area_covered(bairro: str) -> bool:
    """Verifica se bairro está na área de cobertura."""
    area = get_coverage_area(bairro)
    return area is not None and area.is_active


def get_payment_methods_for_customer(customer_type: str) -> List[PaymentMethod]:
    """Retorna métodos de pagamento disponíveis para o tipo de cliente."""
    methods = []
    for method in PAYMENT_METHODS.values():
        if not method.is_active:
            continue
        if customer_type.lower() in method.available_for:
            methods.append(method)
    return methods


def calculate_price(product_code: str, quantity: int, operation_type: str) -> Optional[Decimal]:
    """Calcula preço total baseado no produto, quantidade e tipo de operação."""
    product = get_product(product_code)
    if not product:
        return None
    
    # Selecionar preço baseado na operação
    if operation_type == "sale":
        unit_price = product.price_sale
    else:  # exchange ou pickup
        unit_price = product.price_exchange
    
    return unit_price * quantity


def is_business_open(day_of_week: int, current_time: str) -> bool:
    """
    Verifica se está no horário de funcionamento.
    
    Args:
        day_of_week: 0=Segunda, 6=Domingo
        current_time: "HH:MM"
    """
    hours = BUSINESS_HOURS.get(day_of_week)
    if not hours or not hours.is_open:
        return False
    
    if not hours.open_time or not hours.close_time:
        return False
    
    return hours.open_time <= current_time <= hours.close_time


def can_deliver_now(day_of_week: int, current_time: str) -> bool:
    """
    Verifica se pode fazer entrega agora.
    
    Args:
        day_of_week: 0=Segunda, 6=Domingo
        current_time: "HH:MM"
    """
    hours = BUSINESS_HOURS.get(day_of_week)
    if not hours or not hours.is_open:
        return False
    
    if not hours.delivery_start or not hours.delivery_end:
        return False
    
    return hours.delivery_start <= current_time <= hours.delivery_end
