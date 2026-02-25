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
        # Determinar tipo de cliente baseado no CPF/CNPJ
        customer_type = "PF"
        if customer.cpf_cnpj:
            # CNPJ tem 14 dígitos, CPF tem 11
            cpf_cnpj_clean = ''.join(filter(str.isdigit, customer.cpf_cnpj))
            if len(cpf_cnpj_clean) == 14:
                customer_type = "PJ"
        
        customer_context = CustomerContext(
            customer_id=str(customer.id),
            name=customer.name,
            document=customer.cpf_cnpj,
            customer_type=customer_type,
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
        
        # Cliente conhecido - verificar último pedido (com itens)
        last_order = await self._get_last_order_with_items(customer_context.customer_id)

        if last_order:
            # Formatar itens do último pedido
            order_items = getattr(last_order, "items", []) or []
            items_list = []
            for oi in order_items:
                items_list.append({
                    "product_code": oi.product_code,
                    "quantity": oi.quantity,
                    "unit_price": float(oi.unit_price),
                    "subtotal": float(oi.subtotal),
                    "operation_type": "exchange",
                })

            customer_context.last_order = {
                "order_number": last_order.order_number,
                "total": float(last_order.total_amount),
                "items": items_list,
                "payment_method": last_order.payment_method,
                "address": last_order.delivery_address,
            }

            # Texto dos itens para o greeting
            items_text_lines = []
            for oi in order_items:
                items_text_lines.append(
                    "• {}x {} - {}".format(oi.quantity, oi.product_code, self._format_currency(oi.subtotal))
                )
            items_text = "\n".join(items_text_lines) if items_text_lines else "Pedido anterior"

            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                responses=[
                    self._create_response(
                        text=GREETING_RETURNING.format(
                            name=customer_context.name,
                            last_order_items=items_text,
                            last_order_total=self._format_currency(last_order.total_amount),
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
        
        # Verificar se tem histórico de pedido para saber qual menu foi mostrado
        # Verificar no banco, não apenas no context que pode estar vazio
        has_order_history = False
        if customer_context and customer_context.customer_id:
            # Tentar buscar último pedido do banco
            last_order = await self._get_last_order(customer_context.customer_id)
            has_order_history = last_order is not None
        elif customer_context and customer_context.last_order:
            # Fallback: verificar se tem no context
            has_order_history = True
        
        # Detectar button IDs (sempre funciona)
        if msg_lower == "repeat_order":
            if not has_order_history:
                return await self._start_new_order(conversation_context, customer_context, order_context)
            
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
        
        if msg_lower in ["new_order", "fazer_pedido", "novo"]:
            return await self._start_new_order(conversation_context, customer_context, order_context)
        
        if msg_lower in ["track_order", "ver_pedido", "rastrear", "meus pedidos"]:
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
        
        if msg_lower in ["falar_atendente", "atendente", "humano"]:
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
        
        # Detectar números baseado no menu mostrado
        if msg_lower == "1":
            if has_order_history:
                # Menu com histórico: 1 = Repetir
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
            else:
                # Menu sem histórico: 1 = Fazer Pedido
                return await self._start_new_order(conversation_context, customer_context, order_context)
        
        if msg_lower == "2":
            if has_order_history:
                # Menu com histórico: 2 = Novo Pedido
                return await self._start_new_order(conversation_context, customer_context, order_context)
            else:
                # Menu sem histórico: 2 = Meus Pedidos
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
        
        if msg_lower == "3":
            if has_order_history:
                # Menu com histórico: 3 = Rastrear
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
            else:
                # Menu sem histórico: 3 = Atendente
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
        
        # Continuar pedido abandonado
        if msg_lower == "continue_order":
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

        name = customer_context.name if customer_context else ""
        greeting = "Oi {}!\n\n".format(name) if name else ""

        sections = self._build_product_list_sections()
        product_text = self._build_product_text()

        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="{}🛒 Qual botijão você precisa?\n\n{}".format(greeting, product_text),
                    list_sections=sections,
                    list_button_text="Ver Produtos",
                )
            ],
            next_state=ConversationState.ORDERING_PRODUCT
        )
