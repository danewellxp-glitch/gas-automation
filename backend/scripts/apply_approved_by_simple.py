#!/usr/bin/env python3
"""
Script simples para aplicar migration do campo approved_by.
Não importa modelos para evitar problemas de importação.
"""

import asyncio
import asyncpg
import os
from pathlib import Path

# Carregar variáveis de ambiente do .env se existir
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Pegar URL do banco (padrão do docker-compose)
database_url = os.getenv("DATABASE_URL", "postgresql://gasadmin:gasadmin123@localhost:5433/gas_automation")

# Converter para formato asyncpg (remover +asyncpg)
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
elif database_url.startswith("postgresql://"):
    pass  # Já está no formato correto
else:
    print(f"URL do banco inválida: {database_url}")
    exit(1)


async def apply_migration():
    """Aplica a migration do campo approved_by."""
    conn = await asyncpg.connect(database_url)
    
    try:
        # Verificar se a coluna já existe
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'approved_by'
            )
        """)
        
        if exists:
            print("✓ Coluna 'approved_by' já existe na tabela 'orders'")
        else:
            # Adicionar coluna
            await conn.execute("""
                ALTER TABLE orders 
                ADD COLUMN approved_by INTEGER 
                REFERENCES users(id) ON DELETE SET NULL
            """)
            print("✓ Coluna 'approved_by' adicionada com sucesso")
        
        # Verificar se o índice já existe
        index_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'orders' AND indexname = 'ix_orders_approved_by'
            )
        """)
        
        if index_exists:
            print("✓ Índice 'ix_orders_approved_by' já existe")
        else:
            # Criar índice
            await conn.execute("""
                CREATE INDEX ix_orders_approved_by ON orders(approved_by)
            """)
            print("✓ Índice 'ix_orders_approved_by' criado com sucesso")
        
        print("\n✅ Migration aplicada com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro ao aplicar migration: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(apply_migration())
