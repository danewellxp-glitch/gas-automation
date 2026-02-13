"""
Flow Engine V2 - Sistema de Conversação
Substitui completamente o Flow Engine V1.

Este arquivo é um wrapper que mantém compatibilidade com código existente
mas usa Flow Engine V2 internamente.
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class FlowEngineWrapper:
    """
    Wrapper que expõe interface compatível com V1
    mas usa V2 internamente.
    """
    
    def __init__(self):
        self._v2_engine = None
        logger.info("FlowEngineWrapper inicializado (usando V2 internamente)")
    
    async def _get_v2_engine(self):
        """Lazy load do V2 engine."""
        if self._v2_engine is None:
            from app.core.flow_engine_factory import get_flow_engine_v2
            self._v2_engine = await get_flow_engine_v2()
            logger.info("Flow Engine V2 carregado")
        return self._v2_engine
    
    async def process_message(
        self,
        phone: str,
        message: str,
        message_id: Optional[str] = None,
        waha_chat_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        """Processa mensagem (interface compatível com V1). Aceita trace_id e waha_chat_id para o webhook."""
        engine = await self._get_v2_engine()
        
        logger.debug(f"Processando mensagem com V2: {phone}")
        
        # Processar com V2 (trace_id para logs; message_id usado como fallback)
        responses = await engine.process_message(
            phone=phone,
            message=message,
            trace_id=trace_id or message_id,
        )
        
        # Obter estado atual após processamento (para result.context e result.new_state)
        current_state = None
        try:
            from app.core.state_machine_v2 import ConversationState
            conv = await engine.context_manager.get_conversation_context(phone)
            current_state = conv.current_state if conv else ConversationState.GREETING_INITIAL
        except Exception as e:
            logger.debug(f"Estado pós-processamento não disponível: {e}")
            from app.core.state_machine_v2 import ConversationState
            current_state = ConversationState.GREETING_INITIAL
        
        return self._adapt_response(responses, waha_chat_id=waha_chat_id, phone=phone, current_state=current_state)
    
    def _adapt_response(
        self,
        v2_responses: List[Dict],
        waha_chat_id: Optional[str] = None,
        phone: Optional[str] = None,
        current_state=None,
    ):
        """Adapta resposta V2 para formato V1 (com context e new_state para o webhook)."""
        from app.core.state_machine_v2 import ConversationState
        state = current_state if current_state is not None else ConversationState.GREETING_INITIAL

        class _Context:
            def __init__(self, waha_chat_id, state):
                self.waha_chat_id = waha_chat_id
                self.state = state

        class V1CompatibleResponse:
            def __init__(self, responses, context, new_state):
                self.responses = []
                for r in responses:
                    self.responses.append({
                        "type": r.get("type", "text"),
                        "content": r.get("text", ""),
                        "buttons": r.get("buttons"),
                        "media_url": r.get("media_url"),
                    })
                self.success = True
                self.context = context
                self.new_state = new_state

        context = _Context(waha_chat_id=waha_chat_id, state=state)
        return V1CompatibleResponse(v2_responses, context=context, new_state=state)
    
    async def send_responses(
        self,
        phone: str,
        responses: List[Dict],
        trace_id: Optional[str] = None,
    ):
        """Envia respostas via WAHA."""
        from app.integrations.waha import waha_client
        
        results = {"sent": 0, "failed": 0}
        
        for response in responses:
            try:
                content = response.get("content") or response.get("text", "")
                buttons = response.get("buttons")
                
                if buttons:
                    await waha_client.send_buttons(phone, content, buttons)
                else:
                    await waha_client.send_text(phone, content)
                
                results["sent"] += 1
                
            except Exception as e:
                logger.error(f"Erro ao enviar resposta: {e}")
                results["failed"] += 1
        
        return results
    
    async def get_context(self, phone: str):
        """Obtém contexto (compatibilidade V1)."""
        # V2 usa ContextManager internamente
        # Retornar None para compatibilidade
        return None
    
    async def save_context(self, context):
        """Salva contexto (compatibilidade V1)."""
        # V2 gerencia contextos automaticamente
        pass


# Singleton global (compatibilidade com código existente)
flow_engine = FlowEngineWrapper()
