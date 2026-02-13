"""
Handlers da Fase GREETING - Flow Engine 2.0
Responsáveis por boas-vindas e reconhecimento de clientes.
"""

import logging
from typing import Optional, Dict

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)
from app.core.handlers_v2.base import BaseHandler, HandlerResult, MessageResponse
from app.core.message_templates import (
    GREETING_NEW,
    GREETING_RETURNING,
    GREETING_RETURNING_NO_HISTORY,
    GREETING_ABANDONED_ORDER,
)
from app.core.flow_config import get_quick_replies

logger = logging.getLogger(__name__)


class GreetingInitialHandler(BaseHandler):
    """
    Handler para GREETING_INITIAL.
    
    Estado inicial - primeira mensagem do cliente.
    
    Fluxo:
    - Cliente conhecido → GREETING_RETURNING
    - Cliente novo → IDENTIFY_TYPE
    - Intenção clara com dados → ORDERING_PRODUCT (fast-track)
    - "falar com atendente" → SUPPORT_HUMAN
    - "rastrear pedido" → TRACKING_STATUS
    """
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa saudação inicial."""
        
        # Buscar ou criar cliente
        customer = await self._get_customer_by_phone(conversation_context.phone)
        
        # Se não existe, criar contexto de cliente novo
        if not customer:
            customer_context = CustomerContext()
            conversation_context.is_returning = False
            
            # Cliente novo - perguntar tipo (PF/PJ)
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                responses=[
                    self._create_response(
                        text=GREETING_NEW,
                        buttons=get_quick_replies("customer_type")
                    )
                ],
                next_state=ConversationState.IDENTIFY_TYPE
            )
        
        # Cliente conhecido - criar contexto do cliente
        customer_context = CustomerContext(
            customer_id=str(customer.id),
            name=customer.name,
            document=customer.cpf_cnpj,
            customer_type=customer.tipo_documento or "PF",
            addresses=[customer.address] if customer.address else [],
            order_count=0,  # TODO: buscar do banco
        )
        
        conversation_context.is_returning = True
        
        # Verificar se tem pedido abandonado
        if conversation_context.resumed_from_snapshot:
            return await self._handle_abandoned_order(
                conversation_context,
                customer_context,
                order_context
            )
        
        # Cliente conhecido - verificar último pedido
        last_order = await self._get_last_order(customer_context.customer_id)
        
        if last_order:
            # Tem histórico - oferecer repetir
            customer_context.last_order = {
                "order_number": last_order.order_number,
                "total": float(last_order.total_amount),
                "items": [],  # TODO: buscar itens
            }
            
            last_order_summary = f"{last_order.order_number} - {self._format_currency(last_order.total_amount)}"
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                responses=[
                    self._create_response(
                        text=GREETING_RETURNING.format(
                            name=customer_context.name,
                            last_order_summary=last_order_summary
                        ),
                        buttons=[
                            {"id": "repeat_order", "text": "🔄 Repetir"},
                            {"id": "new_order", "text": "🛒 Novo Pedido"},
                            {"id": "track_order", "text": "📦 Rastrear"},
                        ]
                    )
                ],
                next_state=ConversationState.GREETING_RETURNING
            )
        
        # Cliente conhecido sem histórico
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            responses=[
                self._create_response(
                    text=GREETING_RETURNING_NO_HISTORY.format(
                        name=customer_context.name
                    ),
                    buttons=get_quick_replies("main_menu")
                )
            ],
            next_state=ConversationState.GREETING_RETURNING
        )
    
    async def _handle_abandoned_order(
        self,
        conversation_context: ConversationContext,
        customer_context: CustomerContext,
        order_context: Optional[OrderContext],
    ) -> HandlerResult:
        """Trata recuperação de pedido abandonado."""
        
        # Mapear estado para descrição amigável
        state_labels = {
            ConversationState.ORDERING_PRODUCT: "escolhendo o produto",
            ConversationState.ORDERING_QUANTITY: "informando a quantidade",
            ConversationState.ORDERING_ADDRESS: "informando o endereço",
            ConversationState.CHECKOUT_PAYMENT: "escolhendo a forma de pagamento",
        }
        
        stage = state_labels.get(
            conversation_context.current_state,
            "fazendo seu pedido"
        )
        
        name = customer_context.name or ""
        greeting = f"Oi {name}! " if name else "Oi! "
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text=GREETING_ABANDONED_ORDER.format(
                        name=name,
                        stage=stage
                    ),
                    buttons=[
                        {"id": "continue_order", "text": "✅ Continuar"},
                        {"id": "new_order", "text": "🔄 Novo Pedido"},
                    ]
                )
            ],
            next_state=conversation_context.current_state  # Manter no estado recuperado
        )


class GreetingReturningHandler(BaseHandler):
    """
    Handler para GREETING_RETURNING.
    
    Cliente conhecido retornando.
    
    Fluxo:
    - Repetir pedido → ORDERING_CONFIRM_REPEAT
    - Novo pedido → ORDERING_PRODUCT
    - Continuar abandonado → Estado onde parou
    - Rastrear → TRACKING_STATUS
    """
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa escolha do cliente conhecido."""
        
        msg_lower = message.lower().strip()
        
        # Repetir pedido
        if msg_lower in ["repeat_order", "repetir", "o de sempre"]:
            if not customer_context or not customer_context.last_order:
                # Não tem pedido anterior - ir para novo pedido
                return await self._start_new_order(
                    conversation_context,
                    customer_context,
                    order_context
                )
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="🔄 Vou repetir seu último pedido!\n\nConfirma?",
                        buttons=[
                            {"id": "confirm_repeat", "text": "✅ Confirmar"},
                            {"id": "change_repeat", "text": "✏️ Alterar"},
                        ]
                    )
                ],
                next_state=ConversationState.ORDERING_CONFIRM_REPEAT
            )
        
        # Novo pedido
        if msg_lower in ["new_order", "novo", "fazer_pedido"]:
            return await self._start_new_order(
                conversation_context,
                customer_context,
                order_context
            )
        
        # Rastrear pedido
        if msg_lower in ["track_order", "rastrear", "ver_pedido"]:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="📦 Buscando seus pedidos..."
                    )
                ],
                next_state=ConversationState.TRACKING_STATUS
            )
        
        # Continuar pedido abandonado
        if msg_lower == "continue_order":
            # Retornar ao estado onde estava
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="✅ Continuando de onde você parou..."
                    )
                ],
                next_state=conversation_context.current_state
            )
        
        # Não entendeu - oferecer opções novamente
        self._increment_retry(conversation_context)
        
        if self._should_escalate_to_human(conversation_context):
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Vou te conectar com um atendente."
                    )
                ],
                next_state=ConversationState.SUPPORT_HUMAN,
                needs_human=True
            )
        
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
            next_state=ConversationState.GREETING_RETURNING
        )
    
    async def _start_new_order(
        self,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext],
        order_context: Optional[OrderContext],
    ) -> HandlerResult:
        """Inicia novo pedido."""
        
        # Criar novo contexto de pedido
        if not order_context:
            order_context = OrderContext()
        
        # Buscar produtos ativos
        from app.core.product_catalog import get_active_products
        products = get_active_products()
        
        # Criar botões de produtos
        product_buttons = []
        product_text_lines = []
        
        for product in products:
            product_buttons.append({
                "id": product.code,
                "text": f"{product.emoji} {product.code} - {self._format_currency(product.price_exchange)}"
            })
            label = f" {getattr(product, 'usage_label', '')}" if getattr(product, 'usage_label', None) else ""
            product_text_lines.append(
                f"{product.emoji} *{product.code}* ({product.weight_kg}kg){label} - {self._format_currency(product.price_exchange)}"
            )
        
        product_text = "\n".join(product_text_lines)
        
        name = customer_context.name if customer_context else ""
        greeting = f"Oi {name}!\n\n" if name else "Olá!\n\n"
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text=f"{greeting}🛒 Qual botijão você precisa?\n\n{product_text}",
                    buttons=product_buttons[:3]  # Máximo 3 botões
                )
            ],
            next_state=ConversationState.ORDERING_PRODUCT
        )
