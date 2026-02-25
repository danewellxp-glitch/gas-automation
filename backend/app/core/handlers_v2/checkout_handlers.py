"""
Handlers da Fase CHECKOUT - Flow Engine 2.0
Responsáveis por pagamento e finalização do pedido.
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
from app.core.product_catalog import get_payment_methods_for_customer, PAYMENT_METHODS, get_coverage_area
from app.core.message_templates import (
    ASK_PAYMENT,
    ASK_CHANGE,
    ORDER_SUMMARY,
    ORDER_CONFIRMED,
    PAYMENT_PIX_INFO,
)
from app.core.flow_config import get_quick_replies, CONTACT_INFO

logger = logging.getLogger(__name__)


class CheckoutPaymentHandler(BaseHandler):
    """Handler para CHECKOUT_PAYMENT - Seleção de pagamento."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa seleção de pagamento."""
        
        msg_lower = message.lower().strip()
        
        # Determinar métodos disponíveis (para mostrar opções e aceitar 1, 2, 3, 4)
        customer_type = customer_context.customer_type if customer_context else "PF"
        buttons_key = "payment_methods_pj" if customer_type == "PJ" else "payment_methods_pf"
        payment_buttons = get_quick_replies(buttons_key)
        
        # Detectar método de pagamento (aceitar número 1, 2, 3, 4 ou texto)
        payment_method = None
        if msg_lower == "1" or any(word in msg_lower for word in ["dinheiro", "cash"]):
            payment_method = "cash"
        elif msg_lower == "2" or any(word in msg_lower for word in ["credito", "crédito", "credit", "cartao", "cartão"]):
            payment_method = "credit_card"
        elif msg_lower == "3" or "pix" in msg_lower:
            payment_method = "pix"
        elif msg_lower == "4" or any(word in msg_lower for word in ["boleto", "faturado", "invoice"]):
            payment_method = "invoice"  # PJ tem botão 4 = Faturado
        elif any(word in msg_lower for word in ["debito", "débito", "debit"]):
            payment_method = "debit_card"
        
        if not payment_method:
            self._increment_retry(conversation_context)
            
            # Calcular total
            total = Decimal("0.00")
            if order_context and order_context.items:
                total = Decimal(str(order_context.subtotal))
                if order_context.delivery_fee:
                    total += Decimal(str(order_context.delivery_fee))
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text=ASK_PAYMENT.format(total=self._format_currency(total)) + "\n\n_(pode digitar 1, 2 ou 3)_",
                        buttons=payment_buttons
                    )
                ],
                next_state=ConversationState.CHECKOUT_PAYMENT
            )
        
        # Validar método para tipo de cliente
        customer_type = customer_context.customer_type if customer_context else "PF"
        payment_config = PAYMENT_METHODS.get(payment_method)
        
        if payment_config and customer_type.lower() not in payment_config.available_for:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text=f"❌ {payment_config.name} não disponível para {customer_type}.\n\nEscolha outro método:"
                    )
                ],
                next_state=ConversationState.CHECKOUT_PAYMENT
            )
        
        # Salvar método de pagamento
        if not order_context:
            order_context = OrderContext()
        
        order_context.payment_method = payment_method
        conversation_context.collected_data["payment_method"] = payment_method
        self._reset_retry(conversation_context)
        
        # Se for dinheiro, perguntar troco
        if payment_method == "cash":
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text=ASK_CHANGE,
                        buttons=[
                            {"id": "no_change", "text": "Não precisa"},
                            {"id": "change_50", "text": "R$ 50"},
                            {"id": "change_100", "text": "R$ 100"},
                        ]
                    )
                ],
                next_state=ConversationState.CHECKOUT_CHANGE
            )
        
        # Montar resumo (itens, endereço, total, previsão) para enviar após pagamento
        if not order_context or not order_context.items:
            payment_label = payment_config.name if payment_config else payment_method
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[self._create_response(text=f"✅ Pagamento: {payment_label}")],
                next_state=ConversationState.CHECKOUT_SUMMARY
            )
        items_text = []
        for item in order_context.items:
            qty = item.get("quantity", 1)
            code = item.get("product_code", "")
            subtotal = Decimal(str(item.get("subtotal", 0)))
            items_text.append(f"• {qty}x {code} - {self._format_currency(subtotal)}")
        items_summary = "\n".join(items_text)
        total = Decimal(str(order_context.subtotal))
        if order_context.delivery_fee:
            total += Decimal(str(order_context.delivery_fee))
        order_context.total = float(total)
        address_text = self._format_address(order_context.address) if order_context.address else "Retirada na loja"
        payment_labels = {
            "cash": "💵 Dinheiro",
            "credit_card": "💳 Cartão de Crédito",
            "debit_card": "💳 Cartão de Débito",
            "pix": "📱 PIX",
            "invoice": "📄 Faturado",
        }
        payment_text = payment_labels.get(payment_method, payment_method or "")
        if payment_method == "cash" and order_context.change_for:
            payment_text += f" (troco p/ R$ {order_context.change_for:.2f})".replace(".", ",")
        delivery_estimate = "30-60 min"
        if order_context.address and order_context.address.get("bairro"):
            area = get_coverage_area(order_context.address["bairro"])
            if area:
                delivery_estimate = f"{area.delivery_time_min}-{area.delivery_time_max} min"
        summary_text = ORDER_SUMMARY.format(
            customer_name=customer_context.name if customer_context else "Cliente",
            address=address_text,
            items=items_summary,
            total=self._format_currency(total),
            payment_method=payment_text,
            delivery_estimate=delivery_estimate,
        )
        summary_response = self._create_response(
            text=summary_text,
            buttons=[
                {"id": "confirm", "text": "✅ Confirmar"},
                {"id": "edit", "text": "✏️ Alterar"},
                {"id": "cancel", "text": "❌ Cancelar"},
            ]
        )
        
        # Se for PIX, mostrar informações do PIX e depois resumo
        if payment_method == "pix":
            pix_info_text = PAYMENT_PIX_INFO.format(pix_key=CONTACT_INFO["pix_key"])
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=pix_info_text),
                    summary_response,
                ],
                next_state=ConversationState.CHECKOUT_SUMMARY
            )
        
        # Cartão, débito, faturado: confirmar pagamento e mostrar resumo (doc: → Outros → CHECKOUT_SUMMARY)
        payment_label = payment_config.name if payment_config else payment_method
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(text=f"✅ Pagamento: {payment_label}"),
                summary_response,
            ],
            next_state=ConversationState.CHECKOUT_SUMMARY
        )


