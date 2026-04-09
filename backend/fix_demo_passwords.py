"""Atualiza/cria usuários de demo financeiro e estoque com senha Teste@12345."""
import asyncio
import os
from datetime import datetime, timezone

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
hashed = pwd_context.hash("Teste@12345")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://gasadmin:gasadmin123@db:5432/gas_automation"
)

USERS = [
    {
        "username": "financeiro",
        "email": "financeiro@gasautomation.local",
        "full_name": "Usuário Financeiro",
        "role": "financeiro",
    },
    {
        "username": "estoque",
        "email": "estoque@gasautomation.local",
        "full_name": "Usuário Estoque",
        "role": "estoque",
    },
]


async def main():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            for u in USERS:
                result = await session.execute(
                    text("SELECT id FROM users WHERE username = :username"),
                    {"username": u["username"]},
                )
                row = result.fetchone()
                if row:
                    await session.execute(
                        text("UPDATE users SET hashed_password = :hp, updated_at = :now WHERE username = :username"),
                        {"hp": hashed, "now": datetime.now(timezone.utc), "username": u["username"]},
                    )
                    print(f"Senha atualizada: {u['username']}")
                else:
                    await session.execute(
                        text("""
                            INSERT INTO users (username, email, full_name, hashed_password, role, is_active,
                                              must_change_password, created_at, updated_at)
                            VALUES (:username, :email, :full_name, :hp, :role, true, false, :now, :now)
                        """),
                        {
                            "username": u["username"],
                            "email": u["email"],
                            "full_name": u["full_name"],
                            "hp": hashed,
                            "role": u["role"],
                            "now": datetime.now(timezone.utc),
                        },
                    )
                    print(f"Usuário criado: {u['username']}")

    await engine.dispose()
    print("Concluído. Senha: Teste@12345")


if __name__ == "__main__":
    asyncio.run(main())
