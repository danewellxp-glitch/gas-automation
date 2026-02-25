"""
Handlers da Fase ORDERING - Flow Engine 2.0
Responsáveis por seleção de produtos e configuração do pedido.
"""

import logging
import re
from typing import Optional, Dict
from decimal import Decimal

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)
from app.core.handlers_v2.base import BaseHandler, HandlerResult, MessageResponse
from app.core.product_catalog import (
    get_active_products,
    get_product,
    is_area_covered,
    get_coverage_area,
)
from app.core.message_templates import (
    ASK_PRODUCT,
    PRODUCT_SELECTED,
    ASK_QUANTITY,
    ASK_OPERATION_TYPE,
    ASK_MORE_ITEMS,
    ASK_ADDRESS,
    CONFIRM_ADDRESS,
    ADDRESS_OUT_OF_AREA,
    ASK_COMPLEMENT,
)
from app.core.flow_config import get_quick_replies

logger = logging.getLogger(__name__)


class OrderingProductHandler(BaseHandler):
    """Handler para ORDERING_PRODUCT - Seleção de produto."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa seleção de produto."""
        
        # Extrair código do produto
        product_code = self._extract_product_code(message, entities)
        
        if not product_code:
            # Não entendeu - incrementar retry
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
            
            # Mostrar produtos disponíveis com List Message
            sections = self._build_product_list_sections()
            product_text = self._build_product_text()

            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="🤔 Não entendi. Por favor, escolha um produto:\n\n{}".format(product_text),
                        list_sections=sections,
                        list_button_text="Ver Produtos",
                    )
                ],
                next_state=ConversationState.ORDERING_PRODUCT
            )
        
        # Buscar produto
        product = get_product(product_code)
        if not product or not product.is_active:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text=f"❌ Produto {product_code} não disponível no momento."
                    )
                ],
                next_state=ConversationState.ORDERING_PRODUCT
            )
        
        # Criar ou atualizar contexto do pedido
        if not order_context:
            order_context = OrderContext()
        
        # Salvar produto selecionado
        conversation_context.collected_data["product_code"] = product_code
        self._reset_retry(conversation_context)
        
        # Ir para quantidade
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text=PRODUCT_SELECTED.format(
                        product_name=product.name,
                        unit_price=self._format_currency(product.price_exchange)
                    ),
                    buttons=[
                        {"id": "qty_1", "text": "1 botijão"},
                        {"id": "qty_2", "text": "2 botijões"},
                        {"id": "qty_3", "text": "3 botijões"},
                    ]
                )
            ],
            next_state=ConversationState.ORDERING_QUANTITY
        )
    
    def _extract_product_code(self, message: str, entities: Optional[Dict]) -> Optional[str]:
        """Extrai código do produto da mensagem ou entidades."""
        
        # Tentar das entidades primeiro
        if entities and entities.get("product"):
            return entities["product"].upper()
        
        msg_upper = message.upper().strip()
        
        # Códigos diretos
        if "P13" in msg_upper:
            return "P13"
        if "P20" in msg_upper:
            return "P20"
        if "P45" in msg_upper:
            return "P45"
        
        # Por número de opção
        option_map = {"1": "P13", "2": "P20", "3": "P45"}
        if message.strip() in option_map:
            return option_map[message.strip()]
        
        return None


class OrderingQuantityHandler(BaseHandler):
    """Handler para ORDERING_QUANTITY - Define quantidade."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa quantidade."""
        
        # Extrair quantidade
        quantity = self._extract_quantity(message, entities)
        
        if not quantity or quantity < 1 or quantity > 10:
            self._increment_retry(conversation_context)
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Por favor, informe uma quantidade entre 1 e 10 botijões.",
                        buttons=[
                            {"id": "qty_1", "text": "1"},
                            {"id": "qty_2", "text": "2"},
                            {"id": "qty_3", "text": "3"},
                        ]
                    )
                ],
                next_state=ConversationState.ORDERING_QUANTITY
            )
        
        # Salvar quantidade
        conversation_context.collected_data["quantity"] = quantity
        self._reset_retry(conversation_context)
        
        # Ir para tipo de operação
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
                responses=[
                    self._create_response(
                        text=ASK_OPERATION_TYPE,
                        buttons=[
                            {"id": "exchange", "text": "1. 🔄 Troca"},
                            {"id": "sale", "text": "2. 🆕 Comprar"},
                            {"id": "pickup", "text": "3. 🏪 Retira"},
                        ]
                    )
                ],
                next_state=ConversationState.ORDERING_OPERATION
        )
    
    def _extract_quantity(self, message: str, entities: Optional[Dict]) -> Optional[int]:
        """Extrai quantidade da mensagem."""
        
        # Tentar das entidades
        if entities and entities.get("quantity"):
            return entities["quantity"]
        
        # Botões qty_N
        if message.startswith("qty_"):
            try:
                return int(message.replace("qty_", ""))
            except ValueError:
                pass
        
        # Números na mensagem
        numbers = re.findall(r'\d+', message)
        if numbers:
            qty = int(numbers[0])
            if 1 <= qty <= 10:
                return qty
        
        return None


