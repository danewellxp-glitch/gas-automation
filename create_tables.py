import asyncio
from app.database import engine
from app.models import *
from sqlmodel import SQLModel

async def create_tables():
    # Criar tabelas SQLModel (User, Conversation, Message, AuditLog)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Tabelas criadas com sucesso!")

if __name__ == "__main__":
    asyncio.run(create_tables())
