#!/usr/bin/env python3
"""
Script para aplicar migration do campo approved_by diretamente no banco.
Usado quando alembic não consegue executar devido a problemas de importação.
"""

import asyncio
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import AsyncSessionLocal


async def apply_migration():
    """Aplica a migration do campo approved_by."""
    async with AsyncSessionLocal() as session:
        try:
            # Verificar se a coluna já existe
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'approved_by'
            """)
            result = await session.execute(check_query)
            exists = result.scalar_one_or_none()
            
            if exists:
                print("✓ Coluna 'approved_by' já existe na tabela 'orders'")
            else:
                # Adicionar coluna
                await session.execute(text("""
                    ALTER TABLE orders 
                    ADD COLUMN approved_by INTEGER 
                    REFERENCES users(id) ON DELETE SET NULL
                """))
                print("✓ Coluna 'approved_by' adicionada com sucesso")
            
            # Verificar se o índice já existe
            index_query = text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'orders' AND indexname = 'ix_orders_approved_by'
            """)
            result = await session.execute(index_query)
            index_exists = result.scalar_one_or_none()
            
            if index_exists:
                print("✓ Índice 'ix_orders_approved_by' já existe")
            else:
                # Criar índice
                await session.execute(text("""
                    CREATE INDEX ix_orders_approved_by ON orders(approved_by)
                """))
                print("✓ Índice 'ix_orders_approved_by' criado com sucesso")
            
            await session.commit()
            print("\n✅ Migration aplicada com sucesso!")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Erro ao aplicar migration: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(apply_migration())