class OrderingOperationHandler(BaseHandler):
    """Handler para ORDERING_OPERATION - Tipo de operação (Troca/Venda/Retira)."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa tipo de operação."""
        
        msg_lower = message.lower().strip()
        
        # Detectar tipo de operação (aceitar número 1, 2, 3 ou texto)
        operation_type = None
        if msg_lower == "1" or any(word in msg_lower for word in ["troca", "trocar", "exchange"]):
            operation_type = "exchange"
        elif msg_lower == "2" or any(word in msg_lower for word in ["venda", "comprar", "sale", "novo"]):
            operation_type = "sale"
        elif msg_lower == "3" or any(word in msg_lower for word in ["retira", "retirar", "pickup", "buscar"]):
            operation_type = "pickup"
        
        if not operation_type:
            self._increment_retry(conversation_context)
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Por favor, escolha o tipo de operação (pode digitar 1, 2 ou 3):",
                        buttons=[
                            {"id": "exchange", "text": "1. 🔄 Troca"},
                            {"id": "sale", "text": "2. 🆕 Comprar"},
                            {"id": "pickup", "text": "3. 🏪 Retira"},
                        ]
                    )
                ],
                next_state=ConversationState.ORDERING_OPERATION
            )
        
        # Salvar operação
        if not order_context:
            order_context = OrderContext()
        
        order_context.operation_type = operation_type
        conversation_context.collected_data["operation_type"] = operation_type
        self._reset_retry(conversation_context)
        
        # Calcular preço baseado na operação
        product_code = conversation_context.collected_data.get("product_code")
        quantity = conversation_context.collected_data.get("quantity", 1)
        
        if product_code:
            product = get_product(product_code)
            if product:
                if operation_type == "sale":
                    unit_price = product.price_sale
                else:
                    unit_price = product.price_exchange
                
                total = unit_price * quantity
                # Mesclar com item existente do mesmo produto/operação em vez de duplicar linha
                existing = next(
                    (it for it in order_context.items if it.get("product_code") == product_code and it.get("operation_type") == operation_type),
                    None
                )
                if existing:
                    existing["quantity"] = existing["quantity"] + quantity
                    existing["subtotal"] = existing["subtotal"] + float(total)
                else:
                    order_context.items.append({
                        "product_code": product_code,
                        "quantity": quantity,
                        "unit_price": float(unit_price),
                        "subtotal": float(total),
                        "operation_type": operation_type,
                    })
                order_context.subtotal = sum(it.get("subtotal", 0) for it in order_context.items)
        
        # Perguntar se quer adicionar mais
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
                responses=[
                    self._create_response(
                        text=ASK_MORE_ITEMS,
                        buttons=[
                            {"id": "add_more", "text": "1. ➕ Sim, adicionar"},
                            {"id": "finalize", "text": "2. ✅ Finalizar"},
                        ]
                    )
                ],
                next_state=ConversationState.ORDERING_MORE_ITEMS
            )


