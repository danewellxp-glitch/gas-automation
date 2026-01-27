from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import pytz

# Brazilian timezone
BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')

def brazilian_now():
    """Get current time in Brazilian timezone"""
    return datetime.now(BRAZIL_TZ)

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    full_name: str
    hashed_password: str
    role: str = Field(default="user")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_number: str
    name: Optional[str] = None
    assigned_to: Optional[int] = Field(default=None, foreign_key="user.id")
    created_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    status: str = "pending"

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id")
    sender: str  # "customer", "agent", "bot", "system"
    message_type: str = "customer"  # "customer", "agent", "bot", "system"
    content: str
    bot_service: Optional[str] = None  # "claude", "ollama", "rasa", "fallback", "n8n"
    n8n_workflow_id: Optional[str] = None  # n8n workflow identifier
    n8n_execution_id: Optional[str] = None  # n8n execution identifier
    n8n_processed: bool = False  # whether message was processed by n8n
    timestamp: datetime = Field(default_factory=lambda: datetime.now())

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    action: str
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    details: Optional[str] = None

class BotInteraction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str
    customer_name: Optional[str] = None
    user_message: str
    bot_response: str
    bot_type: str = "enhanced"  # 'rasa', 'ollama', 'enhanced', 'fallback'
    escalated: bool = False
    escalation_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=brazilian_now)
    response_time_ms: Optional[int] = None

class BotContext(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str = Field(unique=True)
    conversation_stage: str = "greeting"
    user_intent: Optional[str] = None
    collected_info: Optional[str] = None  # JSON string
    bot_responses_count: int = 0
    escalation_requested: bool = False
    escalation_reason: Optional[str] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now())
    expires_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(hours=2))