"""
Flow Engine V2 - Orquestrador Principal
Sistema de gerenciamento de conversas com NLU híbrido e handlers modulares.

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md - Parte 6
"""

import logging
import time
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from uuid import uuid4

from app.core.state_machine_v2 import (
    ConversationState,
    ConversationContext,
    CustomerContext,
    OrderContext,
)
from app.core.nlu_engine_v2 import detect_intent, Intent, ExtractedEntities
from app.core.handlers_v2.base import BaseHandler, HandlerResult
from app.core.flow_config import (
    FEATURE_FLAGS,
    ROLLOUT_PERCENTAGE,
    CONTEXT_TTL_SECONDS,
    KPI_TARGETS,
)

logger = logging.getLogger(__name__)


class FlowEngineV2:
    """
    Orquestrador principal do Flow Engine 2.0.
    
    Responsabilidades:
    - Gerenciar ciclo de vida das conversas
    - Rotear mensagens para handlers apropriados
    - Gerenciar contextos (Customer, Conversation, Order)
    - Integrar com NLU Engine
    - Coletar métricas
    - Implementar fast-track e atalhos
    """
    
    def __init__(
        self,
        handler_registry: Dict[ConversationState, BaseHandler],
        context_manager: "ContextManager",
        metrics_collector: Optional["MetricsCollector"] = None,
    ):
        """
        Inicializa o Flow Engine V2.
        
        Args:
            handler_registry: Mapeamento de estados para handlers
            context_manager: Gerenciador de contextos
            metrics_collector: Coletor de métricas (opcional)
        """
        self.handler_registry = handler_registry
        self.context_manager = context_manager
        self.metrics_collector = metrics_collector
        
        logger.info("FlowEngineV2 inicializado com sucesso")
    
    async def process_message(
        self,
        phone: str,
        message: str,
        trace_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Processa uma mensagem recebida.
        
        Args:
            phone: Número de telefone do cliente
            message: Texto da mensagem
            trace_id: ID de rastreamento (gerado se não fornecido)
        
        Returns:
            Lista de respostas para enviar ao cliente
        """
        # Gerar trace_id se não fornecido
        if not trace_id:
            trace_id = str(uuid4())
        
        start_time = time.time()
        
        logger.info(
            f"[{trace_id}] Processando mensagem",
            extra={
                "trace_id": trace_id,
                "phone": phone,
                "message_length": len(message),
            }
        )
        
        try:
            # 1. Carregar ou criar contextos
            contexts = await self._load_contexts(phone, trace_id)
            conversation_context = contexts["conversation"]
            customer_context = contexts["customer"]
            order_context = contexts["order"]
            
            # 2. Detectar intenção e extrair entidades (NLU)
            intent, confidence, entities = await self._detect_intent(
                message,
                conversation_context,
                trace_id
            )
            
            logger.info(
                f"[{trace_id}] NLU detectou: {intent} (confiança: {confidence:.2f})",
                extra={
                    "trace_id": trace_id,
                    "intent": intent,
                    "confidence": confidence,
                    "entities": entities.__dict__ if entities else {},
                }
            )
            
            # 3. Verificar atalhos (fast-track)
            fast_track_result = await self._check_fast_track(
                intent,
                entities,
                conversation_context,
                customer_context,
                order_context,
                trace_id
            )
            
            if fast_track_result:
                logger.info(f"[{trace_id}] Fast-track ativado")
                return await self._finalize_response(
                    fast_track_result,
                    contexts,
                    phone,
                    start_time,
                    trace_id
                )
            
            # 4. Obter handler do estado atual
            current_state = conversation_context.current_state
            handler = self.handler_registry.get(current_state)
            
            if not handler:
                logger.error(
                    f"[{trace_id}] Handler não encontrado para estado: {current_state}"
                )
                # Fallback para error recovery
                handler = self.handler_registry.get(ConversationState.ERROR_RECOVERY)
                if not handler:
                    raise ValueError(f"Handler não encontrado: {current_state}")
            
            # 5. Processar mensagem com handler
            logger.debug(
                f"[{trace_id}] Executando handler: {handler.__class__.__name__}"
            )
            
            result = await handler.handle(
                message=message,
                conversation_context=conversation_context,
                customer_context=customer_context,
                order_context=order_context,
                entities=entities.__dict__ if entities else None,
            )
            
            # 6. Finalizar e retornar resposta
            return await self._finalize_response(
                result,
                contexts,
                phone,
                start_time,
                trace_id
            )
            
        except Exception as e:
            logger.error(
                f"[{trace_id}] Erro ao processar mensagem: {e}",
                exc_info=True,
                extra={"trace_id": trace_id, "phone": phone}
            )
            
            # Coletar métrica de erro
            if self.metrics_collector:
                self.metrics_collector.increment_error_count(
                    error_type=type(e).__name__
                )
            
            # Retornar mensagem de erro genérica
            return [{
                "type": "text",
                "text": "❌ Ocorreu um erro. Por favor, tente novamente ou digite *atendente* para falar com alguém.",
            }]
    
    async def _load_contexts(
        self,
        phone: str,
        trace_id: str,
    ) -> Dict[str, any]:
        """
        Carrega ou cria contextos da conversa.
        
        Args:
            phone: Número de telefone
            trace_id: ID de rastreamento
        
        Returns:
            Dicionário com conversation, customer e order contexts
        """
        # Carregar contexto da conversa
        conversation_context = await self.context_manager.get_conversation_context(phone)
        
        if not conversation_context:
            # Criar novo contexto
            conversation_context = ConversationContext(
                phone=phone,
                current_state=ConversationState.GREETING_INITIAL,
            )
            logger.info(f"[{trace_id}] Novo contexto criado para {phone}")
        else:
            logger.debug(
                f"[{trace_id}] Contexto carregado: estado={conversation_context.current_state}"
            )
        
        # Carregar contexto do cliente
        customer_context = await self.context_manager.get_customer_context(phone)
        
        # Carregar contexto do pedido
        order_context = await self.context_manager.get_order_context(phone)
        
        if not order_context:
            order_context = OrderContext()
        
        return {
            "conversation": conversation_context,
            "customer": customer_context,
            "order": order_context,
        }
    
    async def _detect_intent(
        self,
        message: str,
        conversation_context: ConversationContext,
        trace_id: str,
    ) -> Tuple[Intent, float, Optional[ExtractedEntities]]:
        """
        Detecta intenção e extrai entidades da mensagem.
        
        Args:
            message: Texto da mensagem
            conversation_context: Contexto da conversa
            trace_id: ID de rastreamento
        
        Returns:
            Tupla (intent, confidence, entities)
        """
        # Preparar contexto para NLU
        nlu_context = {
            "current_state": conversation_context.current_state.value,
            "collected_data": conversation_context.collected_data,
            "is_returning": conversation_context.is_returning,
        }
        
        # Detectar intenção
        intent, confidence, entities = await detect_intent(message, nlu_context)
        
        # Coletar métrica de NLU
        if self.metrics_collector:
            self.metrics_collector.record_nlu_confidence(
                intent=intent.value,
                confidence=confidence
            )
        
        return intent, confidence, entities
    
    async def _check_fast_track(
        self,
        intent: Intent,
        entities: Optional[ExtractedEntities],
        conversation_context: ConversationContext,
        customer_context: Optional[CustomerContext],
        order_context: OrderContext,
        trace_id: str,
    ) -> Optional[HandlerResult]:
        """
        Verifica se pode usar fast-track (atalho inteligente).
        
        Fast-track permite pular estados quando:
        - Cliente conhecido quer repetir pedido
        - Mensagem contém todas as informações necessárias
        - Cliente está em estado que permite atalho
        
        Args:
            intent: Intenção detectada
            entities: Entidades extraídas
            conversation_context: Contexto da conversa
            customer_context: Contexto do cliente
            order_context: Contexto do pedido
            trace_id: ID de rastreamento
        
        Returns:
            HandlerResult se fast-track ativado, None caso contrário
        """
        # Fast-track desabilitado
        if not FEATURE_FLAGS.get("fast_track_enabled", True):
            return None
        
        # Fast-track: Repetir pedido
        if intent == Intent.REPEAT_ORDER and customer_context and customer_context.last_order:
            logger.info(f"[{trace_id}] Fast-track: Repetir pedido")
            
            # Usar handler de confirmação de repetição
            handler = self.handler_registry.get(ConversationState.ORDERING_CONFIRM_REPEAT)
            if handler:
                return await handler.handle(
                    message="confirm_repeat",
                    conversation_context=conversation_context,
                    customer_context=customer_context,
                    order_context=order_context,
                    entities=None,
                )
        
        # Fast-track: Pedido completo em uma mensagem
        if (
            intent == Intent.BUY
            and entities
            and entities.product
            and entities.quantity
            and customer_context
            and customer_context.addresses
        ):
            logger.info(f"[{trace_id}] Fast-track: Pedido completo detectado")
            
            # TODO: Implementar lógica de fast-track completo
            # Por enquanto, retorna None para seguir fluxo normal
            pass
        
        return None
    
    async def _finalize_response(
        self,
        result: HandlerResult,
        contexts: Dict[str, any],
        phone: str,
        start_time: float,
        trace_id: str,
    ) -> List[Dict]:
        """
        Finaliza processamento e prepara resposta.
        
        Args:
            result: Resultado do handler
            contexts: Dicionários de contextos
            phone: Número de telefone
            start_time: Timestamp de início
            trace_id: ID de rastreamento
        
        Returns:
            Lista de respostas formatadas
        """
        conversation_context = contexts["conversation"]
        customer_context = contexts["customer"]
        order_context = contexts["order"]
        
        # Atualizar estado da conversa
        if result.next_state:
            # Adicionar ao histórico
            conversation_context.state_history.append(
                conversation_context.current_state.value
            )
            
            # Atualizar estado atual
            conversation_context.current_state = result.next_state
            
            logger.debug(
                f"[{trace_id}] Transição: {conversation_context.state_history[-1]} → {result.next_state.value}"
            )
        
        # Atualizar flag de atendimento humano
        if result.needs_human:
            conversation_context.needs_human = True
        
        # Salvar contextos atualizados
        await self.context_manager.save_conversation_context(phone, conversation_context)
        
        if customer_context:
            await self.context_manager.save_customer_context(phone, customer_context)
        
        if order_context:
            await self.context_manager.save_order_context(phone, order_context)
        
        # Calcular tempo de processamento
        processing_time = (time.time() - start_time) * 1000  # ms
        
        # Coletar métricas
        if self.metrics_collector:
            self.metrics_collector.record_processing_time(processing_time)
            self.metrics_collector.record_state_transition(
                from_state=conversation_context.state_history[-1] if conversation_context.state_history else None,
                to_state=result.next_state.value if result.next_state else None,
            )
        
        logger.info(
            f"[{trace_id}] Processamento concluído em {processing_time:.2f}ms",
            extra={
                "trace_id": trace_id,
                "processing_time_ms": processing_time,
                "next_state": result.next_state.value if result.next_state else None,
                "response_count": len(result.responses),
            }
        )
        
        # Verificar se tempo está dentro da meta
        if processing_time > KPI_TARGETS.get("max_response_time_ms", 1000):
            logger.warning(
                f"[{trace_id}] Tempo de resposta acima da meta: {processing_time:.2f}ms"
            )
        
        # Formatar respostas (MessageResponse tem: text, buttons, image_url, image_base64, footer)
        formatted_responses = []
        for response in result.responses:
            resp_type = "image" if (getattr(response, "image_url", None) or getattr(response, "image_base64", None)) else "text"
            formatted_responses.append({
                "type": resp_type,
                "text": response.text,
                "buttons": response.buttons,
                "media_url": getattr(response, "image_url", None) or getattr(response, "media_url", None),
            })
        
        return formatted_responses
    
    async def get_conversation_status(self, phone: str) -> Dict:
        """
        Obtém status atual da conversa.
        
        Args:
            phone: Número de telefone
        
        Returns:
            Dicionário com status da conversa
        """
        conversation_context = await self.context_manager.get_conversation_context(phone)
        customer_context = await self.context_manager.get_customer_context(phone)
        order_context = await self.context_manager.get_order_context(phone)
        
        if not conversation_context:
            return {
                "exists": False,
                "phone": phone,
            }
        
        return {
            "exists": True,
            "phone": phone,
            "current_state": conversation_context.current_state.value,
            "is_returning": conversation_context.is_returning,
            "needs_human": conversation_context.needs_human,
            "customer_id": customer_context.customer_id if customer_context else None,
            "customer_name": customer_context.name if customer_context else None,
            "order_items_count": len(order_context.items) if order_context else 0,
            "order_total": order_context.total if order_context else 0.0,
        }
    
    async def reset_conversation(self, phone: str) -> bool:
        """
        Reseta conversa para o estado inicial.
        
        Args:
            phone: Número de telefone
        
        Returns:
            True se resetado com sucesso
        """
        try:
            await self.context_manager.delete_conversation_context(phone)
            await self.context_manager.delete_order_context(phone)
            
            logger.info(f"Conversa resetada para {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao resetar conversa: {e}", exc_info=True)
            return False