class OrderingMoreItemsHandler(BaseHandler):
    """Handler para ORDERING_MORE_ITEMS - Pergunta se quer adicionar mais."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa resposta sobre adicionar mais itens."""
        
        msg_lower = message.lower().strip()
        
        # Adicionar mais (aceitar 1 ou texto)
        if msg_lower in ["add_more", "sim", "s", "adicionar", "mais", "1"]:
            # Limpar dados do produto anterior
            conversation_context.collected_data.pop("product_code", None)
            conversation_context.collected_data.pop("quantity", None)
            
            # Voltar para seleção de produto com List Message
            sections = self._build_product_list_sections()
            product_text = self._build_product_text()

            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="🛒 Qual outro produto?\n\n{}".format(product_text),
                        list_sections=sections,
                        list_button_text="Ver Produtos",
                    )
                ],
                next_state=ConversationState.ORDERING_PRODUCT
            )
        
        # Finalizar (aceitar 2 ou "finalizar"/"não" para ir direto ao endereço)
        if msg_lower in ["finalize", "finalizar", "não", "nao", "n", "2"]:
            if not order_context:
                order_context = OrderContext()
            
            # Verificar se é retira (sem entrega)
            operation_type = order_context.operation_type
            
            if operation_type == "pickup":
                # Retira na loja - pular endereço, ir direto para pagamento
                return self._create_result(
                    conversation_context=conversation_context,
                    customer_context=customer_context,
                    order_context=order_context,
                    responses=[
                        self._create_response(
                            text=f"🏪 Retirada na loja!\n\nEndereço: Rua Principal, 1000 - Boqueirão\n\nComo deseja pagar?"
                        )
                    ],
                    next_state=ConversationState.CHECKOUT_PAYMENT
                )
            
            # Entrega - precisa de endereço
            # Verificar se cliente tem endereço cadastrado
            if customer_context and customer_context.addresses:
                address = customer_context.addresses[customer_context.default_address_idx]
                order_context.address = address
                
                return self._create_result(
                    conversation_context=conversation_context,
                    customer_context=customer_context,
                    order_context=order_context,
                    responses=[
                        self._create_response(
                            text=CONFIRM_ADDRESS.format(
                                formatted_address=self._format_address(address)
                            ),
                            buttons=[
                                {"id": "confirm_addr", "text": "✅ Sim"},
                                {"id": "change_addr", "text": "✏️ Alterar"},
                            ]
                        )
                    ],
                    next_state=ConversationState.ORDERING_ADDRESS_CONFIRM
                )
            
            # Não tem endereço - pedir
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=ASK_ADDRESS)
                ],
                next_state=ConversationState.ORDERING_ADDRESS
            )
        
        # Não entendeu
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="Escolha uma opção:",
                    buttons=[
                        {"id": "add_more", "text": "1. ➕ Sim, adicionar"},
                        {"id": "finalize", "text": "2. ✅ Finalizar"},
                    ]
                )
            ],
            next_state=ConversationState.ORDERING_MORE_ITEMS
        )


class OrderingAddressHandler(BaseHandler):
    """Handler para ORDERING_ADDRESS - Coleta endereço de entrega."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa endereço."""
        
        # Extrair endereço e complemento da mesma mensagem (primeira linha = endereço, segunda = complemento opcional)
        raw = message.strip()
        if "\n" in raw:
            parts = raw.split("\n", 1)
            address_line = parts[0].strip()
            complement_line = parts[1].strip() if len(parts) > 1 else None
        else:
            address_line = raw
            complement_line = None
        
        # Validar endereço mínimo
        if len(address_line) < 10:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="❌ Endereço muito curto.\n\nPor favor, informe:\nRua, número e bairro.\n\n_Exemplo: Rua das Flores, 123 - Boqueirão_"
                    )
                ],
                next_state=ConversationState.ORDERING_ADDRESS
            )
        
        # Extrair bairro
        bairro = None
        if entities and entities.get("bairro"):
            bairro = entities["bairro"]
        else:
            # Tentar extrair do texto (usar address_line)
            from app.core.product_catalog import COVERAGE_AREAS
            for b in COVERAGE_AREAS.keys():
                if b.lower() in address_line.lower():
                    bairro = b
                    break
        
        # Validar área de cobertura
        if bairro and not is_area_covered(bairro):
            # Bairro fora da área
            from app.core.product_catalog import COVERAGE_AREAS, STORE_ADDRESS
            covered_list = "\n".join([f"• {b}" for b in COVERAGE_AREAS.keys()])
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text=ADDRESS_OUT_OF_AREA.format(
                            bairro=bairro,
                            covered_areas=covered_list,
                            store_address=STORE_ADDRESS
                        ),
                        buttons=[
                            {"id": "pickup", "text": "🏪 Retirar na loja"},
                            {"id": "other_address", "text": "📍 Outro endereço"},
                        ]
                    )
                ],
                next_state=ConversationState.ORDERING_ADDRESS
            )
        
        # Salvar endereço e complemento
        if not order_context:
            order_context = OrderContext()
        
        address = {
            "full_address": address_line,
            "bairro": bairro,
        }
        
        order_context.address = address
        conversation_context.collected_data["address"] = address
        
        if complement_line and len(complement_line) > 0:
            order_context.complement = complement_line[:200]
            conversation_context.collected_data["complement"] = complement_line[:200]
        
        # Calcular taxa de entrega
        if bairro:
            area = get_coverage_area(bairro)
            if area:
                order_context.delivery_fee = float(area.delivery_fee)
        
        # Confirmar endereço
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text=CONFIRM_ADDRESS.format(
                        formatted_address=self._format_address(address)
                    ),
                    buttons=[
                        {"id": "confirm_addr", "text": "✅ Sim, correto"},
                        {"id": "change_addr", "text": "✏️ Alterar"},
                    ]
                )
            ],
            next_state=ConversationState.ORDERING_ADDRESS_CONFIRM
        )


