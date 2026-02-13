"""
Handlers da Fase IDENTIFY - Flow Engine 2.0
Responsáveis por identificação e coleta de dados do cliente.
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
    ASK_CUSTOMER_TYPE,
    ASK_NAME_PF,
    ASK_NAME_PJ,
    ASK_DOCUMENT_CPF,
    ASK_DOCUMENT_CNPJ,
    INVALID_CPF,
    INVALID_CNPJ,
)
from app.core.flow_config import get_quick_replies

logger = logging.getLogger(__name__)


class IdentifyTypeHandler(BaseHandler):
    """
    Handler para IDENTIFY_TYPE.
    Pergunta se é Pessoa Física ou Jurídica.
    """
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa seleção de tipo de cliente."""
        
        msg = message.lower().strip()
        
        # Verificar se é PF
        is_pf = any(x in msg for x in ["pf", "fisica", "física", "pessoa", "1"])
        is_pj = any(x in msg for x in ["pj", "empresa", "juridica", "jurídica", "cnpj", "2"])
        
        if not customer_context:
            customer_context = CustomerContext()
        
        if is_pj:
            customer_context.customer_type = "PJ"
            conversation_context.collected_data["customer_type"] = "PJ"
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=ASK_NAME_PJ)
                ],
                next_state=ConversationState.IDENTIFY_NAME_PJ
            )
        
        if is_pf:
            customer_context.customer_type = "PF"
            conversation_context.collected_data["customer_type"] = "PF"
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=ASK_NAME_PF)
                ],
                next_state=ConversationState.IDENTIFY_NAME_PF
            )
        
        # Não entendeu
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
        
        # Tentar novamente
        if conversation_context.retry_count >= 2:
            # Assumir PF após 2 tentativas
            customer_context.customer_type = "PF"
            conversation_context.collected_data["customer_type"] = "PF"
            self._reset_retry(conversation_context)
            
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Vou continuar como pessoa física.\n\n" + ASK_NAME_PF
                    )
                ],
                next_state=ConversationState.IDENTIFY_NAME_PF
            )
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="Por favor, escolha uma opção:",
                    buttons=get_quick_replies("customer_type")
                )
            ],
            next_state=ConversationState.IDENTIFY_TYPE
        )


class IdentifyNamePFHandler(BaseHandler):
    """
    Handler para IDENTIFY_NAME_PF.
    Coleta nome completo da Pessoa Física.
    """
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa nome do cliente PF."""
        
        name = message.strip()
        
        # Validar nome
        if len(name) < 2:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Nome muito curto. Por favor, digite o nome completo:"
                    )
                ],
                next_state=ConversationState.IDENTIFY_NAME_PF
            )
        
        if len(name) > 100:
            name = name[:100]
        
        # Capitalizar nome
        name = name.title()
        
        # Atualizar contextos
        if not customer_context:
            customer_context = CustomerContext()
        
        customer_context.name = name
        conversation_context.collected_data["name"] = name
        
        # Salvar no banco
        customer = await self._get_customer_by_phone(conversation_context.phone)
        if customer:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                customer.name = name
                customer.tipo_documento = "PF"
                await db.commit()
        
        # Ir para produtos (CPF será pedido antes de confirmar)
        return await self._go_to_products(
            conversation_context,
            customer_context,
            order_context,
            name
        )
    
    async def _go_to_products(
        self,
        conversation_context: ConversationContext,
        customer_context: CustomerContext,
        order_context: Optional[OrderContext],
        name: str,
    ) -> HandlerResult:
        """Vai para seleção de produtos."""
        
        from app.core.product_catalog import get_active_products
        products = get_active_products()
        
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
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text=f"Prazer, *{name}*!\n\n🛒 Qual botijão você precisa?\n\n{product_text}",
                    buttons=product_buttons[:3]
                )
            ],
            next_state=ConversationState.ORDERING_PRODUCT
        )


class IdentifyNamePJHandler(BaseHandler):
    """
    Handler para IDENTIFY_NAME_PJ.
    Coleta razão social da Pessoa Jurídica.
    """
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa nome da empresa."""
        
        name = message.strip()
        
        # Validar nome
        if len(name) < 2:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="Nome muito curto. Por favor, digite o nome da empresa:"
                    )
                ],
                next_state=ConversationState.IDENTIFY_NAME_PJ
            )
        
        if len(name) > 100:
            name = name[:100]
        
        # Atualizar contextos
        if not customer_context:
            customer_context = CustomerContext()
        
        customer_context.name = name
        customer_context.customer_type = "PJ"
        conversation_context.collected_data["name"] = name
        conversation_context.collected_data["customer_type"] = "PJ"
        
        # Salvar no banco
        customer = await self._get_customer_by_phone(conversation_context.phone)
        if customer:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                customer.name = name
                customer.tipo_documento = "PJ"
                await db.commit()
        
        # Ir para produtos (CNPJ será pedido antes de confirmar)
        from app.core.product_catalog import get_active_products
        products = get_active_products()
        
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
        
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text=f"Prazer, *{name}*!\n\n🛒 Qual botijão você precisa?\n\n{product_text}",
                    buttons=product_buttons[:3]
                )
            ],
            next_state=ConversationState.ORDERING_PRODUCT
        )


