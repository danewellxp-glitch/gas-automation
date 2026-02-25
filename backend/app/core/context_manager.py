"""
Context Manager - Gerenciamento de Contextos
Responsável por carregar, salvar e gerenciar os 3 tipos de contexto.

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md - Parte 5
"""

import logging
import json
from typing import Optional
from datetime import datetime, timedelta

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)
from app.core.flow_config import CONTEXT_TTL_SECONDS
from app.database import AsyncSessionLocal
from app.models.customer import Customer
from sqlalchemy import select

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Gerenciador de contextos do Flow Engine 2.0.
    
    Gerencia 3 tipos de contexto:
    1. ConversationContext - Estado da conversa (Redis)
    2. CustomerContext - Dados do cliente (PostgreSQL + Cache)
    3. OrderContext - Pedido atual (Redis)
    """
    
    def __init__(self, redis_client=None):
        """
        Inicializa o Context Manager.
        
        Args:
            redis_client: Cliente Redis para cache (opcional)
        """
        self.redis = redis_client
        self.ttl = CONTEXT_TTL_SECONDS.get("conversation", 1800)  # 30 min default
        
        logger.info("ContextManager inicializado")
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONVERSATION CONTEXT
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_conversation_context(
        self,
        phone: str
    ) -> Optional[ConversationContext]:
        """
        Carrega contexto da conversa do Redis.
        
        Args:
            phone: Número de telefone
        
        Returns:
            ConversationContext ou None se não existir
        """
        if not self.redis:
            logger.warning("Redis não configurado, contexto não será persistido")
            return None
        
        try:
            key = f"conversation:{phone}"
            data = await self.redis.get(key)
            
            if not data:
                return None
            
            # Deserializar
            context_dict = json.loads(data)
            
            # Reconstruir objeto
            context = ConversationContext(
                phone=context_dict["phone"],
                current_state=ConversationState(context_dict["current_state"]),
                state_history=context_dict.get("state_history", []),
                collected_data=context_dict.get("collected_data", {}),
                is_returning=context_dict.get("is_returning", False),
                needs_human=context_dict.get("needs_human", False),
                retry_count=context_dict.get("retry_count", 0),
                return_state=ConversationState(context_dict["return_state"]) if context_dict.get("return_state") else None,
            )
            
            logger.debug(f"Contexto de conversa carregado: {phone} - {context.current_state}")
            return context
            
        except Exception as e:
            logger.error(f"Erro ao carregar contexto de conversa: {e}", exc_info=True)
            return None
    
    async def save_conversation_context(
        self,
        phone: str,
        context: ConversationContext
    ) -> bool:
        """
        Salva contexto da conversa no Redis.
        
        Args:
            phone: Número de telefone
            context: ConversationContext
        
        Returns:
            True se salvo com sucesso
        """
        if not self.redis:
            return False
        
        try:
            key = f"conversation:{phone}"
            
            # Serializar
            context_dict = {
                "phone": context.phone,
                "current_state": context.current_state.value,
                "state_history": context.state_history,
                "collected_data": context.collected_data,
                "is_returning": context.is_returning,
                "needs_human": context.needs_human,
                "retry_count": context.retry_count,
                "return_state": context.return_state.value if context.return_state else None,
            }
            
            data = json.dumps(context_dict)
            
            # Salvar com TTL
            await self.redis.setex(key, self.ttl, data)
            
            logger.debug(f"Contexto de conversa salvo: {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar contexto de conversa: {e}", exc_info=True)
            return False
    
    async def delete_conversation_context(self, phone: str) -> bool:
        """
        Deleta contexto da conversa.
        
        Args:
            phone: Número de telefone
        
        Returns:
            True se deletado com sucesso
        """
        if not self.redis:
            return False
        
        try:
            key = f"conversation:{phone}"
            await self.redis.delete(key)
            
            logger.info(f"Contexto de conversa deletado: {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar contexto de conversa: {e}", exc_info=True)
            return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # CUSTOMER CONTEXT
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_customer_context(
        self,
        phone: str
    ) -> Optional[CustomerContext]:
        """
        Carrega contexto do cliente (PostgreSQL + Cache).
        
        Args:
            phone: Número de telefone
        
        Returns:
            CustomerContext ou None se não existir
        """
        try:
            # Tentar cache primeiro
            if self.redis:
                cached = await self._get_customer_from_cache(phone)
                if cached:
                    return cached
            
            # Buscar no banco
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Customer).where(Customer.phone == phone)
                )
                customer = result.scalar_one_or_none()
                
                if not customer:
                    return None
                
                # Construir contexto
                # Model tem 'address' (singular), converter para lista
                addresses = []
                if customer.address:
                    addresses = [customer.address]
                
                context = CustomerContext(
                    customer_id=str(customer.id),
                    name=customer.name,
                    document=customer.cpf_cnpj,  # Mapear cpf_cnpj para document
                    customer_type=getattr(customer, 'customer_type', None) or "PF",
                    addresses=addresses,
                    default_address_idx=0,
                    last_order=getattr(customer, 'last_order_data', None),
                    preferences=getattr(customer, 'preferences', None) or {},
                    order_count=getattr(customer, 'order_count', 0) or 0,
                )
                
                # Salvar no cache
                if self.redis:
                    await self._save_customer_to_cache(phone, context)
                
                logger.debug(f"Contexto de cliente carregado: {phone} - {customer.name}")
                return context
                
        except Exception as e:
            logger.error(f"Erro ao carregar contexto de cliente: {e}", exc_info=True)
            return None
    
    async def save_customer_context(
        self,
        phone: str,
        context: CustomerContext
    ) -> bool:
        """
        Salva contexto do cliente (PostgreSQL + Cache).
        
        Args:
            phone: Número de telefone
            context: CustomerContext
        
        Returns:
            True se salvo com sucesso
        """
        try:
            async with AsyncSessionLocal() as db:
                # Buscar cliente existente
                result = await db.execute(
                    select(Customer).where(Customer.phone == phone)
                )
                customer = result.scalar_one_or_none()
                
                if customer:
                    # Atualizar
                    customer.name = context.name
                    customer.cpf_cnpj = context.document  # Mapear document para cpf_cnpj
                    if hasattr(customer, 'customer_type'):
                        customer.customer_type = context.customer_type
                    # Model tem 'address' (singular), pegar primeiro da lista
                    customer.address = context.addresses[0] if context.addresses else None
                    if hasattr(customer, 'last_order_data'):
                        customer.last_order_data = context.last_order
                    if hasattr(customer, 'preferences'):
                        customer.preferences = context.preferences
                    if hasattr(customer, 'order_count'):
                        customer.order_count = context.order_count
                else:
                    # Criar novo
                    customer = Customer(
                        phone=phone,
                        name=context.name,
                        cpf_cnpj=context.document,
                        address=context.addresses[0] if context.addresses else None,
                    )
                    db.add(customer)
                
                await db.commit()
                
                # Atualizar ID se foi criado
                if not context.customer_id:
                    context.customer_id = str(customer.id)
                
                # Salvar no cache
                if self.redis:
                    await self._save_customer_to_cache(phone, context)
                
                logger.debug(f"Contexto de cliente salvo: {phone}")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao salvar contexto de cliente: {e}", exc_info=True)
            return False
    
    async def _get_customer_from_cache(
        self,
        phone: str
    ) -> Optional[CustomerContext]:
        """Busca cliente no cache Redis."""
        try:
            key = f"customer:{phone}"
            data = await self.redis.get(key)
            
            if not data:
                return None
            
            context_dict = json.loads(data)
            
            context = CustomerContext(
                customer_id=context_dict.get("customer_id"),
                name=context_dict.get("name"),
                document=context_dict.get("document"),
                customer_type=context_dict.get("customer_type"),
                addresses=context_dict.get("addresses", []),
                default_address_idx=context_dict.get("default_address_idx", 0),
                last_order=context_dict.get("last_order"),
                preferences=context_dict.get("preferences", {}),
                order_count=context_dict.get("order_count", 0),
            )
            
            return context
            
        except Exception as e:
            logger.debug(f"Erro ao buscar cliente no cache: {e}")
            return None
    
    async def _save_customer_to_cache(
        self,
        phone: str,
        context: CustomerContext
    ) -> bool:
        """Salva cliente no cache Redis."""
        try:
            key = f"customer:{phone}"
            
            context_dict = {
                "customer_id": context.customer_id,
                "name": context.name,
                "document": context.document,
                "customer_type": context.customer_type,
                "addresses": context.addresses,
                "default_address_idx": context.default_address_idx,
                "last_order": context.last_order,
                "preferences": context.preferences,
                "order_count": context.order_count,
            }
            
            data = json.dumps(context_dict)
            
            # Cache por 1 hora
            await self.redis.setex(key, 3600, data)
            
            return True
            
        except Exception as e:
            logger.debug(f"Erro ao salvar cliente no cache: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # ORDER CONTEXT
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_order_context(
        self,
        phone: str
    ) -> Optional[OrderContext]:
        """
        Carrega contexto do pedido atual (Redis).
        
        Args:
            phone: Número de telefone
        
        Returns:
            OrderContext ou None se não existir
        """
        if not self.redis:
            return None
        
        try:
            key = f"order:{phone}"
            data = await self.redis.get(key)
            
            if not data:
                return None
            
            context_dict = json.loads(data)
            
            context = OrderContext(
                items=context_dict.get("items", []),
                subtotal=context_dict.get("subtotal", 0.0),
                delivery_fee=context_dict.get("delivery_fee", 0.0),
                total=context_dict.get("total", 0.0),
                address=context_dict.get("address"),
                complement=context_dict.get("complement"),
                operation_type=context_dict.get("operation_type"),
                payment_method=context_dict.get("payment_method"),
                change_for=context_dict.get("change_for"),
            )
            
            logger.debug(f"Contexto de pedido carregado: {phone}")
            return context
            
        except Exception as e:
            logger.error(f"Erro ao carregar contexto de pedido: {e}", exc_info=True)
            return None
    
    async def save_order_context(
        self,
        phone: str,
        context: OrderContext
    ) -> bool:
        """
        Salva contexto do pedido atual (Redis).
        
        Args:
            phone: Número de telefone
            context: OrderContext
        
        Returns:
            True se salvo com sucesso
        """
        if not self.redis:
            return False
        
        try:
            key = f"order:{phone}"
            
            context_dict = {
                "items": context.items,
                "subtotal": context.subtotal,
                "delivery_fee": context.delivery_fee,
                "total": context.total,
                "address": context.address,
                "complement": context.complement,
                "operation_type": context.operation_type,
                "payment_method": context.payment_method,
                "change_for": context.change_for,
            }
            
            data = json.dumps(context_dict)
            
            # TTL de 1 hora para pedidos
            await self.redis.setex(key, 3600, data)
            
            logger.debug(f"Contexto de pedido salvo: {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar contexto de pedido: {e}", exc_info=True)
            return False
    
    async def delete_order_context(self, phone: str) -> bool:
        """
        Deleta contexto do pedido.
        
        Args:
            phone: Número de telefone
        
        Returns:
            True se deletado com sucesso
        """
        if not self.redis:
            return False
        
        try:
            key = f"order:{phone}"
            await self.redis.delete(key)
            
            logger.info(f"Contexto de pedido deletado: {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar contexto de pedido: {e}", exc_info=True)
            return False
