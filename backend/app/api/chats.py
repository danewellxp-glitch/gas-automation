"""
API de Chats - Gerenciamento de conversas WhatsApp.
"""

import logging
from typing import Optional, List, Dict, Tuple, Generic, TypeVar
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db, redis_manager
from app.models.customer import Customer
from app.models.event_log import EventLog
from app.integrations.waha import waha_client
from app.api.websocket import emit_new_message

logger = logging.getLogger(__name__)


# ===== SCHEMAS =====

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Resposta paginada padronizada."""
    items: List[T]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_pages: int


class SuccessResponse(BaseModel):
    """Resposta de sucesso padronizada."""
    success: bool = True
    message: str


class ChatContextResponse(BaseModel):
    """Resposta de contexto de chat."""
    phone: str
    context: Optional[Dict] = None


class WAHAStatusResponse(BaseModel):
    """Resposta de status WAHA."""
    success: bool
    waha_url: str
    session_name: str
    status: Optional[Dict] = None
    error: Optional[str] = None


class BotInteractionOut(BaseModel):
    """Schema de interação do bot."""
    customer_name: str
    user_message: str
    bot_type: str
    timestamp: str


class MessageOut(BaseModel):
    id: str
    phone: str
    text: str
    from_me: bool
    timestamp: datetime

    class Config:
        from_attributes = True


class ChatOut(BaseModel):
    phone: str
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0
    state: Optional[str] = None


class SendMessageRequest(BaseModel):
    phone: str
    message: str


class ReplyMessageRequest(BaseModel):
    message: str


class ConversationOut(BaseModel):
    id: str
    customer_number: str
    name: Optional[str] = None
    status: str = "waiting"
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    assigned_to: Optional[int] = None
    assigned_to_me: bool = False
    assigned_to_name: Optional[str] = None
    unread_count: int = 0
    created_at: Optional[datetime] = None


class ConversationMessageOut(BaseModel):
    id: Optional[str] = None
    sender: str  # customer, agent, bot, system
    content: str
    message_type: str
    bot_service: Optional[str] = None
    timestamp: Optional[str] = None
    created_at: Optional[str] = None
    isFromCurrentUser: bool = False


# ===== ROUTER =====

router = APIRouter()


# ===== ENDPOINT DE DIAGNÓSTICO (deve vir antes das rotas com parâmetros) =====

@router.get("/waha-status", response_model=WAHAStatusResponse)
async def get_waha_status():
    """Verifica status da conexão WAHA."""
    try:
        status = await waha_client.get_session_status()
        return WAHAStatusResponse(
            success=True,
            waha_url=waha_client.base_url,
            session_name=waha_client.session_name,
            status=status,
        )
    except Exception as e:
        logger.error(f"Erro ao verificar status WAHA: {e}")
        return WAHAStatusResponse(
            success=False,
            waha_url=waha_client.base_url,
            session_name=waha_client.session_name,
            error=str(e),
        )


# ===== FUNÇÃO AUXILIAR PARA EVITAR DUPLICAÇÃO =====

async def _fetch_chat_base_data(db: AsyncSession) -> Tuple[List[str], Dict[str, EventLog], Dict[str, Customer], Dict[str, str]]:
    """
    Busca dados base para listagem de chats/conversas.

    Returns:
        Tuple contendo:
        - phones_ordered: Lista de telefones ordenados por última mensagem
        - phone_last_event: Dict mapeando telefone -> último evento
        - customers_by_phone: Dict mapeando telefone -> cliente
        - phone_states: Dict mapeando telefone -> estado do Redis
    """
    # Buscar todos os eventos de mensagem recebida
    result = await db.execute(
        select(EventLog)
        .where(EventLog.event_type == "message_received")
        .order_by(desc(EventLog.created_at))
    )
    events = result.scalars().all()

    # Extrair telefones únicos em ordem de última mensagem e guardar último evento
    seen_phones = set()
    phones_ordered = []
    phone_last_event = {}
    for event in events:
        phone = event.payload.get("phone")
        if phone and phone not in seen_phones:
            phones_ordered.append(phone)
            seen_phones.add(phone)
            phone_last_event[phone] = event

    if not phones_ordered:
        return [], {}, {}, {}

    # Buscar todos os clientes em uma única query
    customers_result = await db.execute(
        select(Customer).where(Customer.phone.in_(phones_ordered))
    )
    customers_by_phone = {c.phone: c for c in customers_result.scalars().all()}

    # Buscar estados do Redis (com fallback seguro)
    redis = redis_manager.client
    phone_states = {}
    if redis:
        for phone in phones_ordered:
            try:
                context_data = await redis.hgetall(f"conversation:{phone}")
                phone_states[phone] = context_data.get("state", "start") if context_data else "start"
            except Exception as e:
                logger.debug(f"Erro ao buscar estado Redis para {phone}: {e}")
                phone_states[phone] = "start"

    return phones_ordered, phone_last_event, customers_by_phone, phone_states


@router.get("", response_model=List[ChatOut])
async def list_chats(
    db: AsyncSession = Depends(get_db),
):
    """Lista todas as conversas ativas."""
    phones_ordered, phone_last_event, customers_by_phone, phone_states = await _fetch_chat_base_data(db)

    if not phones_ordered:
        return []

    # Montar resposta
    chats = []
    for phone in phones_ordered:
        customer = customers_by_phone.get(phone)
        last_event = phone_last_event.get(phone)

        chats.append(ChatOut(
            phone=phone,
            customer_name=customer.name if customer else None,
            customer_id=str(customer.id) if customer else None,
            last_message=last_event.payload.get("message") if last_event else None,
            last_message_time=last_event.created_at if last_event else None,
            unread_count=0,
            state=phone_states.get(phone, "start"),
        ))

    return chats


@router.get("/{phone}/messages", response_model=List[MessageOut])
async def get_chat_messages(
    phone: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Busca historico de mensagens de uma conversa."""
    messages = []

    # Buscar mensagens recebidas
    result = await db.execute(
        select(EventLog)
        .where(EventLog.event_type.in_(["message_received", "message_sent"]))
        .where(EventLog.payload["phone"].astext == phone)
        .order_by(desc(EventLog.created_at))
        .limit(limit)
    )
    events = result.scalars().all()

    for event in reversed(events):
        messages.append(MessageOut(
            id=str(event.id),
            phone=phone,
            text=event.payload.get("message", ""),
            from_me=event.event_type == "message_sent",
            timestamp=event.created_at
        ))

    return messages


