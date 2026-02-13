"""
Handlers de SUPPORT - Flow Engine 2.0
Handlers paralelos acessíveis de qualquer estado.
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
from app.core.message_templates import (
    TALKING_TO_HUMAN,
    TRACKING_STATUS,
    TRACKING_NO_ORDERS,
    EMERGENCY_ALERT,
)
from app.core.flow_config import get_quick_replies

logger = logging.getLogger(__name__)


class SupportHumanHandler(BaseHandler):
    """Handler para SUPPORT_HUMAN - Atendimento humano."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa transferência para atendente."""
        
        msg_lower = message.lower().strip()
        
        # Voltar ao bot
        if msg_lower in ["menu", "bot", "voltar"]:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="✅ Voltando ao atendimento automático!",
                        buttons=get_quick_replies("main_menu")
                    )
                ],
                next_state=ConversationState.GREETING_INITIAL
            )
        
        # Notificar operadores via WebSocket
        try:
            from app.api.websocket import emit_new_message
            
            customer_data = None
            if customer_context:
                customer_data = {
                    "id": customer_context.customer_id,
                    "name": customer_context.name,
                    "phone": conversation_context.phone,
                }
            
            await emit_new_message(
                phone=conversation_context.phone,
                message=f"🔔 ATENDIMENTO HUMANO: {message}",
                direction="incoming",
                customer_data=customer_data,
            )
            
            logger.info(f"Notificação enviada para operadores: {conversation_context.phone}")
            
        except Exception as e:
            logger.error(f"Erro ao notificar operadores: {e}")
        
        # Mensagem para o cliente
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(text=TALKING_TO_HUMAN)
            ],
            next_state=ConversationState.SUPPORT_HUMAN,
            needs_human=True
        )


class SupportFAQHandler(BaseHandler):
    """Handler para SUPPORT_FAQ - FAQ inline."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa pergunta FAQ."""
        
        # Detectar categoria da FAQ
        faq_category = self._detect_faq_category(message)
        
        if not faq_category:
            # Não é FAQ - voltar ao estado anterior
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Não entendi sua pergunta. Digite *menu* para opções."
                    )
                ],
                next_state=conversation_context.return_state or ConversationState.GREETING_INITIAL
            )
        
        # Responder FAQ
        faq_response = self._get_faq_response(faq_category)
        
        # Se estava no meio de um pedido, lembrar onde parou
        return_prompt = ""
        if conversation_context.return_state and conversation_context.return_state != ConversationState.GREETING_INITIAL:
            state_prompts = {
                ConversationState.ORDERING_PRODUCT: "\n\n─────────────\nVoltando ao pedido...\n🛒 Qual produto?",
                ConversationState.ORDERING_QUANTITY: "\n\n─────────────\nVoltando ao pedido...\nQuantos botijões?",
                ConversationState.ORDERING_ADDRESS: "\n\n─────────────\nVoltando ao pedido...\n📍 Qual o endereço?",
                ConversationState.CHECKOUT_PAYMENT: "\n\n─────────────\nVoltando ao pedido...\n💳 Como deseja pagar?",
            }
            return_prompt = state_prompts.get(conversation_context.return_state, "")
        
        full_response = faq_response + return_prompt
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(text=full_response)
            ],
            next_state=conversation_context.return_state or ConversationState.GREETING_INITIAL
        )
    
    def _detect_faq_category(self, message: str) -> Optional[str]:
        """Detecta categoria da FAQ."""
        msg_lower = message.lower()
        
        if any(word in msg_lower for word in ["horário", "horario", "abre", "fecha", "funciona"]):
            return "business_hours"
        
        if any(word in msg_lower for word in ["preço", "preco", "quanto", "custa", "valor"]):
            return "prices"
        
        if any(word in msg_lower for word in ["entrega", "demora", "tempo", "quanto tempo"]):
            return "delivery_time"
        
        if any(word in msg_lower for word in ["área", "area", "bairro", "entregam", "atende"]):
            return "coverage_area"
        
        if any(word in msg_lower for word in ["pagamento", "pagar", "forma"]):
            return "payment_methods"
        
        return None
    
    def _get_faq_response(self, category: str) -> str:
        """Retorna resposta da FAQ."""
        from app.core.message_templates import (
            FAQ_DELIVERY_TIME,
            FAQ_COVERAGE_AREA,
            FAQ_PAYMENT_METHODS,
            FAQ_PRICES,
        )
        from app.core.product_catalog import COVERAGE_AREAS, PRODUCTS_CATALOG, STORE_ADDRESS
        
        if category == "business_hours":
            return """⏰ *Horário de Funcionamento*

Seg-Sex: 8h às 18h
Sábado: 8h às 12h
Domingo: Fechado

Entregas:
Seg-Sex: 8:30 às 17:30
Sábado: 8:30 às 11:30"""
        
        if category == "prices":
            prices_text = []
            for code, product in PRODUCTS_CATALOG.items():
                prices_text.append(
                    f"{product.emoji} *{code}*: {self._format_currency(product.price_exchange)} (troca) / "
                    f"{self._format_currency(product.price_sale)} (venda)"
                )
            return "💰 *Preços*\n\n" + "\n".join(prices_text)
        
        if category == "delivery_time":
            times_text = []
            for bairro, area in COVERAGE_AREAS.items():
                times_text.append(f"• {bairro}: {area.delivery_time_min}-{area.delivery_time_max} min")
            return "⏱️ *Tempo de Entrega*\n\n" + "\n".join(times_text)
        
        if category == "coverage_area":
            areas_text = "\n".join([f"• {b}" for b in COVERAGE_AREAS.keys()])
            return f"📍 *Área de Entrega*\n\nEntregamos em:\n{areas_text}\n\n🏪 Retirada na loja:\n{STORE_ADDRESS}"
        
        if category == "payment_methods":
            return """💳 *Formas de Pagamento*

• 💵 Dinheiro (troco disponível)
• 💳 Cartão de Crédito/Débito
• 📱 PIX
• 📄 Faturado (apenas PJ)

Pagamento na entrega!"""
        
        return "Informação não disponível."


