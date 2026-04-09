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
        """Vai para selecao de produtos (ou fast-track se intenção foi detectada)."""
        
        # FAST-TRACK: Se intenção foi detectada na mensagem inicial
        intent_product = conversation_context.collected_data.get("intent_product")
        intent_operation = conversation_context.collected_data.get("intent_operation")
        
        if intent_product:
            from app.core.product_catalog import get_product
            from app.core.message_templates import PRODUCT_SELECTED, ASK_ADDRESS
            product = get_product(intent_product)
            if product:
                # Salvar produto e quantidade
                conversation_context.collected_data["product_code"] = intent_product
                conversation_context.collected_data["quantity"] = conversation_context.collected_data.get("intent_quantity", 1)
                
                if intent_operation:
                    # Tem produto + operação → pular direto para endereço
                    conversation_context.collected_data["operation_type"] = intent_operation
                    if not order_context:
                        order_context = OrderContext()
                    
                    quantity = conversation_context.collected_data["quantity"]
                    unit_price = product.price_sale if intent_operation == "sale" else product.price_exchange
                    total = unit_price * quantity
                    order_context.items.append({
                        "product_code": intent_product,
                        "quantity": quantity,
                        "unit_price": float(unit_price),
                        "subtotal": float(total),
                        "operation_type": intent_operation,
                    })
                    order_context.subtotal = float(total)
                    order_context.operation_type = intent_operation
                    
                    op_label = {"exchange": "Troca", "sale": "Compra", "pickup": "Retira"}.get(intent_operation, "Troca")
                    return self._create_result(
                        conversation_context=conversation_context,
                        customer_context=customer_context,
                        order_context=order_context,
                        responses=[
                            self._create_response(
                                text=f"Prazer, *{name}*!\n\n"
                                     f"✅ {quantity}x {intent_product} ({op_label}) - {self._format_currency(total)}\n\n"
                                     + ASK_ADDRESS
                            )
                        ],
                        next_state=ConversationState.ORDERING_ADDRESS
                    )
                else:
                    # Tem produto mas sem operação → mostrar operações
                    price_troca = self._format_currency(product.price_exchange)
                    price_compra = self._format_currency(product.price_sale)
                    return self._create_result(
                        conversation_context=conversation_context,
                        customer_context=customer_context,
                        order_context=order_context,
                        responses=[
                            self._create_response(
                                text=f"Prazer, *{name}*!\n\n"
                                     f"✅ *{product.name}* selecionado!\n"
                                     f"💰 Valor: {price_troca}\n\nComo deseja?",
                                buttons=[
                                    {"id": "exchange", "text": f"🔄 Troca - {price_troca}"},
                                    {"id": "sale", "text": f"🆕 Comprar - {price_compra}"},
                                    {"id": "pickup", "text": f"🏪 Retira - {price_troca}"},
                                ]
                            )
                        ],
                        next_state=ConversationState.ORDERING_OPERATION
                    )
        
        # Fluxo normal: mostrar catálogo de produtos
        sections = self._build_product_list_sections()
        product_text = self._build_product_text()

        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="Prazer, *{}*!\n\n🛒 Qual botijão você precisa?\n\n{}".format(name, product_text),
                    list_sections=sections,
                    list_button_text="Ver Produtos",
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
        
        # Ir para produtos (CNPJ sera pedido antes de confirmar)
        sections = self._build_product_list_sections()
        product_text = self._build_product_text()

        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(
                    text="Prazer, *{}*!\n\n🛒 Qual botijão você precisa?\n\n{}".format(name, product_text),
                    list_sections=sections,
                    list_button_text="Ver Produtos",
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

        # Auto-finalizar pedido (o cliente ja confirmou antes de pedir CPF)
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
                        text="✅ CPF registrado!\n\nNao consegui identificar seu cadastro. Digite *menu* para recomecar."
                    )
                ],
                next_state=ConversationState.GREETING_INITIAL,
                success=False,
            )

        order = await self._create_order(
            conversation_context, customer_context, order_context
        )

        if not order:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="✅ CPF registrado!\n\nErro ao criar pedido. Tente novamente ou fale com um atendente."
                    )
                ],
                next_state=ConversationState.SUPPORT_HUMAN,
                needs_human=True,
                success=False,
            )

        conversation_context.collected_data["order_id"] = str(order.id)

        confirmation_text = self._build_order_confirmation_text(
            order, order_context, customer_context
        )

        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(text="✅ CPF registrado!\n\n" + confirmation_text)
            ],
            next_state=ConversationState.COMPLETE_FOLLOWUP
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

        # Auto-finalizar pedido (o cliente ja confirmou antes de pedir CNPJ)
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
                        text="✅ CNPJ registrado!\n\nNao consegui identificar seu cadastro. Digite *menu* para recomecar."
                    )
                ],
                next_state=ConversationState.GREETING_INITIAL,
                success=False,
            )

        order = await self._create_order(
            conversation_context, customer_context, order_context
        )

        if not order:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[
                    self._create_response(
                        text="✅ CNPJ registrado!\n\nErro ao criar pedido. Tente novamente ou fale com um atendente."
                    )
                ],
                next_state=ConversationState.SUPPORT_HUMAN,
                needs_human=True,
                success=False,
            )

        conversation_context.collected_data["order_id"] = str(order.id)

        confirmation_text = self._build_order_confirmation_text(
            order, order_context, customer_context
        )

        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[
                self._create_response(text="✅ CNPJ registrado!\n\n" + confirmation_text)
            ],
            next_state=ConversationState.COMPLETE_FOLLOWUP
        )


