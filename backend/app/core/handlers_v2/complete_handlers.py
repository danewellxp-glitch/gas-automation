"""
Handlers da Fase COMPLETE - Flow Engine 2.0
Responsáveis por conclusão e pós-venda.
"""

import logging
from typing import Optional, Dict
from decimal import Decimal

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)
from app.core.handlers_v2.base import BaseHandler, HandlerResult, MessageResponse
from app.core.message_templates import ORDER_CONFIRMED
from app.core.product_catalog import get_coverage_area
from app.core.flow_config import get_quick_replies

logger = logging.getLogger(__name__)


class CompleteConfirmedHandler(BaseHandler):
    """Handler para COMPLETE_CONFIRMED - Pedido confirmado com sucesso."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa pedido confirmado."""
        
        # Buscar pedido criado
        order_id = conversation_context.collected_data.get("order_id")
        
        if not order_id:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="❌ Erro ao confirmar pedido. Entre em contato."
                    )
                ],
                next_state=ConversationState.SUPPORT_HUMAN,
                needs_human=True
            )
        
        # Buscar ordem do banco
        from app.database import AsyncSessionLocal
        from app.models.order import Order
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order).where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
        
        if not order:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="❌ Pedido não encontrado. Entre em contato."
                    )
                ],
                next_state=ConversationState.SUPPORT_HUMAN,
                needs_human=True
            )
        
        # Formatar itens (agrupados: 4x P13 em vez de 1x P13 repetido)
        items_text = self._format_items_summary_aggregated(
            order_context.items if order_context and order_context.items else []
        )
        
        # Formatar endereço
        address_text = self._format_address(order_context.address) if order_context and order_context.address else "Retirada na loja"
        
        # Formatar pagamento
        payment_labels = {
            "cash": "💵 Dinheiro na entrega",
            "credit_card": "💳 Cartão na entrega",
            "debit_card": "💳 Cartão de Débito na entrega",
            "pix": "📱 PIX",
            "invoice": "📄 Faturado",
        }
        payment_text = payment_labels.get(
            order_context.payment_method if order_context else None,
            "Pagamento na entrega"
        )
        
        # Estimativa de entrega
        delivery_time = "30-60 min"
        if order_context and order_context.address and order_context.address.get("bairro"):
            area = get_coverage_area(order_context.address["bairro"])
            if area:
                delivery_time = f"{area.delivery_time_min}-{area.delivery_time_max} min"
        
        # Mensagem de confirmação
        confirmation_text = ORDER_CONFIRMED.format(
            order_number=order.order_number,
            items_summary=items_text,
            address=address_text,
            total=self._format_currency(order.total_amount),
            payment_method=payment_text,
            delivery_time=delivery_time
        )
        
        # Atualizar contador de pedidos do cliente
        if customer_context:
            customer_context.order_count += 1
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(text=confirmation_text)
            ],
            next_state=ConversationState.COMPLETE_FOLLOWUP
        )


class CompleteFollowupHandler(BaseHandler):
    """Handler para COMPLETE_FOLLOWUP - Pós-venda e acompanhamento."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa pós-venda."""
        
        msg_lower = message.lower().strip()
        
        # Rastrear pedido
        if any(word in msg_lower for word in ["rastrear", "status", "pedido", "track"]):
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text="📦 Buscando status do seu pedido...")
                ],
                next_state=ConversationState.TRACKING_STATUS
            )
        
        # Novo pedido
        if any(word in msg_lower for word in ["novo", "outro", "mais", "comprar"]):
            # Limpar contexto do pedido anterior
            conversation_context.collected_data = {}
            order_context = OrderContext()
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="🛒 Vamos fazer um novo pedido!\n\nQual produto?"
                    )
                ],
                next_state=ConversationState.ORDERING_PRODUCT
            )
        
        # Qualquer outra mensagem - oferecer opções
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="Posso ajudar com mais alguma coisa?",
                    buttons=[
                        {"id": "track_order", "text": "📦 Ver Status"},
                        {"id": "new_order", "text": "🛒 Novo Pedido"},
                        {"id": "talk_human", "text": "👤 Atendente"},
                    ]
                )
            ],
            next_state=ConversationState.COMPLETE_FOLLOWUP
        )
