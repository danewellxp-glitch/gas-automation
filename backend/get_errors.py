import asyncio
from sqlalchemy import select, desc
from app.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        # Tentar ler a tabela de error_events ou ver o que houve
        from app.models.error_models import ErrorEvent
        result = await session.execute(
            select(ErrorEvent).order_by(desc(ErrorEvent.updated_at)).limit(5)
        )
        errors = result.scalars().all()
        for e in errors:
            print(f"[{e.updated_at}] {e.error_type}: {e.message}")

if __name__ == "__main__":
    asyncio.run(main())