class IdentifyUnknownPhoneHandler(BaseHandler):
    """
    Handler para IDENTIFY_UNKNOWN_PHONE.
    Apresenta menu para número não cadastrado.

    Opções:
    [1] Cadastrar novo → IDENTIFY_TYPE
    [2] Já sou cliente → IDENTIFY_ASSOCIATE_PHONE
    [3] Consumidor final → ORDERING_PRODUCT (sem cadastro)
    """

    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        from app.core.message_templates import UNKNOWN_PHONE_MENU

        msg = message.lower().strip()

        # Opção 1 — Cadastrar
        if msg in ["1", "unknown_cadastrar", "cadastrar", "novo"]:
            if not customer_context:
                customer_context = CustomerContext()
            customer_context.customer_type = "PF"
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[self._create_response(
                    text="📝 Vamos criar seu cadastro!\n\nVocê é:",
                    buttons=get_quick_replies("customer_type")
                )],
                next_state=ConversationState.IDENTIFY_TYPE,
            )

        # Opção 2 — Associar
        if msg in ["2", "unknown_associar", "associar", "já sou cliente", "ja sou cliente"]:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[self._create_response(
                    text="🔍 Para localizar seu cadastro, por favor informe seu CPF ou CNPJ:"
                )],
                next_state=ConversationState.IDENTIFY_ASSOCIATE_PHONE,
            )

        # Opção 3 — Consumidor final
        if msg in ["3", "unknown_consumidor", "consumidor", "sem cadastro"]:
            if not customer_context:
                customer_context = CustomerContext()
            conversation_context.collected_data["is_consumer_final"] = True
            conversation_context.collected_data["customer_type"] = "PF"
            customer_context.name = "Consumidor Final"

            sections = self._build_product_list_sections()
            product_text = self._build_product_text()

            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[self._create_response(
                    text=f"🛒 Qual botijão você precisa?\n\n{product_text}",
                    list_sections=sections,
                    list_button_text="Ver Produtos",
                )],
                next_state=ConversationState.ORDERING_PRODUCT,
            )

        # Não entendeu — reapresentar menu
        self._increment_retry(conversation_context)
        if self._should_escalate_to_human(conversation_context):
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                responses=[self._create_response(text="Vou te conectar com um atendente.")],
                next_state=ConversationState.SUPPORT_HUMAN,
                needs_human=True,
            )

        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[self._create_response(
                text=UNKNOWN_PHONE_MENU,
                buttons=[
                    {"id": "unknown_cadastrar", "text": "1️⃣ Cadastrar"},
                    {"id": "unknown_associar", "text": "2️⃣ Já sou cliente"},
                    {"id": "unknown_consumidor", "text": "3️⃣ Sem cadastro"},
                ]
            )],
            next_state=ConversationState.IDENTIFY_UNKNOWN_PHONE,
        )


