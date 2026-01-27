#!/usr/bin/env python3
"""
Script para sincronizar produtos do Firebird (Gerente.fdb) para PostgreSQL.

Uso:
    python SCRIPT_SINCRONIZAR_PRODUTOS_FIREBIRD.py

Este script:
1. Busca produtos do Firebird
2. Sincroniza com PostgreSQL
3. Atualiza preços e informações
"""

import asyncio
import sys
from pathlib import Path

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.integrations.firebird import firebird_client
from app.database import AsyncSessionLocal
from app.models.product import Product
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def sync_products():
    """Sincroniza produtos do Firebird para PostgreSQL."""
    print("=" * 60)
    print("🔄 Sincronização de Produtos - Firebird → PostgreSQL")
    print("=" * 60)
    print()

    # Verificar conexão Firebird
    if not firebird_client.is_available:
        print("❌ Firebird não está disponível!")
        print("   Verifique a configuração no .env")
        return

    if not firebird_client.test_connection():
        print("❌ Não foi possível conectar ao Firebird!")
        return

    print("✅ Conectado ao Firebird")
    print()

    # Buscar produtos do Firebird
    print("📦 Buscando produtos do Firebird...")
    firebird_products = firebird_client.get_products()
    print(f"   ✅ {len(firebird_products)} produtos encontrados")
    print()

    if not firebird_products:
        print("⚠️ Nenhum produto encontrado no Firebird!")
        return

    # Sincronizar com PostgreSQL
    print("💾 Sincronizando com PostgreSQL...")
    async with AsyncSessionLocal() as db:
        created = 0
        updated = 0
        skipped = 0

        for fb_product in firebird_products:
            code = fb_product.get("code", "").strip()
            if not code:
                skipped += 1
                continue

            # Buscar produto existente
            result = await db.execute(
                select(Product).where(Product.code == code.upper())
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Atualizar produto existente
                existing.name = fb_product.get("name", existing.name)
                existing.price = fb_product.get("price", existing.price)
                existing.weight_kg = fb_product.get("weight_kg") or existing.weight_kg
                existing.description = fb_product.get("name_short") or existing.description
                existing.firebird_code = str(fb_product.get("firebird_id", "")) or existing.firebird_code
                existing.is_active = fb_product.get("is_active", True)
                updated += 1
                print(f"   🔄 Atualizado: {code} - {existing.name}")
            else:
                # Criar novo produto
                new_product = Product(
                    code=code.upper(),
                    name=fb_product.get("name", code),
                    price=fb_product.get("price", 0),
                    weight_kg=fb_product.get("weight_kg") or 0,
                    description=fb_product.get("name_short"),
                    firebird_code=str(fb_product.get("firebird_id", "")),
                    is_active=fb_product.get("is_active", True),
                )
                db.add(new_product)
                created += 1
                print(f"   ➕ Criado: {code} - {new_product.name}")

        await db.commit()

    print()
    print("=" * 60)
    print("✅ Sincronização concluída!")
    print(f"   ➕ Criados: {created}")
    print(f"   🔄 Atualizados: {updated}")
    print(f"   ⏭️ Ignorados: {skipped}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(sync_products())