@router.post("/{phone}/send")
async def send_message(
    phone: str,
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Envia mensagem manual para um cliente."""
    # Formatar telefone para WAHA
    chat_id = phone if "@" in phone else f"{phone}@c.us"

    # 1. Enviar via WAHA (prioridade máxima)
    try:
        logger.info(f"Enviando mensagem manual para {chat_id}")
        result = await waha_client.send_text(chat_id, request.message)

        if not result:
            logger.error(f"WAHA retornou resultado vazio para {chat_id}")
            raise HTTPException(status_code=500, detail="Falha ao enviar mensagem - WAHA não respondeu")

        logger.info(f"Mensagem manual enviada com sucesso para {chat_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro WAHA ao enviar mensagem para {phone}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar mensagem: {str(e)}")

    # 2. Log no banco (não deve falhar o fluxo se der erro)
    try:
        event = EventLog(
            event_type="message_sent",
            entity_type="chat",
            payload={
                "phone": phone,
                "message": request.message,
                "manual": True
            }
        )
        db.add(event)
        await db.commit()
    except Exception as e:
        logger.error(f"Erro ao salvar log de mensagem para {phone}: {e}")
        # Não lançar exceção - mensagem já foi enviada com sucesso

    # 3. Emitir via WebSocket (não deve falhar o fluxo se der erro)
    try:
        await emit_new_message({
            "phone": phone,
            "message": request.message,
            "from_me": True
        })
    except Exception as e:
        logger.error(f"Erro ao emitir WebSocket para {phone}: {e}")
        # Não lançar exceção - mensagem já foi enviada com sucesso

    return {"success": True, "message": "Mensagem enviada", "result": result}


@router.get("/{phone}/context", response_model=ChatContextResponse)
async def get_chat_context(phone: str):
    """Busca contexto atual da conversa."""
    redis = redis_manager.client
    if not redis:
        return ChatContextResponse(phone=phone, context=None)

    context = await redis.hgetall(f"conversation:{phone}")
    return ChatContextResponse(phone=phone, context=context or None)


@router.delete("/{phone}/context", response_model=SuccessResponse)
async def reset_chat_context(phone: str):
    """Reseta contexto da conversa."""
    redis = redis_manager.client
    if redis:
        await redis.delete(f"conversation:{phone}")

    return SuccessResponse(message=f"Contexto resetado para {phone}")


# ===== ENDPOINTS PARA COMPATIBILIDADE COM PAINEL OPERADOR =====

@router.get("/my-conversations", response_model=PaginatedResponse[ConversationOut], deprecated=True)
async def list_my_conversations(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    db: AsyncSession = Depends(get_db),
):
    """
    [DEPRECATED] Use GET /conversations em vez disso.
    Lista conversas atribuídas ao operador atual.
    """
    logger.warning("Endpoint /my-conversations está deprecated. Use /conversations")
    return await list_conversations_operator(page=page, page_size=page_size, db=db)


@router.get("/conversations", response_model=PaginatedResponse[ConversationOut])
async def list_conversations_operator(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    db: AsyncSession = Depends(get_db),
):
    """Lista todas as conversas disponíveis com paginação."""
    phones_ordered, phone_last_event, customers_by_phone, phone_states = await _fetch_chat_base_data(db)

    total = len(phones_ordered)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    if not phones_ordered:
        return PaginatedResponse[ConversationOut](
            items=[], total=0, page=page, page_size=page_size, total_pages=1
        )

    # Aplicar paginação
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    phones_page = phones_ordered[start_idx:end_idx]

    # Montar resposta
    conversations = []
    for phone in phones_page:
        customer = customers_by_phone.get(phone)
        last_event = phone_last_event.get(phone)
        state = phone_states.get(phone, "start")

        # Determinar status baseado no estado
        status = "waiting"
        if state == "talking_to_human":
            status = "active"
        elif state in ["order_confirmed", "tracking_order"]:
            status = "bot"

        conversations.append(ConversationOut(
            id=phone,
            customer_number=phone,
            name=customer.name if customer else None,
            status=status,
            last_message=last_event.payload.get("message") if last_event else None,
            last_message_at=last_event.created_at if last_event else None,
            assigned_to=None,
            assigned_to_me=False,
            assigned_to_name=None,
            unread_count=0,
            created_at=last_event.created_at if last_event else None,
        ))

    return PaginatedResponse[ConversationOut](
        items=conversations,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/conversations/{conversation_id}/assign", response_model=SuccessResponse)
async def assign_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Atribui conversa ao operador atual."""
    # Por enquanto apenas retorna sucesso (sem sistema de atribuição implementado)
    return SuccessResponse(message=f"Conversa {conversation_id} atribuída")


@router.get("/conversations/{conversation_id}/messages", response_model=List[ConversationMessageOut])
async def get_conversation_messages_operator(
    conversation_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Busca histórico de mensagens de uma conversa (formato painel operador)."""
    messages = []

    # Buscar mensagens recebidas e enviadas
    result = await db.execute(
        select(EventLog)
        .where(EventLog.event_type.in_(["message_received", "message_sent"]))
        .where(EventLog.payload["phone"].astext == conversation_id)
        .order_by(desc(EventLog.created_at))
        .limit(limit)
    )
    events = result.scalars().all()

    for event in reversed(events):
        # Determinar sender baseado no tipo de evento
        if event.event_type == "message_received":
            sender = "customer"
        elif event.payload.get("manual"):
            sender = "agent"
        else:
            sender = "bot"

        message = ConversationMessageOut(
            id=str(event.id),
            sender=sender,
            content=event.payload.get("message", ""),
            message_type="text",
            timestamp=event.created_at.isoformat(),
            created_at=event.created_at.isoformat(),
            isFromCurrentUser=(event.event_type == "message_sent")
        )
        messages.append(message)

    return messages


@router.post("/conversations/{conversation_id}/reply")
async def reply_to_conversation(
    conversation_id: str,
    request: ReplyMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Responde a uma conversa."""
    # Formatar telefone para WAHA
    chat_id = conversation_id if "@" in conversation_id else f"{conversation_id}@c.us"

    # 1. Enviar via WAHA (prioridade máxima)
    try:
        logger.info(f"Enviando mensagem para {chat_id}: {request.message[:50]}...")
        result = await waha_client.send_text(chat_id, request.message)

        if not result:
            logger.error(f"WAHA retornou resultado vazio para {chat_id}")
            raise HTTPException(status_code=500, detail="Falha ao enviar mensagem - WAHA não respondeu")

        logger.info(f"Mensagem enviada com sucesso para {chat_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro WAHA ao enviar mensagem para {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar mensagem: {str(e)}")

    # 2. Log no banco (não deve falhar o fluxo se der erro)
    try:
        event = EventLog(
            event_type="message_sent",
            entity_type="chat",
            payload={
                "phone": conversation_id,
                "message": request.message,
                "manual": True
            }
        )
        db.add(event)
        await db.commit()
    except Exception as e:
        logger.error(f"Erro ao salvar log de mensagem para {conversation_id}: {e}")
        # Não lançar exceção - mensagem já foi enviada com sucesso

    # 3. Emitir via WebSocket (não deve falhar o fluxo se der erro)
    try:
        await emit_new_message({
            "phone": conversation_id,
            "message": request.message,
            "from_me": True
        })
    except Exception as e:
        logger.error(f"Erro ao emitir WebSocket para {conversation_id}: {e}")
        # Não lançar exceção - mensagem já foi enviada com sucesso

    return {"success": True, "message": "Mensagem enviada", "result": result}


@router.post("/conversations/{conversation_id}/end", response_model=SuccessResponse)
async def end_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """
    Encerra uma conversa e devolve ao bot.
    - Reseta o estado para 'start' no Redis
    - Envia mensagem informando o cliente
    - Registra no EventLog
    """
    try:
        phone = conversation_id
        redis = redis_manager.client

        logger.info(f"Encerrando conversa {phone}")

        # 1. Resetar estado no Redis para 'start'
        if redis:
            await redis.hset(f"conversation:{phone}", "state", "start")
            # Limpar dados temporários do atendimento humano
            await redis.hdel(f"conversation:{phone}", "assigned_operator")
            logger.info(f"Estado resetado para 'start' no Redis para {phone}")

        # 2. Enviar mensagem ao cliente informando que voltou ao bot
        chat_id = phone if "@" in phone else f"{phone}@c.us"
        message_to_client = (
            "✅ *Atendimento encerrado*\n\n"
            "Obrigado por entrar em contato! "
            "Se precisar de algo mais, é só me chamar.\n\n"
            "Digite *menu* para ver as opções disponíveis."
        )

        waha_success = False
        try:
            result = await waha_client.send_text(chat_id, message_to_client)
            waha_success = bool(result)
            logger.info(f"Mensagem de encerramento enviada para {chat_id}")
        except Exception as e:
            logger.warning(f"Não foi possível enviar mensagem de encerramento para {chat_id}: {e}")

        # 3. Registrar no EventLog
        event = EventLog(
            event_type="conversation_ended",
            entity_type="chat",
            payload={
                "phone": phone,
                "action": "end_conversation",
                "message": "Atendimento encerrado pelo operador",
                "waha_sent": waha_success
            }
        )
        db.add(event)
        await db.commit()

        # 4. Emitir via WebSocket
        await emit_new_message({
            "phone": phone,
            "message": "[Sistema] Conversa encerrada e devolvida ao bot",
            "from_me": True,
            "system": True
        })

        return SuccessResponse(message=f"Conversa {conversation_id} encerrada e devolvida ao bot")

    except Exception as e:
        logger.error(f"Erro ao encerrar conversa {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao encerrar conversa: {str(e)}")


@router.post("/conversations/{conversation_id}/transfer-to-bot", response_model=SuccessResponse)
async def transfer_to_bot(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """
    Transfere a conversa de volta para o bot mantendo o contexto.
    Diferente de 'end' que reseta tudo, este mantém o estado atual do pedido.
    """
    try:
        phone = conversation_id
        redis = redis_manager.client

        logger.info(f"Transferindo conversa {phone} para o bot")

        # 1. Verificar estado atual
        current_state = "start"
        if redis:
            context_data = await redis.hgetall(f"conversation:{phone}")
            current_state = context_data.get("state", "start") if context_data else "start"
            logger.info(f"Estado atual de {phone}: {current_state}")

        # 2. Se está em talking_to_human, voltar para o estado anterior ou awaiting_product
        new_state = current_state
        if current_state == "talking_to_human":
            # Tentar recuperar estado anterior ou usar awaiting_product como padrão
            new_state = "awaiting_product"
            if redis:
                await redis.hset(f"conversation:{phone}", "state", new_state)
                await redis.hdel(f"conversation:{phone}", "assigned_operator")
                logger.info(f"Estado alterado de {current_state} para {new_state}")

        # 3. Enviar mensagem ao cliente
        chat_id = phone if "@" in phone else f"{phone}@c.us"
        message_to_client = (
            "🤖 *Você foi transferido de volta para o atendimento automático*\n\n"
            "Como posso ajudar?\n\n"
            "1️⃣ Fazer um pedido\n"
            "2️⃣ Consultar pedido\n"
            "3️⃣ Falar com atendente"
        )

        waha_success = False
        try:
            result = await waha_client.send_text(chat_id, message_to_client)
            waha_success = bool(result)
            logger.info(f"Mensagem de transferência enviada para {chat_id}")
        except Exception as e:
            logger.warning(f"Não foi possível enviar mensagem de transferência para {chat_id}: {e}")

        # 4. Registrar no EventLog
        event = EventLog(
            event_type="transfer_to_bot",
            entity_type="chat",
            payload={
                "phone": phone,
                "action": "transfer_to_bot",
                "previous_state": current_state,
                "new_state": new_state,
                "waha_sent": waha_success
            }
        )
        db.add(event)
        await db.commit()

        return SuccessResponse(message=f"Conversa {conversation_id} transferida para o bot")

    except Exception as e:
        logger.error(f"Erro ao transferir conversa {conversation_id} para bot: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao transferir para bot: {str(e)}")


@router.get("/bot-interactions", response_model=List[BotInteractionOut])
async def list_bot_interactions(db: AsyncSession = Depends(get_db)):
    """Lista interações do bot."""
    interactions = []

    # Buscar eventos do bot
    result = await db.execute(
        select(EventLog)
        .where(EventLog.event_type == "bot_interaction")
        .order_by(desc(EventLog.created_at))
        .limit(50)
    )
    events = result.scalars().all()

    for event in events:
        interactions.append(BotInteractionOut(
            customer_name=event.payload.get("customer_name", "Cliente"),
            user_message=event.payload.get("user_message", ""),
            bot_type=event.payload.get("bot_type", "chatbot"),
            timestamp=event.created_at.isoformat(),
        ))

    return interactions
