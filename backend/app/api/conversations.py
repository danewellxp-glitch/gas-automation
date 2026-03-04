from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.database import get_db
from app.models.auth_models import User, Conversation, Message
from app.api.auth import get_current_user
from app.schemas.chat_schemas import ConversationOut, ConversationDetail, ConversationStatusUpdate, MessageOut, MessageCreate
from app.services.whatsapp_service import waha_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

@router.get("", response_model=List[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List active conversations"""
    conversations = db.query(Conversation).order_by(desc(Conversation.last_message_at)).all()
    return conversations

@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a conversation with its messages"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Mark messages as read here if needed (could integrate with waha_service)
    conversation.unread_count = 0
    db.commit()

    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp).all()
    
    # Manually attach messages to serialize
    conversation_detail = ConversationDetail.model_validate(conversation)
    conversation_detail.messages = [MessageOut.model_validate(m) for m in messages]
    
    return conversation_detail

@router.patch("/{conversation_id}/status", response_model=ConversationOut)
def finalize_service(
    conversation_id: int,
    status_update: ConversationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update conversation status (e.g. End Chat/RESOLVED)"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation.status = status_update.status
    db.commit()
    db.refresh(conversation)
    return conversation

@router.patch("/{conversation_id}/assign", response_model=ConversationOut)
def assign_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign conversation to current user"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation.assigned_to = current_user.id
    conversation.status = "ASSIGNED"
    db.commit()
    db.refresh(conversation)
    return conversation

@router.post("/{conversation_id}/messages", response_model=MessageOut)
async def send_message(
    conversation_id: int,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to a conversation via WAHA"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Send via WAHA
    whatsapp_response = await waha_service.send_text_message(
        to=conversation.customer_phone,
        text=message_in.content
    )
    
    waha_msg_id = whatsapp_response.get("id", {}).get("_serialized") or None

    new_message = Message(
        conversation_id=conversation.id,
        direction="OUTBOUND",
        sender="agent",
        type="TEXT",
        content=message_in.content,
        status="SENT" if waha_msg_id else "FAILED",
        whatsapp_message_id=waha_msg_id
    )
    
    db.add(new_message)
    
    conversation.last_message_at = new_message.timestamp
    
    db.commit()
    db.refresh(new_message)
    
    # Here we would normally trigger a WebSocket emit:
    # await manager.broadcast(f"message-sent:{conversation.id}", new_message.model_dump())
    
    return new_message
