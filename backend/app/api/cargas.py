"""
API de Cargas de Veículo.
Endpoints para gerenciar cargas dos motoristas.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import CargaVeiculo, CargaItem, CargaStatus, Driver, Product
from app.models.auth_models import User
from app.auth import get_current_user
from app.schemas.carga import (
    CargaCreate,
    CargaUpdate,
    CargaSaidaRequest,
    CargaAcertoRequest,
    CargaResponse,
    CargaBrief,
    CargaAtualResponse,
    CargaItemResponse,
)

router = APIRouter()


def _build_carga_response(carga: CargaVeiculo) -> dict:
    """Constrói resposta da carga com dados relacionados."""
    itens_response = []
    total_produtos = 0

    for item in carga.itens:
        total_produtos += item.qtd_saida
        itens_response.append({
            "id": item.id,
            "carga_id": item.carga_id,
            "produto_id": item.produto_id,
            "produto_nome": item.produto.name if item.produto else None,
            "produto_codigo": item.produto.code if item.produto else None,
            "qtd_saida": item.qtd_saida,
            "qtd_retorno_cheio": item.qtd_retorno_cheio,
            "qtd_retorno_vazio": item.qtd_retorno_vazio,
            "qtd_vendida": item.qtd_vendida,
            "qtd_pendente": item.qtd_pendente,
            "created_at": item.created_at,
        })

    return {
        "id": carga.id,
        "driver_id": carga.driver_id,
        "driver_nome": carga.driver.name if carga.driver else None,
        "status": carga.status,
        "data_saida": carga.data_saida,
        "data_retorno": carga.data_retorno,
        "observacoes": carga.observacoes,
        "itens": itens_response,
        "total_itens": len(itens_response),
        "total_produtos": total_produtos,
        "created_at": carga.created_at,
        "updated_at": carga.updated_at,
    }


@router.get("", response_model=List[CargaBrief])
async def listar_cargas(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    driver_id: Optional[UUID] = Query(None, description="Filtrar por motorista"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Lista cargas de veículo.

    Filtros disponíveis:
    - status: criada, em_rota, finalizada
    - driver_id: ID do motorista
    """
    query = select(CargaVeiculo).options(
        selectinload(CargaVeiculo.driver),
        selectinload(CargaVeiculo.itens)
    )

    # Aplicar filtros
    if status:
        query = query.where(CargaVeiculo.status == status)
    if driver_id:
        query = query.where(CargaVeiculo.driver_id == driver_id)

    # Ordenar por data de criação (mais recente primeiro)
    query = query.order_by(CargaVeiculo.created_at.desc())
    query = query.limit(limit).offset(offset)

    result = await session.execute(query)
    cargas = result.scalars().all()

    return [
        {
            "id": c.id,
            "driver_id": c.driver_id,
            "driver_nome": c.driver.name if c.driver else None,
            "status": c.status,
            "data_saida": c.data_saida,
            "total_itens": len(c.itens),
            "total_produtos": sum(i.qtd_saida for i in c.itens),
            "created_at": c.created_at,
        }
        for c in cargas
    ]


