"""
API de Produtos.
CRUD de produtos (botijões de gás).
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.product import Product
from app.schemas.product import (
    ProductBrief,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter()


@router.get("", response_model=list[ProductResponse])
async def list_products(
    active_only: bool = Query(True, description="Apenas produtos ativos"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista todos os produtos.

    Por padrão retorna apenas produtos ativos.
    """
    query = select(Product)

    if active_only:
        query = query.where(Product.is_active == True)

    query = query.order_by(Product.code)

    result = await db.execute(query)
    products = result.scalars().all()

    return products


@router.get("/active", response_model=list[ProductBrief])
async def list_active_products(
    db: AsyncSession = Depends(get_db),
):
    """
    Lista produtos ativos (versão resumida para o bot).
    """
    query = (
        select(Product)
        .where(Product.is_active == True)
        .order_by(Product.code)
    )

    result = await db.execute(query)
    products = result.scalars().all()

    return [
        ProductBrief(
            id=p.id,
            code=p.code,
            name=p.name,
            price=p.price,
            weight_kg=p.weight_kg,
        )
        for p in products
    ]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Busca produto por ID."""
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    return product


@router.get("/code/{code}", response_model=ProductResponse)
async def get_product_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Busca produto por código (P13, P20, P45)."""
    result = await db.execute(
        select(Product).where(Product.code == code.upper())
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    return product


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Cria um novo produto.

    Normalmente não usado em produção (produtos vêm do Firebird).
    """
    # Verificar se código já existe
    existing = await db.execute(
        select(Product).where(Product.code == data.code.upper())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Produto com código {data.code} já existe"
        )

    product = Product(
        code=data.code.upper(),
        name=data.name,
        description=data.description,
        weight_kg=data.weight_kg,
        price=data.price,
        is_active=data.is_active,
        firebird_code=data.firebird_code,
    )

    db.add(product)
    await db.commit()
    await db.refresh(product)

    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza um produto."""
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Atualizar apenas campos fornecidos
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove um produto (soft delete - apenas desativa).

    Não remove fisicamente para manter histórico de pedidos.
    """
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    product.is_active = False
    await db.commit()

    return {"message": "Produto desativado", "id": str(product_id)}


@router.post("/{product_id}/activate")
async def activate_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Reativa um produto desativado."""
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    product.is_active = True
    await db.commit()

    return {"message": "Produto ativado", "id": str(product_id)}
