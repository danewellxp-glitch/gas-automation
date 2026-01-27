import asyncio
from app.database import engine
from sqlmodel import SQLModel

async def create_tables():
    # Importar todos os modelos para garantir que sejam registrados
    from app.models import (
        User, Conversation, Message, AuditLog, BotInteraction, BotContext,
        Customer, Product, Order, OrderItem, Payment,
        Delivery, Driver, EventLog
    )
    from app.models.base import Base

    # Criar todas as tabelas SQLAlchemy
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Todas as tabelas criadas com sucesso!")
    print("Tabelas: users, customers, products, orders, order_items, payments, deliveries, drivers, event_logs")

if __name__ == "__main__":
    asyncio.run(create_tables())
