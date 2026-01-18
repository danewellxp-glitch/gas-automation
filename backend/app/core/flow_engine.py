"""
Flow Engine - Processador principal de mensagens do WhatsApp.
Gerencia o fluxo de conversa e delega para handlers específicos.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable
from datetime import datetime

from app.config import settings
from app.database import redis_manager, AsyncSessionLocal
from app.models.event_log import EventLog
from app.core.state_machine import ConversationState, ConversationContext
from app.integrations.waha import waha_client

logger = logging.getLogger(__name__)


@dataclass
class MessageResponse:
    """Resposta a ser enviada ao usuário."""

    text: str
    buttons: Optional[list[dict]] = None
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    footer: Optional[str] = None

    def has_buttons(self) -> bool:
        return bool(self.buttons)


@dataclass
class ProcessedMessage:
    """Resultado do processamento de uma mensagem."""

    context: ConversationContext
    responses: list[MessageResponse]
    new_state: ConversationState
    success: bool = True
    error: Optional[str] = None


# Tipo para handlers de estado
StateHandler = Callable[[ConversationContext, str], Awaitable[ProcessedMessage]]


class FlowEngine:
    """
    Motor principal do fluxo de conversa.

    Responsabilidades:
    - Carregar/salvar contexto do Redis
    - Determinar handler baseado no estado
    - Processar mensagem e retornar respostas
    - Gerenciar transições de estado
    """

    def __init__(self):
        self._handlers: dict[ConversationState, StateHandler] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Registra handlers para cada estado."""
        from app.core.handlers import (
            handle_start,
            handle_awaiting_product,
            handle_awaiting_quantity,
            handle_confirming_address,
            handle_awaiting_address,
            handle_awaiting_payment,
            handle_awaiting_pix,
            handle_order_confirmed,
            handle_tracking_order,
            handle_talking_to_human,
        )

        self._handlers = {
            ConversationState.START: handle_start,
            ConversationState.AWAITING_PRODUCT: handle_awaiting_product,
            ConversationState.AWAITING_QUANTITY: handle_awaiting_quantity,
            ConversationState.CONFIRMING_ADDRESS: handle_confirming_address,
            ConversationState.AWAITING_ADDRESS: handle_awaiting_address,
            ConversationState.AWAITING_PAYMENT: handle_awaiting_payment,
            ConversationState.AWAITING_PIX: handle_awaiting_pix,
            ConversationState.ORDER_CONFIRMED: handle_order_confirmed,
            ConversationState.TRACKING_ORDER: handle_tracking_order,
            ConversationState.TALKING_TO_HUMAN: handle_talking_to_human,
        }

    async def get_context(self, phone: str) -> ConversationContext:
        """Carrega contexto da conversa do Redis ou cria um novo."""
        data = await redis_manager.get_conversation_state(phone)

        if data:
            context = ConversationContext.from_dict(data)
            logger.debug(f"Contexto carregado para {phone}: {context.state}")
        else:
            context = ConversationContext(phone=phone)
            logger.debug(f"Novo contexto criado para {phone}")

        return context

    async def save_context(self, context: ConversationContext) -> None:
        """Salva contexto da conversa no Redis."""
        context.last_message_at = datetime.utcnow()
        await redis_manager.set_conversation_state(
            context.phone,
            context.to_dict(),
            ttl=settings.redis_conversation_ttl
        )
        logger.debug(f"Contexto salvo para {context.phone}: {context.state}")

    async def process_message(
        self,
        phone: str,
        message: str,
        message_id: Optional[str] = None,
    ) -> ProcessedMessage:
        """
        Processa uma mensagem recebida.

        Args:
            phone: Número do telefone do cliente
            message: Texto da mensagem
            message_id: ID da mensagem (para marcar como lida)

        Returns:
            ProcessedMessage com respostas e novo estado
        """
        # Carregar contexto
        context = await self.get_context(phone)
        context.message_count += 1

        logger.info(
            f"Processando mensagem de {phone} | "
            f"Estado: {context.state} | "
            f"Mensagem: {message[:50]}..."
        )

        # Verificar comandos globais
        global_result = await self._check_global_commands(context, message)
        if global_result:
            await self.save_context(global_result.context)
            return global_result

        # Obter handler do estado atual
        handler = self._handlers.get(context.state)

        if not handler:
            logger.warning(f"Sem handler para estado {context.state}")
            handler = self._handlers[ConversationState.START]
            context.state = ConversationState.START

        try:
            # Processar mensagem
            result = await handler(context, message)

            # Salvar contexto atualizado
            await self.save_context(result.context)

            # Marcar mensagem como lida
            if message_id:
                try:
                    await waha_client.mark_as_read(phone, message_id)
                except Exception:
                    pass  # Não crítico

            return result

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text="Desculpe, ocorreu um erro. Por favor, tente novamente ou digite *menu* para recomeçar."
                    )
                ],
                new_state=context.state,
                success=False,
                error=str(e),
            )

    async def _check_global_commands(
        self,
        context: ConversationContext,
        message: str,
    ) -> Optional[ProcessedMessage]:
        """
        Verifica comandos globais que funcionam em qualquer estado.

        Comandos:
        - menu / inicio / voltar: Volta ao menu inicial
        - cancelar: Cancela pedido em andamento
        - ajuda / help: Mostra ajuda
        - atendente / humano: Transfere para atendente
        """
        msg_lower = message.lower().strip()

        # Voltar ao menu
        if msg_lower in ["menu", "inicio", "início", "voltar", "0"]:
            context.reset()
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text=(
                            "🏠 *Menu Principal*\n\n"
                            "Olá! Bem-vindo à *Distribuidora de Gás*! 🔥\n\n"
                            "Como posso ajudar?"
                        ),
                        buttons=[
                            {"id": "fazer_pedido", "text": "🛒 Fazer Pedido"},
                            {"id": "ver_pedido", "text": "📦 Meus Pedidos"},
                            {"id": "falar_atendente", "text": "👤 Atendente"},
                        ],
                    )
                ],
                new_state=ConversationState.AWAITING_PRODUCT,
            )

        # Cancelar
        if msg_lower in ["cancelar", "cancela"]:
            if context.order_id:
                # TODO: Cancelar pedido no banco
                context.reset()
                return ProcessedMessage(
                    context=context,
                    responses=[
                        MessageResponse(
                            text="❌ Pedido cancelado.\n\nDigite *menu* para fazer um novo pedido."
                        )
                    ],
                    new_state=ConversationState.START,
                )
            else:
                context.reset()
                return ProcessedMessage(
                    context=context,
                    responses=[
                        MessageResponse(text="Não há pedido em andamento. Digite *menu* para começar.")
                    ],
                    new_state=ConversationState.START,
                )

        # Ajuda
        if msg_lower in ["ajuda", "help", "?"]:
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text=(
                            "ℹ️ *Ajuda*\n\n"
                            "Comandos disponíveis:\n"
                            "• *menu* - Voltar ao menu principal\n"
                            "• *cancelar* - Cancelar pedido\n"
                            "• *atendente* - Falar com atendente\n\n"
                            "Produtos disponíveis:\n"
                            "• *P13* - Botijão 13kg - R$ 110,00\n"
                            "• *P20* - Botijão 20kg - R$ 150,00\n"
                            "• *P45* - Botijão 45kg - R$ 280,00\n\n"
                            "Para fazer um pedido, digite *menu*."
                        )
                    )
                ],
                new_state=context.state,
            )

        # Falar com atendente
        if msg_lower in ["atendente", "humano", "pessoa", "atendimento"]:
            context.state = ConversationState.TALKING_TO_HUMAN
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text=(
                            "👤 *Atendimento Humano*\n\n"
                            "Estou transferindo você para um de nossos atendentes.\n"
                            "Por favor, aguarde que em breve alguém irá atendê-lo.\n\n"
                            "⏰ Horário de atendimento: 8h às 20h"
                        )
                    )
                ],
                new_state=ConversationState.TALKING_TO_HUMAN,
            )

        return None

    async def send_responses(
        self,
        phone: str,
        responses: list[MessageResponse],
    ) -> None:
        """Envia as respostas ao cliente via WAHA."""
        for response in responses:
            try:
                if response.image_url or response.image_base64:
                    await waha_client.send_image(
                        phone=phone,
                        image_url=response.image_url,
                        image_base64=response.image_base64,
                        caption=response.text,
                    )
                elif response.has_buttons():
                    await waha_client.send_buttons(
                        phone=phone,
                        text=response.text,
                        buttons=response.buttons,
                        footer=response.footer,
                    )
                else:
                    await waha_client.send_text(
                        phone=phone,
                        text=response.text,
                    )

                # Salvar mensagem enviada no EventLog
                async with AsyncSessionLocal() as db:
                    event = EventLog(
                        event_type="message_sent",
                        entity_type="chat",
                        payload={"phone": phone, "message": response.text}
                    )
                    db.add(event)
                    await db.commit()

            except Exception as e:
                logger.error(f"Erro ao enviar resposta para {phone}: {e}")


# Instância global
flow_engine = FlowEngine()
