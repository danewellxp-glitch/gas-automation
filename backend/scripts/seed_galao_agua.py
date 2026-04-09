"""
Seed: Galão de Água 20L (G20L)

Cadastra o produto Galão de Água 20L no banco, junto com:
- Entradas em ProdutoPreco para todos os TipoPreco existentes (preço R$0 — financeiro preenche)
- Entrada em StockProduct (estoque zerado)
- Entrada em Vasilhame para controle de comodato

Uso:
    cd backend
    python scripts/seed_galao_agua.py

Idempotente: seguro re-executar (não duplica registros).
"""

import asyncio
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, "/home/daniel/gas-automation/backend")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.product import Product
from app.models.tipo_preco import TipoPreco, ProdutoPreco
from app.models.estoque.stock_product import StockProduct
from app.models.vasilhame import Vasilhame

DATABASE_URL = settings.database_url


async def seed(db: AsyncSession) -> None:
    # ── 1. Produto ──────────────────────────────────────────────────────
    result = await db.execute(select(Product).where(Product.code == "G20L"))
    product = result.scalar_one_or_none()

    if product:
        print(f"[OK] Produto G20L já existe (id={product.id}) — nenhuma ação.")
    else:
        product = Product(
            code="G20L",
            name="Galão de Água 20L",
            description="Galão de água mineral/potável 20 litros",
            categoria="agua",
            weight_kg=None,
            volume_litros=20,
            requer_retorno_vasilhame=True,
            # PREENCHER com valores reais antes de ir para produção:
            price=Decimal("0.00"),
            is_active=True,
            firebird_code=None,
        )
        db.add(product)
        await db.flush()
        print(f"[CRIADO] Produto G20L (id={product.id})")

    # ── 2. ProdutoPreco para todos os TipoPreco existentes ──────────────
    tipos_result = await db.execute(select(TipoPreco).where(TipoPreco.ativo == True))
    tipos = tipos_result.scalars().all()

    hoje = date.today()
    for tipo in tipos:
        existing = await db.execute(
            select(ProdutoPreco).where(
                ProdutoPreco.produto_id == product.id,
                ProdutoPreco.tipo_preco_id == tipo.id,
                ProdutoPreco.vigencia_fim == None,
            )
        )
        if existing.scalar_one_or_none():
            print(f"[OK] ProdutoPreco G20L × {tipo.codigo} já existe — ignorado.")
            continue

        pp = ProdutoPreco(
            produto_id=product.id,
            tipo_preco_id=tipo.id,
            preco=Decimal("0.00"),  # PREENCHER: financeiro atualiza depois
            vigencia_inicio=hoje,
            vigencia_fim=None,
        )
        db.add(pp)
        print(f"[CRIADO] ProdutoPreco G20L × {tipo.codigo} (R$0,00 — preencher)")

    # ── 3. StockProduct ──────────────────────────────────────────────────
    sp_result = await db.execute(
        select(StockProduct).where(StockProduct.code == "G20L")
    )
    if sp_result.scalar_one_or_none():
        print("[OK] StockProduct G20L já existe — ignorado.")
    else:
        sp = StockProduct(
            code="G20L",
            name="Galão de Água 20L",
            unit="unidade",
            cost_price=Decimal("0.00"),  # PREENCHER: custo de compra
            min_stock_alert=10,
            linked_product_code="G20L",
            is_active=True,
        )
        db.add(sp)
        print("[CRIADO] StockProduct G20L")

    # ── 4. Vasilhame (comodato) ──────────────────────────────────────────
    vas_result = await db.execute(
        select(Vasilhame).where(Vasilhame.codigo == "G20L")
    )
    if vas_result.scalar_one_or_none():
        print("[OK] Vasilhame G20L já existe — ignorado.")
    else:
        vas = Vasilhame(
            codigo="G20L",
            descricao="Galão de Água 20 Litros",
            peso_kg=Decimal("1.00"),  # peso do galão vazio (aproximado)
            valor_caucao=Decimal("0.00"),  # PREENCHER: se cobrar depósito
            ativo=True,
            firebird_id=None,
        )
        db.add(vas)
        print("[CRIADO] Vasilhame G20L")

    await db.commit()
    print("\n[CONCLUÍDO] Seed do Galão de Água 20L finalizado.")
    print("\nLEMBRETES — preencher antes de ir para produção:")
    print("  • Product.price          (preço de venda varejo)")
    print("  • StockProduct.cost_price (custo de compra)")
    print("  • ProdutoPreco.preco      (para cada modalidade de preço)")
    print("  • Vasilhame.valor_caucao  (se cobrar depósito de vasilhame)")


async def main() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        await seed(db)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
