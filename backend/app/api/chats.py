"""
API de Chats - Gerenciamento de conversas WhatsApp.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db, redis_manager
from app.models.customer import Customer
from app.models.event_log import EventLog
from app.integrations.waha import waha_client
from app.api.websocket import emit_new_message

router = APIRouter()


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


@router.get("", response_model=list[ChatOut])
async def list_chats(
    db: AsyncSession = Depends(get_db),
):
    """Lista todas as conversas ativas."""
    chats = []
    
    # Buscar todos os eventos de mensagem recebida
    result = await db.execute(
        select(EventLog)
        .where(EventLog.event_type == "message_received")
        .order_by(desc(EventLog.created_at))
    )
    events = result.scalars().all()
    
    # Extrair telefones únicos em ordem de última mensagem
    seen_phones = set()
    phones_ordered = []
    for event in events:
        phone = event.payload.get("phone")
        if phone and phone not in seen_phones:
            phones_ordered.append(phone)
            seen_phones.add(phone)
    
    for phone in phones_ordered:
        # Buscar cliente
        result = await db.execute(
            select(Customer).where(Customer.phone == phone)
        )
        customer = result.scalar_one_or_none()

        # Buscar ultima mensagem do log
        result = await db.execute(
            select(EventLog)
            .where(EventLog.event_type == "message_received")
            .where(EventLog.payload["phone"].astext == phone)
            .order_by(desc(EventLog.created_at))
            .limit(1)
        )
        last_event = result.scalar_one_or_none()
        
        # Buscar estado do Redis
        state = "start"
        redis = redis_manager.client
        if redis:
            try:
                context_data = await redis.hgetall(f"conversation:{phone}")
                state = context_data.get("state", "start") if context_data else "start"
            except Exception as e:
                print(f"Erro ao buscar estado do Redis para {phone}: {e}")

        chat = ChatOut(
            phone=phone,
            customer_name=customer.name if customer else None,
            customer_id=str(customer.id) if customer else None,
            last_message=last_event.payload.get("message") if last_event else None,
            last_message_time=last_event.created_at if last_event else None,
            unread_count=0,
            state=state
        )
        chats.append(chat)

    return chats


@router.get("/{phone}/messages", response_model=list[MessageOut])
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
    try:
        # Formatar telefone para WAHA
        chat_id = phone if "@" in phone else f"{phone}@c.us"

        # Enviar via WAHA
        success = await waha_client.send_message(chat_id, request.message)

        if success:
            # Log da mensagem enviada
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

            # Emitir via WebSocket
            await emit_new_message({
                "phone": phone,
                "message": request.message,
                "from_me": True
            })

            return {"success": True, "message": "Mensagem enviada"}
        else:
            raise HTTPException(status_code=500, detail="Falha ao enviar mensagem")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{phone}/context")
async def get_chat_context(phone: str):
    """Busca contexto atual da conversa."""
    redis = redis_manager.client
    if not redis:
        return {"phone": phone, "context": None}

    context = await redis.hgetall(f"conversation:{phone}")
    return {"phone": phone, "context": context or None}


@router.delete("/{phone}/context")
async def reset_chat_context(phone: str):
    """Reseta contexto da conversa."""
    redis = redis_manager.client
    if redis:
        await redis.delete(f"conversation:{phone}")

    return {"message": f"Contexto resetado para {phone}"}
