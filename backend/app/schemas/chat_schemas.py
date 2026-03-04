from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ContactBase(BaseModel):
    phone_number: str
    name: Optional[str] = None
    is_valid_whatsapp: bool = True

class ContactOut(ContactBase):
    id: int
    last_synced_at: datetime
    
    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    content: str
    type: str = "TEXT"

class MessageCreate(MessageBase):
    conversation_id: int
    direction: str = "OUTBOUND"
    sender: str = "system"

class MessageOut(MessageBase):
    id: int
    conversation_id: int
    direction: str
    sender: str
    status: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    customer_phone: str
    name: Optional[str] = None
    status: str = "OPEN"

class ConversationOut(ConversationBase):
    id: int
    assigned_to: Optional[int]
    unread_count: int
    last_message_at: datetime
    
    class Config:
        from_attributes = True

class ConversationDetail(ConversationOut):
    messages: List[MessageOut] = []

class ConversationStatusUpdate(BaseModel):
    status: str # e.g. "RESOLVED"
