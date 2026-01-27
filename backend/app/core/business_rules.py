"""
Regras de negócio da distribuidora de gás.
Centraliza validações, cálculos e políticas de negócio.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import datetime, time

from app.config import settings


@dataclass
class Product:
    """Representação de um produto."""
    code: str
    name: str
    weight_kg: int
    price: Decimal
    description: str = ""


@dataclass
class DeliveryFee:
    """Taxa de entrega para um bairro."""
    bairro: str
    fee: Decimal
    estimated_minutes: int


@dataclass
class OrderCalculation:
    """Resultado do cálculo de um pedido."""
    product: Product
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal
    estimated_minutes: int


class BusinessRules:
    """
    Regras de negócio da distribuidora.

    Contém todas as regras e políticas que governam o funcionamento do sistema.
    """

    # REMOVIDO: Produtos hardcoded
    # Produtos devem ser buscados do banco de dados (PostgreSQL)
    # Que é sincronizado do Firebird (Gerente.fdb)
    # Usar ProductService ou buscar diretamente do banco

    # Taxas de entrega por bairro
    DELIVERY_FEES: dict[str, DeliveryFee] = {
        "centro": DeliveryFee("Centro", Decimal("0.00"), 30),
        "boqueirão": DeliveryFee("Boqueirão", Decimal("5.00"), 35),
        "boqueirao": DeliveryFee("Boqueirão", Decimal("5.00"), 35),
        "alto boqueirão": DeliveryFee("Alto Boqueirão", Decimal("8.00"), 40),
        "alto boqueirao": DeliveryFee("Alto Boqueirão", Decimal("8.00"), 40),
        "xaxim": DeliveryFee("Xaxim", Decimal("5.00"), 35),
        "hauer": DeliveryFee("Hauer", Decimal("5.00"), 35),
        "uberaba": DeliveryFee("Uberaba", Decimal("8.00"), 40),
        "cajuru": DeliveryFee("Cajuru", Decimal("10.00"), 45),
        "capão raso": DeliveryFee("Capão Raso", Decimal("10.00"), 45),
        "capao raso": DeliveryFee("Capão Raso", Decimal("10.00"), 45),
        "pinheirinho": DeliveryFee("Pinheirinho", Decimal("10.00"), 45),
        "portão": DeliveryFee("Portão", Decimal("8.00"), 40),
        "portao": DeliveryFee("Portão", Decimal("8.00"), 40),
        "água verde": DeliveryFee("Água Verde", Decimal("5.00"), 35),
        "agua verde": DeliveryFee("Água Verde", Decimal("5.00"), 35),
        "cristo rei": DeliveryFee("Cristo Rei", Decimal("8.00"), 40),
        "jardim das américas": DeliveryFee("Jardim das Américas", Decimal("8.00"), 40),
        "jardim das americas": DeliveryFee("Jardim das Américas", Decimal("8.00"), 40),
        "jardim botânico": DeliveryFee("Jardim Botânico", Decimal("5.00"), 35),
        "jardim botanico": DeliveryFee("Jardim Botânico", Decimal("5.00"), 35),
        "rebouças": DeliveryFee("Rebouças", Decimal("5.00"), 35),
        "reboucas": DeliveryFee("Rebouças", Decimal("5.00"), 35),
    }

    # Taxa padrão para bairros não listados
    DEFAULT_DELIVERY_FEE = DeliveryFee("Outros", Decimal("15.00"), 50)

    # Limites
    MAX_QUANTITY_PER_ORDER = 10
    MIN_ORDER_VALUE = Decimal("50.00")
    MAX_ORDER_VALUE = Decimal("5000.00")

    # Horário de funcionamento
    OPENING_TIME = time(7, 0)  # 7:00
    CLOSING_TIME = time(21, 0)  # 21:00

    # Métodos de pagamento
    PAYMENT_METHODS = ["pix", "dinheiro", "cartao", "credit_card", "cash"]

    @classmethod
    async def get_product(cls, code: str, db_session) -> Optional[Product]:
        """Retorna produto pelo código do banco de dados."""
        from sqlalchemy import select
        from app.models.product import Product
        result = await db_session.execute(
            select(Product).where(Product.code == code.upper())
        )
        return result.scalar_one_or_none()

    @classmethod
    async def list_products(cls, db_session) -> list[Product]:
        """Lista todos os produtos disponíveis do banco de dados."""
        from sqlalchemy import select
        from app.models.product import Product
        result = await db_session.execute(
            select(Product).where(Product.is_active == True)
        )
        return result.scalars().all()

    @classmethod
    def get_delivery_fee(cls, bairro: str) -> DeliveryFee:
        """Retorna taxa de entrega para um bairro."""
        if not bairro:
            return cls.DEFAULT_DELIVERY_FEE

        bairro_lower = bairro.lower().strip()
        return cls.DELIVERY_FEES.get(bairro_lower, cls.DEFAULT_DELIVERY_FEE)

    @classmethod
    def is_bairro_supported(cls, bairro: str) -> bool:
        """Verifica se bairro é atendido."""
        if not bairro:
            return False
        return bairro.lower().strip() in cls.DELIVERY_FEES

    @classmethod
    async def calculate_order(
        cls,
        product_code: str,
        quantity: int,
        db_session,
        bairro: Optional[str] = None,
    ) -> Optional[OrderCalculation]:
        """
        Calcula valores do pedido.

        Returns:
            OrderCalculation ou None se produto inválido
        """
        product = await cls.get_product(product_code, db_session)
        if not product:
            return None

        unit_price = product.price
        subtotal = unit_price * quantity

        delivery = cls.get_delivery_fee(bairro) if bairro else cls.DEFAULT_DELIVERY_FEE
        delivery_fee = delivery.fee

        total = subtotal + delivery_fee

        return OrderCalculation(
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            estimated_minutes=delivery.estimated_minutes,
        )

    @classmethod
    def validate_quantity(cls, quantity: int) -> tuple[bool, str]:
        """
        Valida quantidade do pedido.

        Returns:
            (válido, mensagem de erro)
        """
        if quantity < 1:
            return False, "Quantidade mínima é 1 botijão."

        if quantity > cls.MAX_QUANTITY_PER_ORDER:
            return False, f"Quantidade máxima é {cls.MAX_QUANTITY_PER_ORDER} botijões. Para pedidos maiores, fale com um atendente."

        return True, ""

    @classmethod
    def validate_order_value(cls, total: Decimal) -> tuple[bool, str]:
        """
        Valida valor total do pedido.

        Returns:
            (válido, mensagem de erro)
        """
        if total < cls.MIN_ORDER_VALUE:
            return False, f"Valor mínimo do pedido é R$ {cls.MIN_ORDER_VALUE:.2f}."

        if total > cls.MAX_ORDER_VALUE:
            return False, f"Valor máximo do pedido é R$ {cls.MAX_ORDER_VALUE:.2f}. Para pedidos maiores, fale com um atendente."

        return True, ""

    @classmethod
    def validate_payment_method(cls, method: str) -> tuple[bool, str]:
        """
        Valida método de pagamento.

        Returns:
            (válido, mensagem de erro)
        """
        if method.lower() not in cls.PAYMENT_METHODS:
            return False, f"Método de pagamento inválido. Aceitos: Pix, Dinheiro ou Cartão."

        return True, ""

    @classmethod
    def is_open(cls, check_time: Optional[datetime] = None) -> bool:
        """Verifica se está no horário de funcionamento."""
        if check_time is None:
            check_time = datetime.now()

        current_time = check_time.time()
        return cls.OPENING_TIME <= current_time <= cls.CLOSING_TIME

    @classmethod
    def get_opening_hours_message(cls) -> str:
        """Retorna mensagem formatada com horário de funcionamento."""
        return (
            f"Nosso horário de atendimento é das "
            f"{cls.OPENING_TIME.strftime('%H:%M')} às "
            f"{cls.CLOSING_TIME.strftime('%H:%M')}."
        )

    @classmethod
    def format_currency(cls, value: Decimal) -> str:
        """Formata valor como moeda brasileira."""
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @classmethod
    def format_phone(cls, phone: str) -> str:
        """Formata telefone para exibição."""
        # Remove caracteres não numéricos
        digits = "".join(filter(str.isdigit, phone))

        # Formato brasileiro: (41) 99999-9999
        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        elif len(digits) == 13 and digits.startswith("55"):
            return f"+{digits[:2]} ({digits[2:4]}) {digits[4:9]}-{digits[9:]}"

        return phone

    @classmethod
    def extract_bairro_from_address(cls, address: str) -> Optional[str]:
        """
        Tenta extrair o bairro de um endereço completo.

        Procura por bairros conhecidos no texto do endereço.
        """
        if not address:
            return None

        address_lower = address.lower()

        # Procura por bairros conhecidos no endereço
        for bairro_key in cls.DELIVERY_FEES:
            if bairro_key in address_lower:
                return cls.DELIVERY_FEES[bairro_key].bairro

        return None


# Instância global para uso conveniente
business_rules = BusinessRules()
