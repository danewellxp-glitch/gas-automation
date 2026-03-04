"""
Handlers da Fase GREETING - Flow Engine 2.0
Responsáveis por boas-vindas e reconhecimento de clientes.
"""

import logging
import re
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
        
        # Detectar intenção da primeira mensagem (para fast-track)
        detected_intent = self._parse_intent(message)
        
        # Se não existe, criar contexto de cliente novo
        if not customer:
            customer_context = CustomerContext()
            conversation_context.is_returning = False
            
            # Salvar intenção detectada para uso após identificação
            if detected_intent.get("product"):
                conversation_context.collected_data["intent_product"] = detected_intent["product"]
            if detected_intent.get("operation"):
                conversation_context.collected_data["intent_operation"] = detected_intent["operation"]
            if detected_intent.get("quantity"):
                conversation_context.collected_data["intent_quantity"] = detected_intent["quantity"]
            
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
        
        # FAST-TRACK: Se o cliente conhecido já expressou intenção clara na mensagem
        # Ex: "quero trocar meu p13", "manda um gas", "preciso de botijão"
        if detected_intent.get("product"):
            from app.core.product_catalog import get_product
            product = get_product(detected_intent["product"])
            if product:
                if not order_context:
                    order_context = OrderContext()
                
                product_code = detected_intent["product"]
                operation = detected_intent.get("operation", "exchange")  # default: troca
                quantity = detected_intent.get("quantity", 1)
                
                # Calcular preço
                if operation == "sale":
                    unit_price = product.price_sale
                else:
                    unit_price = product.price_exchange
                
                total = unit_price * quantity
                order_context.items.append({
                    "product_code": product_code,
                    "quantity": quantity,
                    "unit_price": float(unit_price),
                    "subtotal": float(total),
                    "operation_type": operation,
                })
                order_context.subtotal = float(total)
                order_context.operation_type = operation
                conversation_context.collected_data["product_code"] = product_code
                conversation_context.collected_data["quantity"] = quantity
                conversation_context.collected_data["operation_type"] = operation
                
                # Se tem endereço e é retira → pagamento
                if operation == "pickup":
                    from app.core.product_catalog import STORE_ADDRESS
                    customer_type_key = "payment_methods_pj" if customer_type == "PJ" else "payment_methods_pf"
                    payment_buttons = get_quick_replies(customer_type_key)
                    return self._create_result(
                        conversation_context=conversation_context,
                        customer_context=customer_context,
                        order_context=order_context,
                        responses=[
                            self._create_response(
                                text=f"👋 Olá, {customer_context.name}!\n\n"
                                     f"✅ {quantity}x {product_code} - {self._format_currency(total)}\n\n"
                                     f"🏪 Retirada na loja: {STORE_ADDRESS}\n\n"
                                     f"💰 Como deseja pagar?",
                                buttons=payment_buttons
                            )
                        ],
                        next_state=ConversationState.CHECKOUT_PAYMENT
                    )
                
                # Se tem endereço cadastrado → confirmar endereço
                if customer_context.addresses:
                    from app.core.message_templates import CONFIRM_ADDRESS
                    address = customer_context.addresses[customer_context.default_address_idx]
                    order_context.address = address
                    return self._create_result(
                        conversation_context=conversation_context,
                        customer_context=customer_context,
                        order_context=order_context,
                        responses=[
                            self._create_response(
                                text=f"👋 Olá, {customer_context.name}!\n\n"
                                     f"✅ {quantity}x {product_code} ({operation == 'exchange' and 'Troca' or 'Compra'}) - {self._format_currency(total)}\n\n"
                                     f"📍 Entregar em: {self._format_address(address)}\n\n"
                                     f"Confirma?",
                                buttons=[
                                    {"id": "confirm_addr", "text": "✅ Sim, entregar aí"},
                                    {"id": "change_addr", "text": "✏️ Outro endereço"},
                                ]
                            )
                        ],
                        next_state=ConversationState.ORDERING_ADDRESS_CONFIRM
                    )
                
                # Sem endereço → pedir endereço
                from app.core.message_templates import ASK_ADDRESS
                return self._create_result(
                    conversation_context=conversation_context,
                    customer_context=customer_context,
                    order_context=order_context,
                    responses=[
                        self._create_response(
                            text=f"👋 Olá, {customer_context.name}!\n\n"
                                 f"✅ {quantity}x {product_code} - {self._format_currency(total)}\n\n"
                                 + ASK_ADDRESS
                        )
                    ],
                    next_state=ConversationState.ORDERING_ADDRESS
                )
        
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
    
    def _parse_intent(self, message: str) -> Dict:
        """Analisa a mensagem do cliente para extrair intenção de compra.
        
        Retorna dict com chaves opcionais: product, operation, quantity.
        
        Exemplos:
        - "quero trocar meu p13" → {product: "P13", operation: "exchange"}
        - "preciso de 2 botijões de gás" → {product: "P13", quantity: 2}
        - "manda um gas pra mim" → {product: "P13", operation: "exchange"}
        - "quero comprar botijão de 45" → {product: "P45", operation: "sale"}
        - "oi" / "olá" → {} (sem intenção detectada)
        """
        msg_lower = message.lower().strip()
        intent = {}
        
        # Ignorar saudações simples (não tentar extrair intenção)
        greetings = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
                      "hello", "hi", "menu", "inicio", "início"]
        if msg_lower in greetings:
            return intent
        
        # --- Detectar PRODUTO ---
        # Códigos diretos (P13, P20, P45)
        if re.search(r'\bp\s*13\b', msg_lower):
            intent["product"] = "P13"
        elif re.search(r'\bp\s*20\b', msg_lower):
            intent["product"] = "P20"
        elif re.search(r'\bp\s*45\b', msg_lower):
            intent["product"] = "P45"
        else:
            # Por peso
            weight_match = re.search(r'\b(13|20|45)\s*(?:kg|kilo|kilos|quilos)?\b', msg_lower)
            if weight_match:
                weight_map = {"13": "P13", "20": "P20", "45": "P45"}
                intent["product"] = weight_map.get(weight_match.group(1))
            else:
                # Palavras-chave específicas
                if any(kw in msg_lower for kw in ["grande", "industrial", "comercial"]):
                    intent["product"] = "P45"
                elif any(kw in msg_lower for kw in [
                    "gas", "gás", "botijão", "botijao", "butijão", "butijao",
                    "botija", "bujao", "bujão", "cozinha", "residencial",
                ]):
                    intent["product"] = "P13"  # Mais vendido
        
        # --- Detectar OPERAÇÃO ---
        if any(kw in msg_lower for kw in ["troca", "trocar", "troco", "vazio"]):
            intent["operation"] = "exchange"
        elif any(kw in msg_lower for kw in ["compra", "comprar", "novo", "primeira vez"]):
            intent["operation"] = "sale"
        elif any(kw in msg_lower for kw in ["retira", "retirar", "buscar", "busca", "pegar"]):
            intent["operation"] = "pickup"
        elif intent.get("product"):
            # Se mencionou produto mas não operação, default = troca
            intent["operation"] = "exchange"
        
        # --- Detectar QUANTIDADE ---
        qty_match = re.search(r'(\d+)\s*x\s', msg_lower)
        if qty_match:
            intent["quantity"] = min(int(qty_match.group(1)), 10)
        else:
            qty_match = re.search(r'(\d+)\s*(?:botij|butij|bujao|bujão|unidade)', msg_lower)
            if qty_match:
                intent["quantity"] = min(int(qty_match.group(1)), 10)
        
        return intent


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
