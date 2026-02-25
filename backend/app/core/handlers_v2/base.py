"""
Base Handler - Classe abstrata para todos os handlers do Flow Engine 2.0
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from decimal import Decimal

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)

logger = logging.getLogger(__name__)


@dataclass
class MessageResponse:
    """Resposta a ser enviada ao usuário."""

    text: str
    buttons: Optional[List[Dict]] = None
    list_sections: Optional[List[Dict]] = None
    list_button_text: Optional[str] = None
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    footer: Optional[str] = None

    def has_buttons(self) -> bool:
        return bool(self.buttons)

    def has_list(self) -> bool:
        return bool(self.list_sections)


@dataclass
class HandlerResult:
    """Resultado do processamento de um handler."""
    
    # Contextos atualizados
    conversation_context: ConversationContext
    customer_context: Optional[CustomerContext] = None
    order_context: Optional[OrderContext] = None
    
    # Respostas
    responses: List[MessageResponse] = None
    
    # Próximo estado
    next_state: ConversationState = None
    
    # Status
    success: bool = True
    error: Optional[str] = None
    
    # Flags especiais
    needs_human: bool = False
    should_save_snapshot: bool = False
    
    def __post_init__(self):
        if self.responses is None:
            self.responses = []


class BaseHandler(ABC):
    """
    Classe base abstrata para todos os handlers.
    
    Cada handler é responsável por:
    1. Processar a mensagem do usuário
    2. Atualizar os contextos
    3. Gerar respostas apropriadas
    4. Determinar o próximo estado
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """
        Processa a mensagem e retorna o resultado.
        
        Args:
            message: Mensagem do usuário
            conversation_context: Contexto da conversa
            customer_context: Contexto do cliente
            order_context: Contexto do pedido
            entities: Entidades extraídas pelo NLU
        
        Returns:
            HandlerResult com respostas e próximo estado
        """
        pass
    
    def _create_response(
        self,
        text: str,
        buttons: Optional[List[Dict]] = None,
        list_sections: Optional[List[Dict]] = None,
        list_button_text: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> MessageResponse:
        """Helper para criar resposta."""
        return MessageResponse(
            text=text,
            buttons=buttons,
            list_sections=list_sections,
            list_button_text=list_button_text,
            footer=footer,
        )
    
    def _create_result(
        self,
        conversation_context: ConversationContext,
        responses: List[MessageResponse],
        next_state: ConversationState,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        **kwargs
    ) -> HandlerResult:
        """Helper para criar resultado."""
        return HandlerResult(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=responses,
            next_state=next_state,
            **kwargs
        )
    
    def _format_currency(self, value: Decimal) -> str:
        """Formata valor em reais."""
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def _format_items_summary_aggregated(self, items: List[Dict]) -> str:
        """Agrupa itens por product_code e formata como '4x P13' ou '2x P13, 1x P20'."""
        if not items:
            return "Pedido"
        agg: Dict[str, int] = {}
        for item in items:
            code = item.get("product_code", "") or ""
            qty = int(item.get("quantity", 1))
            agg[code] = agg.get(code, 0) + qty
        parts = [f"{qty}x {code}" for code, qty in sorted(agg.items()) if code]
        return ", ".join(parts) if parts else "Pedido"
    
    def _format_address(self, address: Dict) -> str:
        """Formata endereço para exibição."""
        if not address:
            return "Endereço não informado"
        
        if address.get("full_address"):
            return address["full_address"]
        
        parts = []
        if address.get("street"):
            parts.append(address["street"])
        if address.get("number"):
            parts.append(address["number"])
        if address.get("complement"):
            parts.append(f"- {address['complement']}")
        if address.get("bairro"):
            parts.append(f"- {address['bairro']}")
        
        return ", ".join(parts) if parts else "Endereço cadastrado"
    
    def _increment_retry(self, context: ConversationContext) -> int:
        """Incrementa contador de tentativas."""
        context.retry_count += 1
        return context.retry_count
    
    def _reset_retry(self, context: ConversationContext) -> None:
        """Reseta contador de tentativas."""
        context.retry_count = 0
    
    def _should_escalate_to_human(self, context: ConversationContext) -> bool:
        """Verifica se deve escalar para atendente humano."""
        from app.core.flow_config import MAX_RETRY_COUNT
        return context.retry_count >= MAX_RETRY_COUNT
    
    async def _get_customer_by_phone(self, phone: str):
        """Busca cliente pelo telefone."""
        from app.database import AsyncSessionLocal
        from app.models.customer import Customer
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Customer).where(Customer.phone == phone)
            )
            return result.scalar_one_or_none()
    
    async def _get_last_order(self, customer_id: str):
        """Busca último pedido do cliente."""
        from app.database import AsyncSessionLocal
        from app.models.order import Order, OrderStatus
        from sqlalchemy import select, desc
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order)
                .where(Order.customer_id == customer_id)
                .where(Order.status != OrderStatus.CANCELLED.value)
                .order_by(desc(Order.created_at))
                .limit(1)
            )
            return result.scalar_one_or_none()
    
    async def _get_product(self, code: str):
        """Busca produto pelo código."""
        from app.database import AsyncSessionLocal
        from app.models.product import Product
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product).where(Product.code == code.upper())
            )
            return result.scalar_one_or_none()
    
    def _validate_cpf(self, cpf: str) -> bool:
        """Valida CPF brasileiro."""
        import re
        
        cpf = re.sub(r"[^0-9]", "", cpf)
        if len(cpf) != 11:
            return False
        if cpf == cpf[0] * 11:
            return False
        
        # Validação dos dígitos verificadores
        for i in range(9, 11):
            value = sum((int(cpf[num]) * ((i + 1) - num) for num in range(0, i)))
            digit = ((value * 10) % 11) % 10
            if digit != int(cpf[i]):
                return False
        
        return True
    
    def _validate_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ brasileiro."""
        import re

        cnpj = re.sub(r"[^0-9]", "", cnpj)
        if len(cnpj) != 14:
            return False
        if cnpj == cnpj[0] * 14:
            return False

        return True

    async def _get_last_order_with_items(self, customer_id: str):
        """Busca ultimo pedido do cliente com itens."""
        from app.database import AsyncSessionLocal
        from app.models.order import Order, OrderItem, OrderStatus
        from sqlalchemy import select, desc
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.customer_id == customer_id)
                .where(Order.status != OrderStatus.CANCELLED.value)
                .order_by(desc(Order.created_at))
                .limit(1)
            )
            return result.scalar_one_or_none()

    def _build_product_list_sections(self) -> List[Dict]:
        """Constroi secoes de List Message com todos os produtos ativos."""
        from app.core.product_catalog import get_active_products

        products = get_active_products()
        residential = []
        commercial = []

        for p in products:
            price_text = self._format_currency(p.price_exchange)
            # WhatsApp List row: title max 24 chars, description max 72 chars
            row = {
                "id": p.code,
                "title": "{} ({:.0f}kg) - {}".format(p.code, p.weight_kg, price_text),
                "description": p.description or "",
            }
            if p.is_commercial:
                commercial.append(row)
            else:
                residential.append(row)

        sections = []
        if residential:
            sections.append({"title": "Residencial", "rows": residential})
        if commercial:
            sections.append({"title": "Comercial", "rows": commercial})
        return sections

    def _build_product_text(self) -> str:
        """Constroi texto descritivo dos produtos (fallback)."""
        from app.core.product_catalog import get_active_products

        products = get_active_products()
        lines = []
        for p in products:
            label = " {}".format(p.usage_label) if getattr(p, "usage_label", None) else ""
            lines.append(
                "{} *{}* ({:.0f}kg){} - {}".format(
                    p.emoji, p.code, p.weight_kg, label, self._format_currency(p.price_exchange)
                )
            )
        return "\n".join(lines)

    async def _ensure_customer_for_order(
        self,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext],
    ) -> Optional[CustomerContext]:
        """Garante que o cliente existe no banco e que customer_context.customer_id esta definido."""
        if not customer_context:
            customer_context = CustomerContext()
        if customer_context.customer_id:
            return customer_context
        try:
            from app.database import AsyncSessionLocal
            from app.models.customer import Customer
            from sqlalchemy import select

            phone = conversation_context.phone
            if not phone:
                return customer_context

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Customer).where(Customer.phone == phone)
                )
                customer = result.scalar_one_or_none()

                if not customer:
                    name = (
                        conversation_context.collected_data.get("name")
                        or customer_context.name
                        or "Cliente"
                    )
                    name = (name or "Cliente").strip()[:200]
                    customer = Customer(phone=phone, name=name or "Cliente")
                    db.add(customer)
                    await db.flush()
                else:
                    name_from_ctx = (
                        conversation_context.collected_data.get("name")
                        or customer_context.name
                    )
                    if name_from_ctx and (name_from_ctx or "").strip():
                        name_from_ctx = (name_from_ctx or "").strip()[:200]
                        if name_from_ctx and name_from_ctx != (customer.name or ""):
                            customer.name = name_from_ctx

                await db.commit()
                customer_context.customer_id = str(customer.id)
                if not customer_context.name and getattr(customer, "name", None):
                    customer_context.name = customer.name
                return customer_context
        except Exception as e:
            logger.error("Erro ao garantir cliente: %s", e, exc_info=True)
            return customer_context

    async def _create_order(
        self,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext],
        order_context: Optional[OrderContext],
    ):
        """Cria pedido no banco de dados."""
        try:
            from app.database import AsyncSessionLocal
            from app.models.order import Order, OrderItem, OrderStatus
            from sqlalchemy import select

            if not order_context or not order_context.items:
                return None

            order_total = sum(Decimal(str(it.get("subtotal", 0))) for it in order_context.items)
            if order_context.delivery_fee:
                order_total += Decimal(str(order_context.delivery_fee))

            async with AsyncSessionLocal() as db:
                order = Order(
                    customer_id=customer_context.customer_id if customer_context else None,
                    status=OrderStatus.PENDING.value,
                    payment_method=order_context.payment_method,
                    total_amount=order_total,
                    delivery_address=order_context.address,
                    delivery_bairro=order_context.address.get("bairro") if order_context.address else None,
                )
                db.add(order)
                await db.flush()

                for item_data in order_context.items:
                    item = OrderItem(
                        order_id=order.id,
                        product_code=item_data["product_code"],
                        product_name=item_data.get("product_name", item_data["product_code"]),
                        quantity=item_data["quantity"],
                        unit_price=Decimal(str(item_data["unit_price"])),
                        subtotal=Decimal(str(item_data["subtotal"])),
                    )
                    db.add(item)

                await db.commit()
                await db.refresh(order)

                logger.info("Pedido criado: #%s - Total: %s", order.order_number, order.total_amount)

                try:
                    from app.api.websocket import emit_new_order
                    await emit_new_order({
                        "id": str(order.id),
                        "order_number": order.order_number,
                        "customer_id": customer_context.customer_id if customer_context else None,
                        "status": order.status,
                        "total_amount": float(order.total_amount),
                        "payment_method": order_context.payment_method,
                        "created_at": order.created_at.isoformat() if order.created_at else None,
                    })
                except Exception as e:
                    logger.error("Erro ao emitir evento WebSocket: %s", e)

                return order

        except Exception as e:
            logger.error("Erro ao criar pedido: %s", e, exc_info=True)
            return None

    def _build_order_confirmation_text(
        self,
        order,
        order_context: Optional[OrderContext],
        customer_context: Optional[CustomerContext],
    ) -> str:
        """Monta texto de confirmacao do pedido."""
        from app.core.message_templates import ORDER_CONFIRMED
        from app.core.product_catalog import get_coverage_area

        items_text = self._format_items_summary_aggregated(
            order_context.items if order_context and order_context.items else []
        )
        address_text = self._format_address(order_context.address) if order_context and order_context.address else "Retirada na loja"
        payment_labels = {
            "cash": "Dinheiro na entrega",
            "credit_card": "Cartao na entrega",
            "debit_card": "Cartao de Debito na entrega",
            "pix": "PIX",
            "invoice": "Faturado",
        }
        payment_text = payment_labels.get(
            order_context.payment_method if order_context else None, "Pagamento na entrega"
        )
        delivery_time = "30-60 min"
        if order_context and order_context.address and order_context.address.get("bairro"):
            area = get_coverage_area(order_context.address["bairro"])
            if area:
                delivery_time = "{}-{} min".format(area.delivery_time_min, area.delivery_time_max)

        return ORDER_CONFIRMED.format(
            order_number=order.order_number,
            items_summary=items_text,
            address=address_text,
            total=self._format_currency(order.total_amount),
            payment_method=payment_text,
            delivery_time=delivery_time,
        )