class OrderingAddressConfirmHandler(BaseHandler):
    """Handler para ORDERING_ADDRESS_CONFIRM - Confirma endereço."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa confirmação de endereço."""
        
        msg_lower = message.lower().strip()
        
        # Confirmar (aceitar 1 ou texto; depois ir direto para pagamento com opções)
        if msg_lower in ["confirm_addr", "sim", "s", "correto", "confirmar", "1"]:
            # Salvar endereço no cliente
            if customer_context and order_context and order_context.address:
                if not customer_context.addresses:
                    customer_context.addresses = []
                
                # Adicionar se não existe
                if order_context.address not in customer_context.addresses:
                    customer_context.addresses.append(order_context.address)
                
                # Salvar no banco
                customer = await self._get_customer_by_phone(conversation_context.phone)
                if customer:
                    from app.database import AsyncSessionLocal
                    async with AsyncSessionLocal() as db:
                        customer.address = order_context.address
                        await db.commit()
            
            # Ir direto para pagamento (só botões, sem duplicar lista no texto)
            customer_type = customer_context.customer_type if customer_context else "PF"
            buttons_key = "payment_methods_pj" if customer_type == "PJ" else "payment_methods_pf"
            payment_buttons = get_quick_replies(buttons_key)
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="✅ Endereço registrado!\n\n💰 Como deseja pagar? (pode digitar 1, 2 ou 3)",
                        buttons=payment_buttons
                    )
                ],
                next_state=ConversationState.CHECKOUT_PAYMENT
            )
        
        # Alterar (aceitar 2 ou texto)
        if msg_lower in ["change_addr", "não", "nao", "n", "alterar", "2"]:
            # Limpar endereço
            if order_context:
                order_context.address = None
            conversation_context.collected_data.pop("address", None)
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=ASK_ADDRESS)
                ],
                next_state=ConversationState.ORDERING_ADDRESS
            )
        
        # Não entendeu
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="Por favor, confirme o endereço:",
                    buttons=[
                        {"id": "confirm_addr", "text": "✅ Sim"},
                        {"id": "change_addr", "text": "✏️ Alterar"},
                    ]
                )
            ],
            next_state=ConversationState.ORDERING_ADDRESS_CONFIRM
        )


class OrderingComplementHandler(BaseHandler):
    """Handler para ORDERING_COMPLEMENT - Coleta complemento."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa complemento."""
        
        complement = message.strip()
        
        # Permitir pular (opcional)
        if complement.lower() in ["não", "nao", "n", "sem", "pular", "skip"]:
            complement = None
        
        # Salvar complemento
        if complement and len(complement) > 0:
            if not order_context:
                order_context = OrderContext()
            
            order_context.complement = complement[:200]  # Limite
            conversation_context.collected_data["complement"] = complement[:200]
        
        # Ir para pagamento (só botões)
        customer_type = customer_context.customer_type if customer_context else "PF"
        buttons_key = "payment_methods_pj" if customer_type == "PJ" else "payment_methods_pf"
        payment_buttons = get_quick_replies(buttons_key)
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="✅ Endereço registrado!\n\n💰 Como deseja pagar? (pode digitar 1, 2 ou 3)",
                    buttons=payment_buttons
                )
            ],
            next_state=ConversationState.CHECKOUT_PAYMENT
        )