class CheckoutChangeHandler(BaseHandler):
    """Handler para CHECKOUT_CHANGE - Pergunta troco."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa valor do troco."""
        
        msg_lower = message.lower().strip()
        
        # Não precisa de troco
        if msg_lower in ["no_change", "não", "nao", "n", "sem", "1"]:
            if not order_context:
                order_context = OrderContext()
            
            order_context.change_for = None
            
            # Mostrar resumo em seguida
            items_text = []
            for item in order_context.items:
                qty = item.get("quantity", 1)
                code = item.get("product_code", "")
                subtotal = Decimal(str(item.get("subtotal", 0)))
                items_text.append(f"• {qty}x {code} - {self._format_currency(subtotal)}")
            items_summary = "\n".join(items_text)
            total = Decimal(str(order_context.subtotal))
            if order_context.delivery_fee:
                total += Decimal(str(order_context.delivery_fee))
            order_context.total = float(total)
            address_text = self._format_address(order_context.address) if order_context.address else "Retirada na loja"
            payment_labels = {
                "cash": "💵 Dinheiro",
                "credit_card": "💳 Cartão de Crédito",
                "debit_card": "💳 Cartão de Débito",
                "pix": "📱 PIX",
                "invoice": "📄 Faturado",
            }
            payment_text = payment_labels.get(order_context.payment_method, order_context.payment_method or "")
            delivery_estimate = "30-60 min"
            if order_context.address and order_context.address.get("bairro"):
                area = get_coverage_area(order_context.address["bairro"])
                if area:
                    delivery_estimate = f"{area.delivery_time_min}-{area.delivery_time_max} min"
            summary_text = ORDER_SUMMARY.format(
                customer_name=customer_context.name if customer_context else "Cliente",
                address=address_text,
                items=items_summary,
                total=self._format_currency(total),
                payment_method=payment_text,
                delivery_estimate=delivery_estimate,
            )
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text="✅ Sem troco!"),
                    self._create_response(
                        text=summary_text,
                        buttons=[
                            {"id": "confirm", "text": "✅ Confirmar"},
                            {"id": "edit", "text": "✏️ Alterar"},
                            {"id": "cancel", "text": "❌ Cancelar"},
                        ]
                    ),
                ],
                next_state=ConversationState.CHECKOUT_SUMMARY
            )
        
        # Extrair valor do troco
        change_value = None
        
        # Botões change_N
        if msg_lower.startswith("change_"):
            try:
                change_value = float(msg_lower.replace("change_", ""))
            except ValueError:
                pass
        
        # Extrair da mensagem
        if not change_value:
            if entities and entities.get("change_for"):
                change_value = entities["change_for"]
            else:
                # Procurar por números
                numbers = re.findall(r'\d+', message)
                if numbers:
                    change_value = float(numbers[0])
        
        if not change_value or change_value < 0:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Por favor, informe o valor para o troco:",
                        buttons=[
                            {"id": "no_change", "text": "Não precisa"},
                            {"id": "change_50", "text": "R$ 50"},
                            {"id": "change_100", "text": "R$ 100"},
                        ]
                    )
                ],
                next_state=ConversationState.CHECKOUT_CHANGE
            )
        
        # Salvar troco
        if not order_context:
            order_context = OrderContext()
        
        order_context.change_for = change_value
        conversation_context.collected_data["change_for"] = change_value
        
        # Mostrar resumo em seguida para o cliente confirmar o pedido (não encerrar o fluxo)
        items_text = []
        for item in order_context.items:
            qty = item.get("quantity", 1)
            code = item.get("product_code", "")
            subtotal = Decimal(str(item.get("subtotal", 0)))
            items_text.append(f"• {qty}x {code} - {self._format_currency(subtotal)}")
        items_summary = "\n".join(items_text)
        total = Decimal(str(order_context.subtotal))
        if order_context.delivery_fee:
            total += Decimal(str(order_context.delivery_fee))
        order_context.total = float(total)
        address_text = self._format_address(order_context.address) if order_context.address else "Retirada na loja"
        payment_labels = {
            "cash": "💵 Dinheiro",
            "credit_card": "💳 Cartão de Crédito",
            "debit_card": "💳 Cartão de Débito",
            "pix": "📱 PIX",
            "invoice": "📄 Faturado",
        }
        payment_text = payment_labels.get(order_context.payment_method, order_context.payment_method or "")
        payment_text += f" (troco p/ R$ {change_value:.2f})".replace(".", ",")
        delivery_estimate = "30-60 min"
        if order_context.address and order_context.address.get("bairro"):
            area = get_coverage_area(order_context.address["bairro"])
            if area:
                delivery_estimate = f"{area.delivery_time_min}-{area.delivery_time_max} min"
        summary_text = ORDER_SUMMARY.format(
            customer_name=customer_context.name if customer_context else "Cliente",
            address=address_text,
            items=items_summary,
            total=self._format_currency(total),
            payment_method=payment_text,
            delivery_estimate=delivery_estimate,
        )
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(text=f"✅ Troco para R$ {change_value:.2f}".replace(".", ",")),
                self._create_response(
                    text=summary_text,
                    buttons=[
                        {"id": "confirm", "text": "✅ Confirmar"},
                        {"id": "edit", "text": "✏️ Alterar"},
                        {"id": "cancel", "text": "❌ Cancelar"},
                    ]
                ),
            ],
            next_state=ConversationState.CHECKOUT_SUMMARY
        )


