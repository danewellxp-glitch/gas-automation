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
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    footer: Optional[str] = None
    
    def has_buttons(self) -> bool:
        return bool(self.buttons)


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
        footer: Optional[str] = None,
    ) -> MessageResponse:
        """Helper para criar resposta."""
        return MessageResponse(text=text, buttons=buttons, footer=footer)
    
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
