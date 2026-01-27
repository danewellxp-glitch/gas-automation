"""
API de Tipos de Preço e Preços por Produto.
Gerencia modalidades de preço (varejo, atacado, funcionário, revenda).
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tipo_preco import TipoPreco, ProdutoPreco
from app.models.product import Product
from app.schemas.tipo_preco import (
    TipoPrecoCreate,
    TipoPrecoResponse,
    TipoPrecoUpdate,
    ProdutoPrecoCreate,
    ProdutoPrecoResponse,
    ProdutoPrecoUpdate,
)

router = APIRouter()


# ==================== TIPOS DE PREÇO ====================

@router.get("", response_model=list[TipoPrecoResponse])
async def list_tipos_preco(
    ativos_only: bool = Query(True, description="Apenas tipos ativos"),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os tipos de preço."""
    query = select(TipoPreco)

    if ativos_only:
        query = query.where(TipoPreco.ativo == True)

    query = query.order_by(TipoPreco.codigo)

    result = await db.execute(query)
    tipos = result.scalars().all()

    return tipos


@router.get("/{tipo_id}", response_model=TipoPrecoResponse)
async def get_tipo_preco(
    tipo_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Busca tipo de preço por ID."""
    result = await db.execute(
        select(TipoPreco).where(TipoPreco.id == tipo_id)
    )
    tipo = result.scalar_one_or_none()

    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de preço não encontrado")

    return tipo


@router.get("/codigo/{codigo}", response_model=TipoPrecoResponse)
async def get_tipo_preco_by_codigo(
    codigo: str,
    db: AsyncSession = Depends(get_db),
):
    """Busca tipo de preço por código."""
    result = await db.execute(
        select(TipoPreco).where(TipoPreco.codigo == codigo.lower())
    )
    tipo = result.scalar_one_or_none()

    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de preço não encontrado")

    return tipo


@router.post("", response_model=TipoPrecoResponse, status_code=201)
async def create_tipo_preco(
    data: TipoPrecoCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cria um novo tipo de preço."""
    # Verificar se código já existe
    existing = await db.execute(
        select(TipoPreco).where(TipoPreco.codigo == data.codigo.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de preço com código '{data.codigo}' já existe"
        )

    tipo = TipoPreco(
        codigo=data.codigo.lower(),
        descricao=data.descricao,
        percentual_desconto=data.percentual_desconto,
        firebird_id=data.firebird_id,
    )

    db.add(tipo)
    await db.commit()
    await db.refresh(tipo)

    return tipo


@router.patch("/{tipo_id}", response_model=TipoPrecoResponse)
async def update_tipo_preco(
    tipo_id: UUID,
    data: TipoPrecoUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza um tipo de preço."""
    result = await db.execute(
        select(TipoPreco).where(TipoPreco.id == tipo_id)
    )
    tipo = result.scalar_one_or_none()

    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de preço não encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tipo, field, value)

    await db.commit()
    await db.refresh(tipo)

    return tipo


@router.delete("/{tipo_id}")
async def delete_tipo_preco(
    tipo_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Desativa um tipo de preço (soft delete)."""
    result = await db.execute(
        select(TipoPreco).where(TipoPreco.id == tipo_id)
    )
    tipo = result.scalar_one_or_none()

    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de preço não encontrado")

    tipo.ativo = False
    await db.commit()

    return {"message": "Tipo de preço desativado", "id": str(tipo_id)}


# ==================== PREÇOS POR PRODUTO ====================

@router.get("/produtos/precos", response_model=list[ProdutoPrecoResponse])
async def list_produto_precos(
    produto_id: Optional[UUID] = Query(None, description="Filtrar por produto"),
    tipo_preco_id: Optional[UUID] = Query(None, description="Filtrar por tipo"),
    vigentes_only: bool = Query(True, description="Apenas preços vigentes"),
    db: AsyncSession = Depends(get_db),
):
    """Lista preços por produto/modalidade."""
    query = select(ProdutoPreco)

    if produto_id:
        query = query.where(ProdutoPreco.produto_id == produto_id)

    if tipo_preco_id:
        query = query.where(ProdutoPreco.tipo_preco_id == tipo_preco_id)

    if vigentes_only:
        hoje = date.today()
        query = query.where(
            and_(
                ProdutoPreco.vigencia_inicio <= hoje,
                or_(
                    ProdutoPreco.vigencia_fim.is_(None),
                    ProdutoPreco.vigencia_fim >= hoje
                )
            )
        )

    result = await db.execute(query)
    precos = result.scalars().all()

    # Enriquecer com nomes
    response = []
    for p in precos:
        # Buscar produto
        prod_result = await db.execute(select(Product).where(Product.id == p.produto_id))
        produto = prod_result.scalar_one_or_none()

        # Buscar tipo
        tipo_result = await db.execute(select(TipoPreco).where(TipoPreco.id == p.tipo_preco_id))
        tipo = tipo_result.scalar_one_or_none()

        response.append(ProdutoPrecoResponse(
            id=p.id,
            produto_id=p.produto_id,
            tipo_preco_id=p.tipo_preco_id,
            preco=p.preco,
            vigencia_inicio=p.vigencia_inicio,
            vigencia_fim=p.vigencia_fim,
            created_at=p.created_at,
            updated_at=p.updated_at,
            produto_nome=produto.name if produto else None,
            tipo_preco_codigo=tipo.codigo if tipo else None,
        ))

    return response


@router.post("/produtos/precos", response_model=ProdutoPrecoResponse, status_code=201)
async def create_produto_preco(
    data: ProdutoPrecoCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cria um preço para produto/modalidade."""
    # Verificar se produto existe
    prod_result = await db.execute(select(Product).where(Product.id == data.produto_id))
    produto = prod_result.scalar_one_or_none()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Verificar se tipo de preço existe
    tipo_result = await db.execute(select(TipoPreco).where(TipoPreco.id == data.tipo_preco_id))
    tipo = tipo_result.scalar_one_or_none()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de preço não encontrado")

    preco = ProdutoPreco(
        produto_id=data.produto_id,
        tipo_preco_id=data.tipo_preco_id,
        preco=data.preco,
        vigencia_inicio=data.vigencia_inicio,
        vigencia_fim=data.vigencia_fim,
    )

    db.add(preco)
    await db.commit()
    await db.refresh(preco)

    return ProdutoPrecoResponse(
        id=preco.id,
        produto_id=preco.produto_id,
        tipo_preco_id=preco.tipo_preco_id,
        preco=preco.preco,
        vigencia_inicio=preco.vigencia_inicio,
        vigencia_fim=preco.vigencia_fim,
        created_at=preco.created_at,
        updated_at=preco.updated_at,
        produto_nome=produto.name,
        tipo_preco_codigo=tipo.codigo,
    )


@router.patch("/produtos/precos/{preco_id}", response_model=ProdutoPrecoResponse)
async def update_produto_preco(
    preco_id: UUID,
    data: ProdutoPrecoUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza um preço de produto."""
    result = await db.execute(
        select(ProdutoPreco).where(ProdutoPreco.id == preco_id)
    )
    preco = result.scalar_one_or_none()

    if not preco:
        raise HTTPException(status_code=404, detail="Preço não encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preco, field, value)

    await db.commit()
    await db.refresh(preco)

    # Buscar nomes
    prod_result = await db.execute(select(Product).where(Product.id == preco.produto_id))
    produto = prod_result.scalar_one_or_none()
    tipo_result = await db.execute(select(TipoPreco).where(TipoPreco.id == preco.tipo_preco_id))
    tipo = tipo_result.scalar_one_or_none()

    return ProdutoPrecoResponse(
        id=preco.id,
        produto_id=preco.produto_id,
        tipo_preco_id=preco.tipo_preco_id,
        preco=preco.preco,
        vigencia_inicio=preco.vigencia_inicio,
        vigencia_fim=preco.vigencia_fim,
        created_at=preco.created_at,
        updated_at=preco.updated_at,
        produto_nome=produto.name if produto else None,
        tipo_preco_codigo=tipo.codigo if tipo else None,
    )


@router.delete("/produtos/precos/{preco_id}")
async def delete_produto_preco(
    preco_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove um preço de produto."""
    result = await db.execute(
        select(ProdutoPreco).where(ProdutoPreco.id == preco_id)
    )
    preco = result.scalar_one_or_none()

    if not preco:
        raise HTTPException(status_code=404, detail="Preço não encontrado")

    await db.delete(preco)
    await db.commit()

    return {"message": "Preço removido", "id": str(preco_id)}


# ==================== UTILITÁRIO: BUSCAR PREÇO ====================

@router.get("/buscar-preco/{produto_id}")
async def buscar_preco_produto(
    produto_id: UUID,
    tipo_preco_codigo: str = Query("varejo", description="Código do tipo de preço"),
    db: AsyncSession = Depends(get_db),
):
    """
    Busca o preço de um produto para uma modalidade.
    Se não houver preço específico, retorna o preço padrão do produto.
    """
    # Buscar produto
    prod_result = await db.execute(select(Product).where(Product.id == produto_id))
    produto = prod_result.scalar_one_or_none()

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Buscar tipo de preço
    tipo_result = await db.execute(
        select(TipoPreco).where(TipoPreco.codigo == tipo_preco_codigo.lower())
    )
    tipo = tipo_result.scalar_one_or_none()

    if not tipo:
        # Se tipo não existe, usar preço padrão do produto
        return {
            "produto_id": str(produto_id),
            "produto_nome": produto.name,
            "tipo_preco": "varejo",
            "preco": float(produto.price),
            "fonte": "preco_padrao"
        }

    # Buscar preço específico vigente
    hoje = date.today()
    preco_result = await db.execute(
        select(ProdutoPreco).where(
            and_(
                ProdutoPreco.produto_id == produto_id,
                ProdutoPreco.tipo_preco_id == tipo.id,
                ProdutoPreco.vigencia_inicio <= hoje,
                or_(
                    ProdutoPreco.vigencia_fim.is_(None),
                    ProdutoPreco.vigencia_fim >= hoje
                )
            )
        ).order_by(ProdutoPreco.vigencia_inicio.desc())
    )
    preco_especifico = preco_result.scalar_one_or_none()

    if preco_especifico:
        return {
            "produto_id": str(produto_id),
            "produto_nome": produto.name,
            "tipo_preco": tipo.codigo,
            "preco": float(preco_especifico.preco),
            "fonte": "preco_especifico"
        }

    # Calcular preço com desconto padrão do tipo
    preco_com_desconto = float(produto.price) * (1 - float(tipo.percentual_desconto) / 100)

    return {
        "produto_id": str(produto_id),
        "produto_nome": produto.name,
        "tipo_preco": tipo.codigo,
        "preco": round(preco_com_desconto, 2),
        "fonte": "desconto_padrao",
        "desconto_aplicado": float(tipo.percentual_desconto)
    }
