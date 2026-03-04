import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.models.base import Base
import app.models.auth_models  # Import to register models

from sqlmodel import SQLModel

engine = create_async_engine(settings.database_url)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        print("Tables created successfully.")

asyncio.run(create_tables())