class IdentifyDocumentCPFHandler(BaseHandler):
    """
    Handler para IDENTIFY_DOCUMENT_CPF.
    Coleta e valida CPF.
    """
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa CPF."""
        
        # Extrair apenas números
        cpf = re.sub(r"[^0-9]", "", message)
        
        # Validar tamanho
        if len(cpf) != 11:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=INVALID_CPF)
                ],
                next_state=ConversationState.IDENTIFY_DOCUMENT_CPF
            )
        
        # Validar CPF
        if not self._validate_cpf(cpf):
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=INVALID_CPF)
                ],
                next_state=ConversationState.IDENTIFY_DOCUMENT_CPF
            )
        
        # Salvar CPF
        if not customer_context:
            customer_context = CustomerContext()
        
        customer_context.document = cpf
        conversation_context.collected_data["document"] = cpf
        
        # Salvar no banco
        customer = await self._get_customer_by_phone(conversation_context.phone)
        if customer:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                customer.cpf_cnpj = cpf
                await db.commit()
        
        # Voltar para resumo do pedido (será chamado pelo flow engine)
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(text="✅ CPF registrado!")
            ],
            next_state=ConversationState.CHECKOUT_SUMMARY
        )


class IdentifyDocumentCNPJHandler(BaseHandler):
    """
    Handler para IDENTIFY_DOCUMENT_CNPJ.
    Coleta e valida CNPJ.
    """
    
    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        """Processa CNPJ."""
        
        # Extrair apenas números
        cnpj = re.sub(r"[^0-9]", "", message)
        
        # Validar tamanho
        if len(cnpj) != 14:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=INVALID_CNPJ)
                ],
                next_state=ConversationState.IDENTIFY_DOCUMENT_CNPJ
            )
        
        # Validar CNPJ
        if not self._validate_cnpj(cnpj):
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(text=INVALID_CNPJ)
                ],
                next_state=ConversationState.IDENTIFY_DOCUMENT_CNPJ
            )
        
        # Salvar CNPJ
        if not customer_context:
            customer_context = CustomerContext()
        
        customer_context.document = cnpj
        conversation_context.collected_data["document"] = cnpj
        
        # Salvar no banco
        customer = await self._get_customer_by_phone(conversation_context.phone)
        if customer:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                customer.cpf_cnpj = cnpj
                await db.commit()
        
        # Voltar para resumo do pedido
        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(text="✅ CNPJ registrado!")
            ],
            next_state=ConversationState.CHECKOUT_SUMMARY
        )
