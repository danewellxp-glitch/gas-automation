"""
Flow Engine Router - Roteador Inteligente V1/V2
Escolhe automaticamente entre Flow Engine V1 e V2 baseado em feature flags.

Este arquivo garante que NÃO HAVERÁ DUPLICIDADE:
- Se V2 habilitado → usa V2
- Se V2 desabilitado → usa V1
- Rollout gradual → alguns usuários V2, outros V1
"""

import logging
from typing import List, Dict, Optional

from app.core.flow_config import FEATURE_FLAGS, ROLLOUT_PERCENTAGE

logger = logging.getLogger(__name__)


class FlowEngineRouter:
    """
    Roteador que decide qual Flow Engine usar (V1 ou V2).
    
    Garante que apenas UMA versão processa cada mensagem.
    """
    
    def __init__(self):
        self._v1_engine = None
        self._v2_engine = None
        self._v2_factory = None
        
        logger.info("FlowEngineRouter inicializado")
    
    async def process_message(
        self,
        phone: str,
        message: str,
        message_id: Optional[str] = None,
        waha_chat_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Processa mensagem usando V1 ou V2 automaticamente.
        
        Args:
            phone: Número de telefone
            message: Texto da mensagem
            message_id: ID da mensagem
            waha_chat_id: ID do chat no WAHA
            trace_id: ID de rastreamento
        
        Returns:
            Resultado do processamento (compatível com V1)
        """
        # Decidir qual versão usar
        use_v2 = self._should_use_v2(phone)
        
        if use_v2:
            logger.info(f"[{trace_id}] Usando Flow Engine V2 para {phone}")
            return await self._process_with_v2(
                phone, message, message_id, waha_chat_id, trace_id
            )
        else:
            logger.info(f"[{trace_id}] Usando Flow Engine V1 para {phone}")
            return await self._process_with_v1(
                phone, message, message_id, waha_chat_id
            )
    
    def _should_use_v2(self, phone: str) -> bool:
        """
        Decide se deve usar V2 para este telefone.
        
        Args:
            phone: Número de telefone
        
        Returns:
            True se deve usar V2, False para V1
        """
        # Feature flag desabilitado → V1
        if not FEATURE_FLAGS.get("flow_engine_v2_enabled", False):
            return False
        
        # Rollout 100% → V2 para todos
        if ROLLOUT_PERCENTAGE >= 100:
            return True
        
        # Rollout 0% → V1 para todos
        if ROLLOUT_PERCENTAGE <= 0:
            return False
        
        # Rollout gradual baseado em hash do telefone
        phone_hash = hash(phone) % 100
        return phone_hash < ROLLOUT_PERCENTAGE
    
    async def _process_with_v1(
        self,
        phone: str,
        message: str,
        message_id: Optional[str],
        waha_chat_id: Optional[str],
    ):
        """Processa com Flow Engine V1 (atual)."""
        # Lazy load V1
        if self._v1_engine is None:
            from app.core.flow_engine import flow_engine
            self._v1_engine = flow_engine
        
        # Processar com V1
        return await self._v1_engine.process_message(
            phone=phone,
            message=message,
            message_id=message_id,
            waha_chat_id=waha_chat_id,
        )
    
    async def _process_with_v2(
        self,
        phone: str,
        message: str,
        message_id: Optional[str],
        waha_chat_id: Optional[str],
        trace_id: Optional[str],
    ):
        """Processa com Flow Engine V2 (novo)."""
        # Lazy load V2
        if self._v2_engine is None:
            from app.core.flow_engine_factory import get_flow_engine_v2
            self._v2_engine = await get_flow_engine_v2()
        
        # Processar com V2
        responses = await self._v2_engine.process_message(
            phone=phone,
            message=message,
            trace_id=trace_id,
        )
        
        # Converter resposta V2 para formato V1 (compatibilidade)
        return self._convert_v2_to_v1_format(responses)
    
    def _convert_v2_to_v1_format(self, v2_responses: List[Dict]) -> object:
        """
        Converte resposta do V2 para formato compatível com V1.
        
        Args:
            v2_responses: Lista de respostas do V2
        
        Returns:
            Objeto compatível com V1 (tem .responses e .success)
        """
        class V1CompatibleResult:
            def __init__(self, responses):
                self.responses = responses
                self.success = True
        
        # Converter formato de resposta
        v1_responses = []
        for resp in v2_responses:
            v1_responses.append({
                "type": resp.get("type", "text"),
                "content": resp.get("text", ""),
                "buttons": resp.get("buttons"),
                "media_url": resp.get("media_url"),
            })
        
        return V1CompatibleResult(v1_responses)
    
    async def send_responses(
        self,
        phone: str,
        responses: List[Dict],
        trace_id: Optional[str] = None,
    ):
        """
        Envia respostas usando WAHA.
        
        Args:
            phone: Número de telefone
            responses: Lista de respostas
            trace_id: ID de rastreamento
        
        Returns:
            Resultado do envio
        """
        # Usar V1 para envio (já está implementado)
        if self._v1_engine is None:
            from app.core.flow_engine import flow_engine
            self._v1_engine = flow_engine
        
        return await self._v1_engine.send_responses(
            phone, responses, trace_id=trace_id
        )
    
    async def get_context(self, phone: str):
        """Obtém contexto (compatibilidade V1)."""
        use_v2 = self._should_use_v2(phone)
        
        if use_v2:
            # V2: Usar ContextManager
            if self._v2_engine is None:
                from app.core.flow_engine_factory import get_flow_engine_v2
                self._v2_engine = await get_flow_engine_v2()
            
            # V2 não expõe get_context diretamente, retornar None
            return None
        else:
            # V1
            if self._v1_engine is None:
                from app.core.flow_engine import flow_engine
                self._v1_engine = flow_engine
            
            return await self._v1_engine.get_context(phone)
    
    async def save_context(self, context):
        """Salva contexto (compatibilidade V1)."""
        # V1 apenas
        if self._v1_engine is None:
            from app.core.flow_engine import flow_engine
            self._v1_engine = flow_engine
        
        return await self._v1_engine.save_context(context)
    
    def get_engine_version(self, phone: str) -> str:
        """
        Retorna versão do engine para um telefone.
        
        Args:
            phone: Número de telefone
        
        Returns:
            "v1" ou "v2"
        """
        return "v2" if self._should_use_v2(phone) else "v1"


# Singleton global
_router_instance: Optional[FlowEngineRouter] = None


def get_flow_engine_router() -> FlowEngineRouter:
    """
    Obtém instância singleton do router.
    
    Returns:
        FlowEngineRouter
    """
    global _router_instance
    
    if _router_instance is None:
        _router_instance = FlowEngineRouter()
    
    return _router_instance


# Alias para compatibilidade com código existente
flow_engine = get_flow_engine_router()
