"""
Flow Engine - Processador principal de mensagens do WhatsApp.
Usa deteccao de intencao e extracao de entidades (NLP) para
fluxo conversacional inteligente em vez de menus rigidos.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, List, Dict
from datetime import datetime, timezone

from app.config import settings
from app.database import redis_manager, AsyncSessionLocal
from app.models.event_log import EventLog
from app.core.state_machine import ConversationState, ConversationContext
import re
from app.core.nlp_utils import (
    normalize_text,
    detect_intention,
    extract_entities,
    extract_product,
    Intention,
)
from app.integrations.waha import waha_client
from app.models.product import OPTION_TO_CODE, DEFAULT_PRODUCT_CODES

logger = logging.getLogger(__name__)


@dataclass
class MessageResponse:
    """Resposta a ser enviada ao usuario."""

    text: str
    buttons: Optional[List[Dict]] = None
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    footer: Optional[str] = None

    def has_buttons(self) -> bool:
        return bool(self.buttons)


@dataclass
class ProcessedMessage:
    """Resultado do processamento de uma mensagem."""

    context: ConversationContext
    responses: List[MessageResponse]
    new_state: ConversationState
    success: bool = True
    error: Optional[str] = None


# Tipo para handlers de estado
StateHandler = Callable[[ConversationContext, str], Awaitable[ProcessedMessage]]


class FlowEngine:
    """
    Motor principal do fluxo de conversa.

    Fluxo hibrido: usa NLP para deteccao de intencao no estado START
    e delega para handlers especificos nos estados intermediarios.
    Nos estados intermediarios, tambem extrai entidades inline.
    """

    def __init__(self):
        self._handlers: Dict[ConversationState, StateHandler] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Registra handlers para cada estado."""
        from app.core.handlers import (
            handle_start,
            handle_asking_customer_type,
            handle_collecting_name,
            handle_collecting_document,
            handle_awaiting_product,
            handle_awaiting_quantity,
            handle_confirming_address,
            handle_awaiting_address,
            handle_awaiting_payment,
            handle_awaiting_pix,
            handle_confirming_order,
            handle_order_confirmed,
            handle_tracking_order,
            handle_talking_to_human,
        )

        self._handlers = {
            ConversationState.START: handle_start,
            ConversationState.ASKING_CUSTOMER_TYPE: handle_asking_customer_type,
            ConversationState.COLLECTING_NAME: handle_collecting_name,
            ConversationState.COLLECTING_DOCUMENT: handle_collecting_document,
            ConversationState.AWAITING_PRODUCT: handle_awaiting_product,
            ConversationState.AWAITING_QUANTITY: handle_awaiting_quantity,
            ConversationState.CONFIRMING_ADDRESS: handle_confirming_address,
            ConversationState.AWAITING_ADDRESS: handle_awaiting_address,
            ConversationState.AWAITING_PAYMENT: handle_awaiting_payment,
            ConversationState.AWAITING_PIX: handle_awaiting_pix,
            ConversationState.CONFIRMING_ORDER: handle_confirming_order,
            ConversationState.ORDER_CONFIRMED: handle_order_confirmed,
            ConversationState.TRACKING_ORDER: handle_tracking_order,
            ConversationState.TALKING_TO_HUMAN: handle_talking_to_human,
        }

    async def get_context(self, phone: str) -> ConversationContext:
        """
        Carrega contexto da conversa.

        Prioridade:
        1. Redis (rapido, TTL 30min)
        2. PostgreSQL snapshot (fallback, TTL 24h)
        3. Novo contexto vazio
        """
        data = await redis_manager.get_conversation_state(phone)

        if data:
            context = ConversationContext.from_dict(data)
            logger.debug(f"Contexto carregado do Redis para {phone}: {context.state}")
            return context

        # Fallback: tentar recuperar do PostgreSQL (pedido abandonado)
        try:
            context = await self._load_snapshot(phone)
            if context:
                logger.info(f"Contexto recuperado do snapshot PostgreSQL para {phone}: {context.state}")
                return context
        except Exception as e:
            logger.warning(f"Erro ao carregar snapshot para {phone}: {e}")

        context = ConversationContext(phone=phone)
        logger.debug(f"Novo contexto criado para {phone}")
        return context

    async def _load_snapshot(self, phone: str) -> Optional[ConversationContext]:
        """Carrega snapshot do PostgreSQL se existir e tiver menos de 24h."""
        from sqlalchemy import select
        from app.models.conversation_snapshot import ConversationSnapshot

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ConversationSnapshot).where(ConversationSnapshot.phone == phone)
            )
            snapshot = result.scalar_one_or_none()

        if not snapshot:
            return None

        # Verificar se snapshot tem menos de 24h
        updated = snapshot.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - updated
        if age.total_seconds() > 86400:  # 24 horas
            logger.debug(f"Snapshot de {phone} expirado ({age})")
            return None

        # Restaurar contexto do snapshot
        context = ConversationContext.from_dict(snapshot.context_json)
        context.resumed_from_snapshot = True
        # Limpar dados transitorios
        context.pending_entities = {}
        context.recent_messages = []
        context.retry_count = 0
        return context

    async def save_context(
        self,
        context: ConversationContext,
        previous_state: Optional[ConversationState] = None,
    ) -> None:
        """Salva contexto da conversa no Redis + PostgreSQL (backup).

        Args:
            context: Contexto atualizado da conversa
            previous_state: Estado anterior (se fornecido, só salva snapshot
                           no PostgreSQL quando o estado muda)
        """
        context.last_message_at = datetime.now(timezone.utc)
        context_dict = context.to_dict()

        # 1. Salvar no Redis (primário, rápido) — sempre
        await redis_manager.set_conversation_state(
            context.phone,
            context_dict,
            ttl=settings.redis_conversation_ttl
        )
        logger.debug(f"Contexto salvo no Redis para {context.phone}: {context.state}")

        # 2. Upsert no PostgreSQL (backup, best-effort)
        # Só salva quando o estado muda (reduz ~80% dos writes)
        state_changed = previous_state is None or previous_state != context.state
        if state_changed:
            try:
                await self._save_snapshot(context.phone, context.state.value, context_dict)
            except Exception as e:
                logger.warning(f"Erro ao salvar snapshot PostgreSQL para {context.phone}: {e}")

    async def _save_snapshot(self, phone: str, state: str, context_dict: dict) -> None:
        """Upsert do snapshot no PostgreSQL."""
        from sqlalchemy.dialects.postgresql import insert
        from app.models.conversation_snapshot import ConversationSnapshot

        async with AsyncSessionLocal() as db:
            stmt = insert(ConversationSnapshot).values(
                phone=phone,
                state=state,
                context_json=context_dict,
            ).on_conflict_do_update(
                index_elements=["phone"],
                set_={
                    "state": state,
                    "context_json": context_dict,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await db.execute(stmt)
            await db.commit()

    async def process_message(
        self,
        phone: str,
        message: str,
        message_id: Optional[str] = None,
    ) -> ProcessedMessage:
        """
        Processa uma mensagem recebida com NLP.

        Novo fluxo:
        1. Carrega contexto
        2. Normaliza texto e extrai entidades
        3. Detecta intencao com hierarquia de prioridades
        4. Mescla entidades no contexto
        5. Roteia para handler baseado em intencao + estado
        """
        # DEBUG: Normalizar phone para evitar inconsistencias de formato WAHA
        # WAHA pode enviar @lid ou @c.us - normalizamos para garantir mesma chave Redis
        original_phone = phone
        if "@" in phone:
            # Extrair apenas o numero para usar como chave consistente
            phone = phone.split("@")[0]
        logger.info(f"[DEBUG] Phone original: {original_phone} -> normalizado: {phone}")

        # Carregar contexto
        context = await self.get_context(phone)
        previous_state = context.state  # Guardar para otimizar snapshot
        logger.info(f"[DEBUG-1] Estado CARREGADO do Redis: {context.state} (phone={phone})")
        context.message_count += 1

        # Guardar mensagem no historico recente (ultimas 3)
        context.recent_messages.append(message)
        if len(context.recent_messages) > 3:
            context.recent_messages = context.recent_messages[-3:]

        logger.info(
            f"Processando mensagem de {phone} | "
            f"Estado: {context.state} | "
            f"Mensagem: {message[:50]}..."
        )

        # Extrair entidades da mensagem (produto, quantidade, pagamento, etc)
        entities = extract_entities(message, settings.supported_bairros)
        if entities:
            context.pending_entities.update(entities)
            logger.info(f"Entidades extraidas: {entities}")

        # Detectar intencao com NLP
        intention = detect_intention(message, context)
        context.last_intent = intention
        logger.info(f"Intencao detectada: {intention}")

        # Verificar comandos globais via NLP (prioridade alta)
        global_result = await self._check_global_commands_nlp(context, message, intention)
        if global_result:
            global_result.context.state = global_result.new_state
            await self.save_context(global_result.context, previous_state=previous_state)
            # mark_as_read agora é feito no webhook (feedback imediato)
            return global_result

        # Roteamento inteligente baseado em intencao + estado
        try:
            result = await self._route_message(context, message, intention)

            # IMPORTANTE: Sincronizar estado no contexto para persistir no Redis
            result.context.state = result.new_state
            await self.save_context(result.context, previous_state=previous_state)
            # mark_as_read agora é feito no webhook (feedback imediato)

            return result

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text="Desculpe, ocorreu um erro. Por favor, tente novamente ou digite *menu* para recomecar."
                    )
                ],
                new_state=context.state,
                success=False,
                error=str(e),
            )

    async def _route_message(
        self,
        context: ConversationContext,
        message: str,
        intention: str,
    ) -> ProcessedMessage:
        """
        Roteia a mensagem para o handler apropriado baseado em intencao + estado.

        Logica:
        - Se esta em estado intermediario (AWAITING_*), respeita o estado
          mas permite interrupcoes por intencoes de alta prioridade
        - Se esta em START, usa intencao para determinar proximo passo
        - Se intencao UNKNOWN em estado intermediario, tenta interpretar
          como resposta ao que foi perguntado
        """
        from app.core.handlers import (
            handle_start,
            handle_tracking_order,
            handle_talking_to_human,
            handle_greeting,
            handle_collect_missing_data,
            handle_show_confirmation,
            handle_not_understood,
            handle_emergency,
        )

        # --- Emergencia: prioridade maxima em qualquer estado ---
        if intention == Intention.EMERGENCY:
            return await handle_emergency(context, message)

        # --- Se esta falando com humano, manter no estado ---
        if context.state == ConversationState.TALKING_TO_HUMAN:
            return await handle_talking_to_human(context, message)

        # --- Intencoes que interrompem qualquer estado ---
        if intention == Intention.TRACK:
            return await handle_tracking_order(context, message)

        if intention == Intention.HUMAN:
            return await handle_talking_to_human(context, message)

        # --- Mapeamento de números para button IDs do menu principal ---
        msg_lower = message.strip().lower()
        MENU_NUMBER_MAPPING = {
            "1": "fazer_pedido",
            "2": "ver_pedido",
            "3": "falar_atendente",
        }
        if msg_lower in MENU_NUMBER_MAPPING:
            msg_lower = MENU_NUMBER_MAPPING[msg_lower]
            logger.info(f"Número '{message.strip()}' mapeado para '{msg_lower}'")

        # --- Botoes de pedido abandonado recuperado ---
        if msg_lower == "continuar_pedido":
            # Retomar fluxo do estado atual (handler do estado)
            handler = self._handlers.get(context.state)
            if handler:
                return await handler(context, message)
            return await handle_greeting(context, message)

        if msg_lower == "recomecar":
            context.reset()
            return await handle_greeting(context, message)

        # --- Botoes do menu principal (fazer_pedido, ver_pedido, falar_atendente) ---
        if msg_lower == "fazer_pedido":
            return await handle_greeting(context, message)

        if msg_lower == "ver_pedido":
            return await handle_tracking_order(context, message)

        if msg_lower == "falar_atendente":
            return await handle_talking_to_human(context, message)

        # --- FAQ: responder e manter estado atual ---
        if intention == Intention.INFO:
            from app.core.nlp_utils import detect_faq_category
            from app.core.handlers import handle_faq
            faq_cat = detect_faq_category(normalize_text(message))
            if faq_cat:
                return await handle_faq(context, message, faq_cat)

        # --- Estados de coleta de dados (identificacao) ---
        if context.state == ConversationState.ASKING_CUSTOMER_TYPE:
            from app.core.handlers import handle_asking_customer_type
            return await handle_asking_customer_type(context, message)

        if context.state == ConversationState.COLLECTING_NAME:
            from app.core.handlers import handle_collecting_name
            return await handle_collecting_name(context, message)

        if context.state == ConversationState.COLLECTING_DOCUMENT:
            from app.core.handlers import handle_collecting_document
            return await handle_collecting_document(context, message)

        # --- Estado START: roteamento por intencao ---
        if context.state == ConversationState.START:
            return await self._handle_start_state(context, message, intention)

        # --- Repetir pedido ---
        if intention == Intention.REPEAT_ORDER:
            from app.core.handlers import handle_repeat_order
            return await handle_repeat_order(context, message)

        # --- Estados intermediarios: rotear para fluxo conversacional ---
        if context.state in (
            ConversationState.AWAITING_PRODUCT,
            ConversationState.AWAITING_QUANTITY,
            ConversationState.CONFIRMING_ADDRESS,
            ConversationState.AWAITING_ADDRESS,
            ConversationState.AWAITING_PAYMENT,
            ConversationState.CONFIRMING_ORDER,
        ):
            # Se confirmacao/negacao em estado de confirmacao
            if context.state == ConversationState.CONFIRMING_ORDER:
                if intention == Intention.CONFIRM:
                    from app.core.handlers import handle_confirm_order
                    return await handle_confirm_order(context, message)
                if intention in (Intention.DENY, Intention.EDIT):
                    from app.core.handlers import handle_edit_order
                    return await handle_edit_order(context, message)

            if context.state == ConversationState.CONFIRMING_ADDRESS:
                if intention == Intention.CONFIRM:
                    handler = self._handlers.get(ConversationState.CONFIRMING_ADDRESS)
                    return await handler(context, "sim")
                if intention == Intention.DENY:
                    handler = self._handlers.get(ConversationState.CONFIRMING_ADDRESS)
                    return await handler(context, "alterar")

            # Enriquecer pending_entities de entradas curtas (1, 2, 3, P13, qty_1, etc)
            self._enrich_pending_from_state(context, message)

            # Se temos dados novos ou ja tinhamos BUY, usar fluxo conversacional
            if context.pending_entities or intention == Intention.BUY:
                return await handle_collect_missing_data(context, message)

            # Fallback: handler do estado atual
            handler = self._handlers.get(context.state)
            if handler:
                return await handler(context, message)

        # --- Estado ORDER_CONFIRMED ---
        if context.state == ConversationState.ORDER_CONFIRMED:
            handler = self._handlers.get(ConversationState.ORDER_CONFIRMED)
            if handler:
                return await handler(context, message)

        # --- Fallback: handler de inicio ---
        return await handle_start(context, message)

    async def _handle_start_state(
        self,
        context: ConversationContext,
        message: str,
        intention: str,
    ) -> ProcessedMessage:
        """Roteamento no estado START baseado em intencao NLP."""
        from app.core.handlers import (
            handle_greeting,
            handle_collect_missing_data,
            handle_not_understood,
            handle_tracking_order,
            handle_talking_to_human,
            handle_start,
        )

        if intention == Intention.GREETING:
            return await handle_greeting(context, message)

        # Botao "Sim, o de sempre" envia id "repeat_order"
        if message.strip().lower() == "repeat_order" or intention == Intention.REPEAT_ORDER:
            from app.core.handlers import handle_repeat_order
            return await handle_repeat_order(context, message)

        if intention == Intention.BUY:
            # Verificar se ja tem entidades suficientes para atalho
            if self._has_complete_order_data(context):
                from app.core.handlers import handle_show_confirmation
                return await handle_show_confirmation(context, message)
            # Tem pelo menos produto? Pula para coleta do que falta
            if context.pending_entities.get("product") or context.selected_product:
                return await handle_collect_missing_data(context, message)
            # Saudacao + intencao de compra -> trata como greeting com sugestao
            return await handle_greeting(context, message)

        if intention == Intention.TRACK:
            return await handle_tracking_order(context, message)

        if intention == Intention.HUMAN:
            return await handle_talking_to_human(context, message)

        if intention == Intention.CONFIRM:
            # Confirmacao sem contexto - provavelmente resposta a sugestao
            if context.pending_entities:
                return await handle_collect_missing_data(context, message)
            return await handle_start(context, message)

        if intention == Intention.UNKNOWN:
            return await handle_not_understood(context, message)

        # Fallback para qualquer outra intencao
        return await handle_start(context, message)

    def _enrich_pending_from_state(
        self,
        context: ConversationContext,
        message: str,
    ) -> None:
        """
        Enriquece pending_entities a partir de entradas curtas (1, 2, 3, P13, qty_1)
        quando o usuario responde ao menu com numero ou botao.
        """
        msg = message.strip()
        pe = context.pending_entities

        if context.state == ConversationState.AWAITING_PRODUCT:
            product = None
            if not pe.get("product"):
                product = extract_product(message)
                if not product:
                    product = OPTION_TO_CODE.get(msg)
                if not product and msg.upper() in DEFAULT_PRODUCT_CODES:
                    product = msg.upper()
            if product:
                pe["product"] = product
                logger.debug(f"Produto extraido da mensagem: {product}")

        elif context.state == ConversationState.AWAITING_QUANTITY:
            quantity = None
            if not pe.get("quantity"):
                if msg.startswith("qty_"):
                    try:
                        quantity = int(msg.replace("qty_", ""))
                    except ValueError:
                        pass
                if quantity is None:
                    numbers = re.findall(r"\d+", message)
                    if numbers:
                        q = int(numbers[0])
                        if 1 <= q <= 10:
                            quantity = q
            if quantity is not None:
                pe["quantity"] = quantity
                context.selected_quantity = quantity
                logger.debug(f"Quantidade extraida da mensagem: {quantity}")

        elif context.state == ConversationState.AWAITING_ADDRESS:
            if not context.address and len(msg) >= 10:
                pe["address_raw"] = msg
                logger.debug("Endereco extraido da mensagem")

        elif context.state == ConversationState.AWAITING_PAYMENT:
            if not pe.get("payment") and not context.payment_method:
                ml = msg.lower()
                if "dinheiro" in ml or ml in ("2", "dinheiro"):
                    pe["payment"] = "cash"
                elif "cartao" in ml or "cartão" in ml or ml in ("3", "cartao", "cartão"):
                    pe["payment"] = "credit_card"
                elif "pix" in ml or ml == "1":
                    pe["payment"] = "pix"

    def _has_complete_order_data(self, context: ConversationContext) -> bool:
        """Verifica se tem todos os dados para finalizar pedido."""
        pe = context.pending_entities

        has_product = pe.get("product") or context.selected_product
        has_quantity = pe.get("quantity") or context.selected_quantity > 0
        has_address = pe.get("address_raw") or context.address
        has_payment = pe.get("payment") or context.payment_method

        return all([has_product, has_address, has_payment])

    async def _check_global_commands_nlp(
        self,
        context: ConversationContext,
        message: str,
        intention: str,
    ) -> Optional[ProcessedMessage]:
        """
        Verifica comandos globais usando NLP em vez de match exato.
        """
        # MENU: volta ao inicio
        if intention == Intention.MENU:
            context.reset()
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text=(
                            "Ola! Bem-vindo a *GasMaster*!\n\n"
                            "Como posso ajudar?"
                        ),
                        buttons=[
                            {"id": "fazer_pedido", "text": "Fazer Pedido"},
                            {"id": "ver_pedido", "text": "Meus Pedidos"},
                            {"id": "falar_atendente", "text": "Atendente"},
                        ],
                    )
                ],
                new_state=ConversationState.START,
            )

        # CANCELAR: cancela pedido em andamento
        if intention == Intention.CANCEL:
            return await self._handle_cancel(context)

        # AJUDA
        if intention == Intention.HELP:
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text=(
                            "*Ajuda*\n\n"
                            "Voce pode:\n"
                            "- Pedir gas escrevendo naturalmente (ex: 'quero 2 P13')\n"
                            "- Ver seus pedidos (ex: 'cade meu pedido')\n"
                            "- Falar com atendente (ex: 'quero falar com alguem')\n"
                            "- Cancelar pedido (ex: 'cancelar')\n"
                            "- Voltar ao menu (ex: 'menu')\n\n"
                            "Produtos disponiveis: P13, P20, P45"
                        )
                    )
                ],
                new_state=context.state,
            )

        return None

    async def _handle_cancel(
        self,
        context: ConversationContext,
    ) -> ProcessedMessage:
        """Cancela pedido em andamento."""
        if context.order_id:
            cancel_success = False
            try:
                from app.models.order import Order, OrderStatus
                from sqlalchemy import select

                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Order).where(Order.id == context.order_id)
                    )
                    order = result.scalar_one_or_none()
                    if order and order.status in [
                        OrderStatus.PENDING.value,
                        OrderStatus.PAID.value,
                    ]:
                        order.status = OrderStatus.CANCELLED.value
                        order.cancellation_reason = "Cancelado pelo cliente via bot"
                        await db.commit()
                        cancel_success = True
                        logger.info(f"Pedido {context.order_id} cancelado pelo cliente")
            except Exception as e:
                logger.error(f"Erro ao cancelar pedido {context.order_id}: {e}")

            context.reset()
            if cancel_success:
                return ProcessedMessage(
                    context=context,
                    responses=[
                        MessageResponse(
                            text="Pedido cancelado com sucesso.\n\nPosso ajudar com mais alguma coisa?",
                            buttons=[
                                {"id": "fazer_pedido", "text": "Novo Pedido"},
                                {"id": "falar_atendente", "text": "Atendente"},
                            ],
                        )
                    ],
                    new_state=ConversationState.START,
                )
            else:
                return ProcessedMessage(
                    context=context,
                    responses=[
                        MessageResponse(
                            text="Nao foi possivel cancelar o pedido. Vou te conectar com um atendente.",
                        )
                    ],
                    new_state=ConversationState.TALKING_TO_HUMAN,
                )
        else:
            # Sem pedido - reseta contexto do fluxo
            context.reset()
            return ProcessedMessage(
                context=context,
                responses=[
                    MessageResponse(
                        text="Nao ha pedido em andamento.\n\nPosso ajudar com mais alguma coisa?",
                        buttons=[
                            {"id": "fazer_pedido", "text": "Fazer Pedido"},
                            {"id": "ver_pedido", "text": "Meus Pedidos"},
                        ],
                    )
                ],
                new_state=ConversationState.START,
            )

    async def _mark_as_read(self, phone: str, message_id: str) -> None:
        """Marca mensagem como lida no WAHA."""
        try:
            await waha_client.mark_as_read(phone, message_id)
        except Exception as e:
            logger.debug(f"Nao foi possivel marcar mensagem como lida: {e}")

    async def send_responses(
        self,
        phone: str,
        responses: List[MessageResponse],
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
                logger.error(f"Erro ao enviar resposta para {phone}: {e}", exc_info=True)
                try:
                    await waha_client.send_text(
                        phone,
                        "Desculpe, houve um problema ao enviar. Digite *menu* para recomecar.",
                    )
                except Exception as fallback_err:
                    logger.error(f"Fallback send tambem falhou: {fallback_err}")


# Instancia global
flow_engine = FlowEngine()
