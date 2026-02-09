"""
Model para persistência de contexto de conversa no PostgreSQL.
Backup do Redis para recuperar pedidos abandonados.
"""

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import BaseModel


class ConversationSnapshot(BaseModel):
    """
    Snapshot do contexto de conversa salvo no PostgreSQL.

    Permite recuperar o estado da conversa quando o Redis TTL expira (30min).
    Atualizado a cada interação via upsert (INSERT ON CONFLICT DO UPDATE).
    """

    __tablename__ = "conversation_snapshots"

    phone = Column(String(20), unique=True, nullable=False, index=True)
    state = Column(String(50), nullable=False, default="start")
    context_json = Column(JSONB, nullable=False, default={})

    def __repr__(self):
        return f"<ConversationSnapshot phone={self.phone} state={self.state}>"