@router.post("", response_model=CargaResponse)
async def criar_carga(
    data: CargaCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Cria uma nova carga de veículo.

    Requer:
    - driver_id: ID do motorista
    - itens: Lista de produtos com quantidade
    """
    # Verificar se motorista existe
    driver_result = await session.execute(
        select(Driver).where(Driver.id == data.driver_id)
    )
    driver = driver_result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Motorista não encontrado")

    # Verificar se motorista já tem carga ativa (criada ou em_rota)
    carga_ativa_result = await session.execute(
        select(CargaVeiculo).where(
            and_(
                CargaVeiculo.driver_id == data.driver_id,
                CargaVeiculo.status.in_([CargaStatus.CRIADA.value, CargaStatus.EM_ROTA.value])
            )
        )
    )
    carga_ativa = carga_ativa_result.scalar_one_or_none()
    if carga_ativa:
        raise HTTPException(
            status_code=400,
            detail="Motorista já possui uma carga ativa. Finalize a carga atual antes de criar outra."
        )

    # Criar carga
    carga = CargaVeiculo(
        driver_id=data.driver_id,
        status=CargaStatus.CRIADA.value,
        observacoes=data.observacoes,
    )
    session.add(carga)
    await session.flush()  # Para obter o ID da carga

    # Adicionar itens
    for item_data in data.itens:
        # Verificar se produto existe
        produto_result = await session.execute(
            select(Product).where(Product.id == item_data.produto_id)
        )
        produto = produto_result.scalar_one_or_none()
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto {item_data.produto_id} não encontrado"
            )

        item = CargaItem(
            carga_id=carga.id,
            produto_id=item_data.produto_id,
            qtd_saida=item_data.qtd_saida,
        )
        session.add(item)

    await session.commit()

    # Recarregar com relacionamentos
    await session.refresh(carga)
    result = await session.execute(
        select(CargaVeiculo)
        .options(
            selectinload(CargaVeiculo.driver),
            selectinload(CargaVeiculo.itens).selectinload(CargaItem.produto)
        )
        .where(CargaVeiculo.id == carga.id)
    )
    carga = result.scalar_one()

    return _build_carga_response(carga)


@router.get("/{carga_id}", response_model=CargaResponse)
async def obter_carga(
    carga_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Obtém detalhes de uma carga."""
    result = await session.execute(
        select(CargaVeiculo)
        .options(
            selectinload(CargaVeiculo.driver),
            selectinload(CargaVeiculo.itens).selectinload(CargaItem.produto)
        )
        .where(CargaVeiculo.id == carga_id)
    )
    carga = result.scalar_one_or_none()

    if not carga:
        raise HTTPException(status_code=404, detail="Carga não encontrada")

    return _build_carga_response(carga)


@router.post("/{carga_id}/saida", response_model=CargaResponse)
async def registrar_saida(
    carga_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Registra a saída do motorista com a carga.
    Muda o status de 'criada' para 'em_rota'.
    """
    result = await session.execute(
        select(CargaVeiculo)
        .options(
            selectinload(CargaVeiculo.driver),
            selectinload(CargaVeiculo.itens).selectinload(CargaItem.produto)
        )
        .where(CargaVeiculo.id == carga_id)
    )
    carga = result.scalar_one_or_none()

    if not carga:
        raise HTTPException(status_code=404, detail="Carga não encontrada")

    if carga.status != CargaStatus.CRIADA.value:
        raise HTTPException(
            status_code=400,
            detail=f"Carga não está no status 'criada'. Status atual: {carga.status}"
        )

    carga.registrar_saida()
    await session.commit()
    await session.refresh(carga)

    return _build_carga_response(carga)


@router.post("/{carga_id}/acerto", response_model=CargaResponse)
async def realizar_acerto(
    carga_id: UUID,
    data: CargaAcertoRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Realiza o acerto da carga (retorno do motorista).

    Para cada item, informar:
    - qtd_retorno_cheio: Quantidade que voltou cheia
    - qtd_retorno_vazio: Quantidade de vazios que voltou
    - qtd_vendida: Quantidade vendida
    """
    result = await session.execute(
        select(CargaVeiculo)
        .options(
            selectinload(CargaVeiculo.driver),
            selectinload(CargaVeiculo.itens).selectinload(CargaItem.produto)
        )
        .where(CargaVeiculo.id == carga_id)
    )
    carga = result.scalar_one_or_none()

    if not carga:
        raise HTTPException(status_code=404, detail="Carga não encontrada")

    if carga.status != CargaStatus.EM_ROTA.value:
        raise HTTPException(
            status_code=400,
            detail=f"Carga não está em rota. Status atual: {carga.status}"
        )

    # Criar mapa de itens da carga para atualização
    itens_map = {str(item.produto_id): item for item in carga.itens}

    # Atualizar cada item
    for item_acerto in data.itens:
        item = itens_map.get(str(item_acerto.produto_id))
        if not item:
            raise HTTPException(
                status_code=400,
                detail=f"Produto {item_acerto.produto_id} não está na carga"
            )

        # Validar que o acerto não excede a saída
        total_retorno = item_acerto.qtd_vendida + item_acerto.qtd_retorno_cheio
        if total_retorno > item.qtd_saida:
            raise HTTPException(
                status_code=400,
                detail=f"Acerto inválido para produto {item_acerto.produto_id}: "
                       f"vendido({item_acerto.qtd_vendida}) + retorno_cheio({item_acerto.qtd_retorno_cheio}) "
                       f"excede a saída({item.qtd_saida})"
            )

        item.qtd_retorno_cheio = item_acerto.qtd_retorno_cheio
        item.qtd_retorno_vazio = item_acerto.qtd_retorno_vazio
        item.qtd_vendida = item_acerto.qtd_vendida

    # Finalizar carga
    carga.finalizar()
    if data.observacoes:
        carga.observacoes = (carga.observacoes or "") + f"\n[Acerto] {data.observacoes}"

    await session.commit()
    await session.refresh(carga)

    # Recarregar com relacionamentos
    result = await session.execute(
        select(CargaVeiculo)
        .options(
            selectinload(CargaVeiculo.driver),
            selectinload(CargaVeiculo.itens).selectinload(CargaItem.produto)
        )
        .where(CargaVeiculo.id == carga_id)
    )
    carga = result.scalar_one()

    return _build_carga_response(carga)


@router.get("/driver/{driver_id}/atual", response_model=CargaAtualResponse)
async def obter_carga_atual_motorista(
    driver_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Obtém a carga atual (ativa) do motorista.
    Retorna carga com status 'criada' ou 'em_rota'.
    """
    result = await session.execute(
        select(CargaVeiculo)
        .options(
            selectinload(CargaVeiculo.driver),
            selectinload(CargaVeiculo.itens).selectinload(CargaItem.produto)
        )
        .where(
            and_(
                CargaVeiculo.driver_id == driver_id,
                CargaVeiculo.status.in_([CargaStatus.CRIADA.value, CargaStatus.EM_ROTA.value])
            )
        )
    )
    carga = result.scalar_one_or_none()

    if not carga:
        return {"tem_carga": False, "carga": None}

    return {
        "tem_carga": True,
        "carga": _build_carga_response(carga)
    }


@router.delete("/{carga_id}")
async def excluir_carga(
    carga_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Exclui uma carga.
    Só pode excluir cargas com status 'criada'.
    """
    result = await session.execute(
        select(CargaVeiculo).where(CargaVeiculo.id == carga_id)
    )
    carga = result.scalar_one_or_none()

    if not carga:
        raise HTTPException(status_code=404, detail="Carga não encontrada")

    if carga.status != CargaStatus.CRIADA.value:
        raise HTTPException(
            status_code=400,
            detail="Só é possível excluir cargas com status 'criada'"
        )

    await session.delete(carga)
    await session.commit()

    return {"message": "Carga excluída com sucesso"}