class CheckoutSummaryHandler(BaseHandler):
    """Handler para CHECKOUT_SUMMARY - Mostra resumo e pede confirmação."""
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa confirmação do pedido."""
        
        msg_lower = message.lower().strip()
        
        # Confirmar pedido (aceitar 1 ou texto)
        if msg_lower in ["confirm", "confirmar", "sim", "s", "ok", "1"]:
            # Verificar se tem documento (CPF/CNPJ)
            if customer_context and not customer_context.document:
                # Pedir documento antes de confirmar
                customer_type = customer_context.customer_type or "PF"
                
                if customer_type == "PJ":
                    from app.core.message_templates import ASK_DOCUMENT_CNPJ
                    return self._create_result(
                        conversation_context=conversation_context,
                        customer_context=customer_context,
                        order_context=order_context,
                        responses=[
                            self._create_response(text=ASK_DOCUMENT_CNPJ)
                        ],
                        next_state=ConversationState.IDENTIFY_DOCUMENT_CNPJ
                    )
                else:
                    from app.core.message_templates import ASK_DOCUMENT_CPF
                    return self._create_result(
                        conversation_context=conversation_context,
                        customer_context=customer_context,
                        order_context=order_context,
                        responses=[
                            self._create_response(text=ASK_DOCUMENT_CPF)
                        ],
                        next_state=ConversationState.IDENTIFY_DOCUMENT_CPF
                    )
            
            # Garantir que o cliente existe no banco (Order.customer_id NOT NULL)
            customer_context = await self._ensure_customer_for_order(
                conversation_context, customer_context
            )
            if not customer_context or not customer_context.customer_id:
                return self._create_result(
                    conversation_context=conversation_context,
                    customer_context=customer_context,
                    order_context=order_context,
                    responses=[
                        self._create_response(
                            text="❌ Não foi possível identificar seu cadastro. Por favor, recomece o pedido (digite *menu*)."
                        )
                    ],
                    next_state=ConversationState.GREETING_INITIAL,
                    success=False
                )
            
            # Criar pedido no banco
            order = await self._create_order(
                conversation_context,
                customer_context,
                order_context
            )
            
            if not order:
                return self._create_result(
                    conversation_context=conversation_context,
                    customer_context=customer_context,
                    order_context=order_context,
                    responses=[
                        self._create_response(
                            text="❌ Erro ao criar pedido. Tente novamente ou fale com um atendente."
                        )
                    ],
                    next_state=ConversationState.SUPPORT_HUMAN,
                    needs_human=True,
                    success=False
                )
            
            # Salvar order_id no contexto
            conversation_context.collected_data["order_id"] = str(order.id)
            
            # Mensagem de confirmação completa (resumo agrupado: 4x P13 em vez de 1x P13 repetido)
            items_text = self._format_items_summary_aggregated(
                order_context.items if order_context and order_context.items else []
            )
            address_text = self._format_address(order_context.address) if order_context and order_context.address else "Retirada na loja"
            payment_labels = {
                "cash": "💵 Dinheiro na entrega",
                "credit_card": "💳 Cartão na entrega",
                "debit_card": "💳 Cartão de Débito na entrega",
                "pix": "📱 PIX",
                "invoice": "📄 Faturado",
            }
            payment_text = payment_labels.get(order_context.payment_method if order_context else None, "Pagamento na entrega")
            delivery_time = "30-60 min"
            if order_context and order_context.address and order_context.address.get("bairro"):
                area = get_coverage_area(order_context.address["bairro"])
                if area:
                    delivery_time = f"{area.delivery_time_min}-{area.delivery_time_max} min"
            confirmation_text = ORDER_CONFIRMED.format(
                order_number=order.order_number,
                items_summary=items_text,
                address=address_text,
                total=self._format_currency(order.total_amount),
                payment_method=payment_text,
                delivery_time=delivery_time,
            )
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=confirmation_text)
                ],
                next_state=ConversationState.COMPLETE_CONFIRMED
            )
        
        # Alterar algo
        if msg_lower in ["edit", "alterar", "mudar"]:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="O que deseja alterar?",
                        buttons=[
                            {"id": "edit_product", "text": "🛒 Produto"},
                            {"id": "edit_address", "text": "📍 Endereço"},
                            {"id": "edit_payment", "text": "💳 Pagamento"},
                        ]
                    )
                ],
                next_state=ConversationState.CHECKOUT_SUMMARY
            )
        
        # Cancelar
        if msg_lower in ["cancel", "cancelar"]:
            # Resetar contextos
            conversation_context.collected_data = {}
            if order_context:
                order_context.items = []
                order_context.subtotal = 0.0
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="❌ Pedido cancelado.\n\nPosso ajudar com mais alguma coisa?",
                        buttons=get_quick_replies("main_menu")
                    )
                ],
                next_state=ConversationState.GREETING_INITIAL
            )
        
        # Editar produto
        if msg_lower == "edit_product":
            conversation_context.collected_data.pop("product_code", None)
            conversation_context.collected_data.pop("quantity", None)
            if order_context:
                order_context.items = []
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text="🛒 Qual produto deseja?")
                ],
                next_state=ConversationState.ORDERING_PRODUCT
            )
        
        # Editar endereço
        if msg_lower == "edit_address":
            conversation_context.collected_data.pop("address", None)
            if order_context:
                order_context.address = None
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text="📍 Qual o novo endereço?")
                ],
                next_state=ConversationState.ORDERING_ADDRESS
            )
        
        # Editar pagamento
        if msg_lower == "edit_payment":
            conversation_context.collected_data.pop("payment_method", None)
            if order_context:
                order_context.payment_method = None
            
            customer_type = customer_context.customer_type if customer_context else "PF"
            buttons_key = "payment_methods_pj" if customer_type == "PJ" else "payment_methods_pf"
            payment_buttons = get_quick_replies(buttons_key)
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="💳 Como deseja pagar? (pode digitar 1, 2 ou 3)",
                        buttons=payment_buttons
                    )
                ],
                next_state=ConversationState.CHECKOUT_PAYMENT
            )
        
        # Mostrar resumo
        return await self._show_summary(
            conversation_context,
            customer_context,
            order_context
        )
    
    async def _show_summary(
        self,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext],
        order_context: Optional[OrderContext],
    ) -> HandlerResult:
        """Mostra resumo do pedido."""
        
        if not order_context or not order_context.items:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="❌ Nenhum item no pedido. Vamos começar de novo?"
                    )
                ],
                next_state=ConversationState.ORDERING_PRODUCT
            )
        
        # Formatar itens
        items_text = []
        for item in order_context.items:
            qty = item.get("quantity", 1)
            code = item.get("product_code", "")
            subtotal = Decimal(str(item.get("subtotal", 0)))
            items_text.append(f"• {qty}x {code} - {self._format_currency(subtotal)}")
        
        items_summary = "\n".join(items_text)
        
        # Calcular total
        total = Decimal(str(order_context.subtotal))
        if order_context.delivery_fee:
            total += Decimal(str(order_context.delivery_fee))
        
        order_context.total = float(total)
        
        # Formatar endereço
        address_text = self._format_address(order_context.address) if order_context.address else "Retirada na loja"
        
        # Formatar pagamento
        payment_labels = {
            "cash": "💵 Dinheiro",
            "credit_card": "💳 Cartão de Crédito",
            "debit_card": "💳 Cartão de Débito",
            "pix": "📱 PIX",
            "invoice": "📄 Faturado",
        }
        payment_text = payment_labels.get(order_context.payment_method, order_context.payment_method or "")
        
        if order_context.payment_method == "cash" and order_context.change_for:
            payment_text += f" (troco p/ R$ {order_context.change_for:.2f})".replace(".", ",")
        
        # Estimativa de entrega
        delivery_estimate = "30-60 min"
        if order_context.address and order_context.address.get("bairro"):
            area = get_coverage_area(order_context.address["bairro"])
            if area:
                delivery_estimate = f"{area.delivery_time_min}-{area.delivery_time_max} min"
        
        # Mostrar resumo
        summary_text = ORDER_SUMMARY.format(
            customer_name=customer_context.name if customer_context else "Cliente",
            address=address_text,
            items=items_summary,
            total=self._format_currency(total),
            payment_method=payment_text,
            delivery_estimate=delivery_estimate
        )
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text=summary_text,
                    buttons=[
                        {"id": "confirm", "text": "✅ Confirmar"},
                        {"id": "edit", "text": "✏️ Alterar"},
                        {"id": "cancel", "text": "❌ Cancelar"},
                    ]
                )
            ],
            next_state=ConversationState.CHECKOUT_SUMMARY
        )