class TrackingStatusHandler(BaseHandler):
    """Handler para TRACKING_STATUS - Status do pedido."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa rastreamento."""
        
        # Buscar pedidos do cliente
        if not customer_context or not customer_context.customer_id:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text=TRACKING_NO_ORDERS
                    )
                ],
                next_state=ConversationState.GREETING_INITIAL
            )
        
        # Buscar pedidos ativos
        from app.database import AsyncSessionLocal
        from app.models.order import Order, OrderStatus
        from sqlalchemy import select, desc
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Order)
                .where(Order.customer_id == customer_context.customer_id)
                .where(Order.status.in_([
                    OrderStatus.PENDING.value,
                    OrderStatus.CONFIRMED.value,
                    OrderStatus.IN_TRANSIT.value,
                ]))
                .order_by(desc(Order.created_at))
                .limit(5)
            )
            orders = result.scalars().all()
        
        if not orders:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text=TRACKING_NO_ORDERS
                    )
                ],
                next_state=ConversationState.GREETING_INITIAL
            )
        
        # Formatar status dos pedidos
        orders_text = []
        for order in orders:
            status_emoji = {
                OrderStatus.PENDING.value: "⏳",
                OrderStatus.CONFIRMED.value: "✅",
                OrderStatus.IN_TRANSIT.value: "🚚",
            }
            
            status_labels = {
                OrderStatus.PENDING.value: "Aguardando confirmação",
                OrderStatus.CONFIRMED.value: "Confirmado",
                OrderStatus.IN_TRANSIT.value: "Em rota de entrega",
            }
            
            emoji = status_emoji.get(order.status, "📦")
            label = status_labels.get(order.status, order.status)
            
            orders_text.append(
                f"{emoji} *Pedido #{order.order_number}*\n"
                f"Status: {label}\n"
                f"Total: {self._format_currency(order.total_amount)}"
            )
        
        full_text = "\n\n".join(orders_text)
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text=f"📦 *Seus Pedidos*\n\n{full_text}",
                    buttons=[
                        {"id": "new_order", "text": "🛒 Novo Pedido"},
                        {"id": "menu", "text": "📋 Menu"},
                    ]
                )
            ],
            next_state=ConversationState.TRACKING_OPTIONS
        )


class TrackingOptionsHandler(BaseHandler):
    """Handler para TRACKING_OPTIONS - Opções após ver status."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa opções de tracking."""
        
        msg_lower = message.lower().strip()
        
        # Novo pedido
        if msg_lower in ["new_order", "novo", "comprar"]:
            # Limpar contexto
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
        
        # Menu
        if msg_lower in ["menu", "voltar"]:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Como posso ajudar?",
                        buttons=get_quick_replies("main_menu")
                    )
                ],
                next_state=ConversationState.GREETING_INITIAL
            )
        
        # Qualquer outra mensagem
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="O que deseja fazer?",
                    buttons=[
                        {"id": "new_order", "text": "🛒 Novo Pedido"},
                        {"id": "menu", "text": "📋 Menu"},
                    ]
                )
            ],
            next_state=ConversationState.TRACKING_OPTIONS
        )


class ErrorRecoveryHandler(BaseHandler):
    """Handler para ERROR_RECOVERY - Recuperação de erro."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa recuperação de erro."""
        
        msg_lower = message.lower().strip()
        
        # Tentar novamente
        if msg_lower in ["retry", "tentar", "sim", "s"]:
            # Voltar ao estado anterior
            if conversation_context.state_history:
                previous_state = conversation_context.state_history[-1]
                
                return self._create_result(
                    conversation_context=conversation_context,
                    customer_context=customer_context,
                    order_context=order_context,
                    responses=[
                        self._create_response(
                            text="✅ Vamos tentar novamente!"
                        )
                    ],
                    next_state=ConversationState(previous_state)
                )
        
        # Recomeçar
        if msg_lower in ["restart", "recomeçar", "começar", "novo"]:
            # Limpar contextos
            conversation_context.collected_data = {}
            conversation_context.state_history = []
            order_context = OrderContext()
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="🔄 Vamos começar de novo!\n\nComo posso ajudar?",
                        buttons=get_quick_replies("main_menu")
                    )
                ],
                next_state=ConversationState.GREETING_INITIAL
            )
        
        # Falar com atendente
        if msg_lower in ["human", "atendente", "ajuda"]:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="👤 Conectando com um atendente..."
                    )
                ],
                next_state=ConversationState.SUPPORT_HUMAN,
                needs_human=True
            )
        
        # Oferecer opções
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="❌ Ocorreu um erro.\n\nO que deseja fazer?",
                    buttons=[
                        {"id": "retry", "text": "🔄 Tentar novamente"},
                        {"id": "restart", "text": "🆕 Recomeçar"},
                        {"id": "human", "text": "👤 Atendente"},
                    ]
                )
            ],
            next_state=ConversationState.ERROR_RECOVERY
        )