class OrderingConfirmRepeatHandler(BaseHandler):
    """Handler para ORDERING_CONFIRM_REPEAT - Confirma repetição de pedido."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa confirmação de repetir pedido."""
        
        msg_lower = message.lower().strip()
        
        # Confirmar repetição
        if msg_lower in ["confirm_repeat", "sim", "s", "confirmar", "repetir"]:
            # Carregar dados do último pedido
            if not customer_context or not customer_context.last_order:
                return self._create_result(
                    conversation_context=conversation_context,
                    customer_context=customer_context,
                    order_context=order_context,
                    responses=[
                        self._create_response(
                            text="Não encontrei seu último pedido.\n\nVamos fazer um novo?"
                        )
                    ],
                    next_state=ConversationState.ORDERING_PRODUCT
                )

            # Criar contexto do pedido com dados do último
            if not order_context:
                order_context = OrderContext()

            last_order = customer_context.last_order

            # Copiar itens
            order_context.items = last_order.get("items", [])
            order_context.subtotal = last_order.get("total", 0.0)

            # Copiar endereço se disponível
            if last_order.get("address"):
                order_context.address = last_order["address"]
            elif customer_context.addresses:
                order_context.address = customer_context.addresses[customer_context.default_address_idx]

            # Copiar pagamento anterior se disponível
            if last_order.get("payment_method"):
                order_context.payment_method = last_order["payment_method"]

            # Se temos tudo (itens + endereço + pagamento), ir direto para summary
            if order_context.items and order_context.address and order_context.payment_method:
                # Calcular total
                order_context.total = float(order_context.subtotal)
                if order_context.delivery_fee:
                    order_context.total += order_context.delivery_fee

                from app.core.message_templates import ORDER_SUMMARY
                from app.core.product_catalog import get_coverage_area

                items_text = []
                for item in order_context.items:
                    qty = item.get("quantity", 1)
                    code = item.get("product_code", "")
                    subtotal = Decimal(str(item.get("subtotal", 0)))
                    items_text.append("• {}x {} - {}".format(qty, code, self._format_currency(subtotal)))
                items_summary = "\n".join(items_text)
                address_text = self._format_address(order_context.address)
                payment_labels = {
                    "cash": "Dinheiro", "credit_card": "Cartao",
                    "pix": "PIX", "invoice": "Faturado",
                }
                payment_text = payment_labels.get(order_context.payment_method, order_context.payment_method or "")
                delivery_estimate = "30-60 min"
                if order_context.address and order_context.address.get("bairro"):
                    area = get_coverage_area(order_context.address["bairro"])
                    if area:
                        delivery_estimate = "{}-{} min".format(area.delivery_time_min, area.delivery_time_max)

                summary_text = ORDER_SUMMARY.format(
                    customer_name=customer_context.name if customer_context else "Cliente",
                    address=address_text,
                    items=items_summary,
                    total=self._format_currency(Decimal(str(order_context.subtotal))),
                    payment_method=payment_text,
                    delivery_estimate=delivery_estimate,
                )

                return self._create_result(
                    conversation_context=conversation_context,
                    customer_context=customer_context,
                    order_context=order_context,
                    responses=[
                        self._create_response(
                            text="🔄 Repetindo seu último pedido!\n\n" + summary_text,
                            buttons=[
                                {"id": "confirm", "text": "✅ Confirmar"},
                                {"id": "edit", "text": "✏️ Alterar"},
                                {"id": "cancel", "text": "❌ Cancelar"},
                            ]
                        )
                    ],
                    next_state=ConversationState.CHECKOUT_SUMMARY
                )

            # Se falta pagamento, pedir
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="🔄 Repetindo seu último pedido!\n\n💰 Como deseja pagar?"
                    )
                ],
                next_state=ConversationState.CHECKOUT_PAYMENT
            )
        
        # Alterar pedido
        if msg_lower in ["change_repeat", "não", "nao", "n", "alterar"]:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Vamos fazer um novo pedido então!\n\n🛒 Qual produto?"
                    )
                ],
                next_state=ConversationState.ORDERING_PRODUCT
            )
        
        # Não entendeu
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="Deseja repetir o último pedido?",
                    buttons=[
                        {"id": "confirm_repeat", "text": "✅ Sim"},
                        {"id": "change_repeat", "text": "🛒 Novo Pedido"},
                    ]
                )
            ],
            next_state=ConversationState.ORDERING_CONFIRM_REPEAT
        )