class IdentifyAssociatePhoneHandler(BaseHandler):
    """
    Handler para IDENTIFY_ASSOCIATE_PHONE.
    Coleta CPF/CNPJ, localiza cadastro existente e associa o número.
    """

    async def handle(
        self,
        message: str,
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext] = None,
        order_context: Optional[OrderContext] = None,
        entities: Optional[Dict] = None,
    ) -> HandlerResult:
        from app.core.message_templates import UNKNOWN_PHONE_MENU

        doc = ''.join(filter(str.isdigit, message.strip()))

        if len(doc) not in (11, 14):
            self._increment_retry(conversation_context)
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[self._create_response(
                    text="⚠️ CPF ou CNPJ inválido. Por favor, informe apenas os números (11 dígitos CPF ou 14 dígitos CNPJ):"
                )],
                next_state=ConversationState.IDENTIFY_ASSOCIATE_PHONE,
            )

        # Buscar cliente por CPF/CNPJ no banco
        customer = await self._find_customer_by_document(doc)

        if not customer:
            return self._create_result(
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                responses=[self._create_response(
                    text=f"❌ Não encontrei cadastro com esse documento.\n\nDeseja:\n\n"
                         + UNKNOWN_PHONE_MENU,
                    buttons=[
                        {"id": "unknown_cadastrar", "text": "1️⃣ Cadastrar"},
                        {"id": "unknown_associar", "text": "2️⃣ Tentar outro documento"},
                        {"id": "unknown_consumidor", "text": "3️⃣ Sem cadastro"},
                    ]
                )],
                next_state=ConversationState.IDENTIFY_UNKNOWN_PHONE,
            )

        # Associar número de telefone ao cliente
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from app.models.customer import Customer
            result = await db.execute(
                select(Customer).where(Customer.id == customer.id)
            )
            db_customer = result.scalar_one_or_none()
            if db_customer:
                db_customer.phone = conversation_context.phone
                await db.commit()

        customer_type = "PJ" if len(doc) == 14 else "PF"
        customer_context = CustomerContext(
            customer_id=str(customer.id),
            name=customer.name,
            document=customer.cpf_cnpj,
            customer_type=customer_type,
            addresses=[customer.address] if customer.address else [],
        )
        conversation_context.is_returning = True

        return self._create_result(
            conversation_context=conversation_context,
            customer_context=customer_context,
            order_context=order_context,
            responses=[self._create_response(
                text=f"✅ Cadastro encontrado! Olá, *{customer.name}*!\n\n"
                     f"Seu número foi associado ao seu cadastro.\n\n"
                     f"Como posso ajudar?",
                buttons=[
                    {"id": "new_order", "text": "🛒 Fazer Pedido"},
                    {"id": "track_order", "text": "📦 Meus Pedidos"},
                ]
            )],
            next_state=ConversationState.GREETING_RETURNING,
        )

    async def _find_customer_by_document(self, doc: str):
        """Busca cliente por CPF/CNPJ no banco."""
        try:
            from app.database import AsyncSessionLocal
            from sqlalchemy import select, or_
            from app.models.customer import Customer

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Customer).where(
                        or_(
                            Customer.cpf_cnpj == doc,
                            Customer.cpf_cnpj == f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}",  # CPF formatado
                        )
                    )
                )
                return result.scalar_one_or_none()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erro ao buscar cliente por documento: {e}")
            return None
