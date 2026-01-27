"""
API de Vasilhames e Controle de Comodato.
Gerencia botijões emprestados aos clientes.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vasilhame import Vasilhame, ClienteVasilhame, MovimentacaoVasilhame
from app.models.customer import Customer
from app.schemas.vasilhame import (
    VasilhameCreate,
    VasilhameResponse,
    VasilhameUpdate,
    ClienteVasilhameCreate,
    ClienteVasilhameResponse,
    ClienteVasilhameUpdate,
    MovimentacaoCreate,
    MovimentacaoResponse,
    ResumoVasilhamesCliente,
    RegistrarVendaVasilhame,
    RegistrarDevolucao,
)

router = APIRouter()


# ==================== VASILHAMES (TIPOS) ====================

@router.get("", response_model=list[VasilhameResponse])
async def list_vasilhames(
    ativos_only: bool = Query(True, description="Apenas vasilhames ativos"),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os tipos de vasilhame."""
    query = select(Vasilhame)

    if ativos_only:
        query = query.where(Vasilhame.ativo == True)

    query = query.order_by(Vasilhame.codigo)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{vasilhame_id}", response_model=VasilhameResponse)
async def get_vasilhame(
    vasilhame_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Busca vasilhame por ID."""
    result = await db.execute(
        select(Vasilhame).where(Vasilhame.id == vasilhame_id)
    )
    vasilhame = result.scalar_one_or_none()

    if not vasilhame:
        raise HTTPException(status_code=404, detail="Vasilhame não encontrado")

    return vasilhame


@router.post("", response_model=VasilhameResponse, status_code=201)
async def create_vasilhame(
    data: VasilhameCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cria um novo tipo de vasilhame."""
    # Verificar código único
    existing = await db.execute(
        select(Vasilhame).where(Vasilhame.codigo == data.codigo.upper())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Vasilhame com código '{data.codigo}' já existe"
        )

    vasilhame = Vasilhame(
        codigo=data.codigo.upper(),
        descricao=data.descricao,
        peso_kg=data.peso_kg,
        valor_caucao=data.valor_caucao,
        firebird_id=data.firebird_id,
    )

    db.add(vasilhame)
    await db.commit()
    await db.refresh(vasilhame)

    return vasilhame


@router.patch("/{vasilhame_id}", response_model=VasilhameResponse)
async def update_vasilhame(
    vasilhame_id: UUID,
    data: VasilhameUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza um vasilhame."""
    result = await db.execute(
        select(Vasilhame).where(Vasilhame.id == vasilhame_id)
    )
    vasilhame = result.scalar_one_or_none()

    if not vasilhame:
        raise HTTPException(status_code=404, detail="Vasilhame não encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vasilhame, field, value)

    await db.commit()
    await db.refresh(vasilhame)

    return vasilhame


@router.delete("/{vasilhame_id}")
async def delete_vasilhame(
    vasilhame_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Desativa um vasilhame (soft delete)."""
    result = await db.execute(
        select(Vasilhame).where(Vasilhame.id == vasilhame_id)
    )
    vasilhame = result.scalar_one_or_none()

    if not vasilhame:
        raise HTTPException(status_code=404, detail="Vasilhame não encontrado")

    vasilhame.ativo = False
    await db.commit()

    return {"message": "Vasilhame desativado", "id": str(vasilhame_id)}


# ==================== CLIENTE VASILHAMES ====================

@router.get("/cliente/{customer_id}", response_model=ResumoVasilhamesCliente)
async def get_vasilhames_cliente(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Busca resumo de vasilhames de um cliente."""
    # Buscar cliente
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Buscar vasilhames do cliente
    query = select(ClienteVasilhame).where(
        ClienteVasilhame.customer_id == customer_id
    )
    result = await db.execute(query)
    cliente_vasilhames = result.scalars().all()

    # Enriquecer dados
    itens = []
    total_vasilhames = 0
    total_caucao = Decimal("0.00")

    for cv in cliente_vasilhames:
        # Buscar vasilhame
        vas_result = await db.execute(
            select(Vasilhame).where(Vasilhame.id == cv.vasilhame_id)
        )
        vasilhame = vas_result.scalar_one_or_none()

        itens.append(ClienteVasilhameResponse(
            id=cv.id,
            customer_id=cv.customer_id,
            vasilhame_id=cv.vasilhame_id,
            quantidade=cv.quantidade,
            valor_caucao_pago=cv.valor_caucao_pago,
            data_primeiro_emprestimo=cv.data_primeiro_emprestimo,
            observacoes=cv.observacoes,
            created_at=cv.created_at,
            updated_at=cv.updated_at,
            vasilhame_codigo=vasilhame.codigo if vasilhame else None,
            vasilhame_descricao=vasilhame.descricao if vasilhame else None,
            customer_nome=customer.name,
        ))

        total_vasilhames += cv.quantidade
        total_caucao += cv.valor_caucao_pago

    return ResumoVasilhamesCliente(
        customer_id=customer_id,
        customer_nome=customer.name or "Sem nome",
        total_vasilhames=total_vasilhames,
        total_caucao_pago=total_caucao,
        itens=itens,
    )


@router.post("/cliente", response_model=ClienteVasilhameResponse, status_code=201)
async def add_vasilhame_cliente(
    data: ClienteVasilhameCreate,
    db: AsyncSession = Depends(get_db),
):
    """Adiciona/atualiza vasilhame de um cliente."""
    # Verificar cliente
    customer_result = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Verificar vasilhame
    vas_result = await db.execute(
        select(Vasilhame).where(Vasilhame.id == data.vasilhame_id)
    )
    vasilhame = vas_result.scalar_one_or_none()
    if not vasilhame:
        raise HTTPException(status_code=404, detail="Vasilhame não encontrado")

    # Verificar se já existe registro
    existing_result = await db.execute(
        select(ClienteVasilhame).where(
            ClienteVasilhame.customer_id == data.customer_id,
            ClienteVasilhame.vasilhame_id == data.vasilhame_id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Atualizar existente
        existing.quantidade = data.quantidade
        if data.valor_caucao_pago is not None:
            existing.valor_caucao_pago = data.valor_caucao_pago
        if data.observacoes:
            existing.observacoes = data.observacoes
        await db.commit()
        await db.refresh(existing)
        cliente_vasilhame = existing
    else:
        # Criar novo
        cliente_vasilhame = ClienteVasilhame(
            customer_id=data.customer_id,
            vasilhame_id=data.vasilhame_id,
            quantidade=data.quantidade,
            valor_caucao_pago=data.valor_caucao_pago or Decimal("0.00"),
            data_primeiro_emprestimo=datetime.now() if data.quantidade > 0 else None,
            observacoes=data.observacoes,
        )
        db.add(cliente_vasilhame)
        await db.commit()
        await db.refresh(cliente_vasilhame)

    return ClienteVasilhameResponse(
        id=cliente_vasilhame.id,
        customer_id=cliente_vasilhame.customer_id,
        vasilhame_id=cliente_vasilhame.vasilhame_id,
        quantidade=cliente_vasilhame.quantidade,
        valor_caucao_pago=cliente_vasilhame.valor_caucao_pago,
        data_primeiro_emprestimo=cliente_vasilhame.data_primeiro_emprestimo,
        observacoes=cliente_vasilhame.observacoes,
        created_at=cliente_vasilhame.created_at,
        updated_at=cliente_vasilhame.updated_at,
        vasilhame_codigo=vasilhame.codigo,
        vasilhame_descricao=vasilhame.descricao,
        customer_nome=customer.name,
    )


# ==================== OPERAÇÕES DE VENDA/DEVOLUÇÃO ====================

@router.post("/venda", response_model=ClienteVasilhameResponse)
async def registrar_venda(
    data: RegistrarVendaVasilhame,
    db: AsyncSession = Depends(get_db),
):
    """
    Registra venda de vasilhame (cliente novo sem botijão).
    Incrementa quantidade e registra caução paga.
    """
    # Buscar vasilhame para pegar valor caução
    vas_result = await db.execute(
        select(Vasilhame).where(Vasilhame.id == data.vasilhame_id)
    )
    vasilhame = vas_result.scalar_one_or_none()
    if not vasilhame:
        raise HTTPException(status_code=404, detail="Vasilhame não encontrado")

    # Buscar cliente
    customer_result = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Buscar ou criar registro
    existing_result = await db.execute(
        select(ClienteVasilhame).where(
            ClienteVasilhame.customer_id == data.customer_id,
            ClienteVasilhame.vasilhame_id == data.vasilhame_id,
        )
    )
    cliente_vasilhame = existing_result.scalar_one_or_none()

    valor_caucao = vasilhame.valor_caucao * data.quantidade

    if cliente_vasilhame:
        cliente_vasilhame.quantidade += data.quantidade
        cliente_vasilhame.valor_caucao_pago += valor_caucao
    else:
        cliente_vasilhame = ClienteVasilhame(
            customer_id=data.customer_id,
            vasilhame_id=data.vasilhame_id,
            quantidade=data.quantidade,
            valor_caucao_pago=valor_caucao,
            data_primeiro_emprestimo=datetime.now(),
        )
        db.add(cliente_vasilhame)

    await db.flush()

    # Registrar movimentação
    movimentacao = MovimentacaoVasilhame(
        cliente_vasilhame_id=cliente_vasilhame.id,
        tipo="ENTRADA",
        quantidade=data.quantidade,
        valor_caucao=valor_caucao,
        order_id=data.order_id,
        motivo="venda",
    )
    db.add(movimentacao)

    await db.commit()
    await db.refresh(cliente_vasilhame)

    return ClienteVasilhameResponse(
        id=cliente_vasilhame.id,
        customer_id=cliente_vasilhame.customer_id,
        vasilhame_id=cliente_vasilhame.vasilhame_id,
        quantidade=cliente_vasilhame.quantidade,
        valor_caucao_pago=cliente_vasilhame.valor_caucao_pago,
        data_primeiro_emprestimo=cliente_vasilhame.data_primeiro_emprestimo,
        observacoes=cliente_vasilhame.observacoes,
        created_at=cliente_vasilhame.created_at,
        updated_at=cliente_vasilhame.updated_at,
        vasilhame_codigo=vasilhame.codigo,
        vasilhame_descricao=vasilhame.descricao,
        customer_nome=customer.name,
    )


@router.post("/devolucao", response_model=dict)
async def registrar_devolucao(
    data: RegistrarDevolucao,
    db: AsyncSession = Depends(get_db),
):
    """
    Registra devolução de vasilhame.
    Decrementa quantidade e opcionalmente devolve caução.
    """
    # Buscar registro do cliente
    existing_result = await db.execute(
        select(ClienteVasilhame).where(
            ClienteVasilhame.customer_id == data.customer_id,
            ClienteVasilhame.vasilhame_id == data.vasilhame_id,
        )
    )
    cliente_vasilhame = existing_result.scalar_one_or_none()

    if not cliente_vasilhame:
        raise HTTPException(
            status_code=404,
            detail="Cliente não possui vasilhame deste tipo"
        )

    if cliente_vasilhame.quantidade < data.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Cliente possui apenas {cliente_vasilhame.quantidade} vasilhame(s)"
        )

    # Buscar vasilhame
    vas_result = await db.execute(
        select(Vasilhame).where(Vasilhame.id == data.vasilhame_id)
    )
    vasilhame = vas_result.scalar_one_or_none()

    # Calcular caução a devolver
    valor_caucao_devolver = Decimal("0.00")
    if data.devolver_caucao:
        valor_caucao_devolver = vasilhame.valor_caucao * data.quantidade

    # Atualizar
    cliente_vasilhame.quantidade -= data.quantidade
    cliente_vasilhame.valor_caucao_pago -= valor_caucao_devolver
    if cliente_vasilhame.valor_caucao_pago < 0:
        cliente_vasilhame.valor_caucao_pago = Decimal("0.00")

    # Registrar movimentação
    movimentacao = MovimentacaoVasilhame(
        cliente_vasilhame_id=cliente_vasilhame.id,
        tipo="SAIDA",
        quantidade=data.quantidade,
        valor_caucao=valor_caucao_devolver,
        motivo="devolucao",
        observacoes=data.observacoes,
    )
    db.add(movimentacao)

    await db.commit()

    return {
        "message": "Devolução registrada",
        "quantidade_devolvida": data.quantidade,
        "valor_caucao_devolvido": float(valor_caucao_devolver),
        "quantidade_restante": cliente_vasilhame.quantidade,
    }


# ==================== MOVIMENTAÇÕES ====================

@router.get("/movimentacoes/{customer_id}", response_model=list[MovimentacaoResponse])
async def get_movimentacoes_cliente(
    customer_id: UUID,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lista movimentações de vasilhames de um cliente."""
    # Buscar cliente_vasilhames do cliente
    cv_result = await db.execute(
        select(ClienteVasilhame.id).where(
            ClienteVasilhame.customer_id == customer_id
        )
    )
    cv_ids = [row[0] for row in cv_result.all()]

    if not cv_ids:
        return []

    # Buscar movimentações
    query = select(MovimentacaoVasilhame).where(
        MovimentacaoVasilhame.cliente_vasilhame_id.in_(cv_ids)
    ).order_by(MovimentacaoVasilhame.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


# ==================== RELATÓRIOS ====================

@router.get("/relatorio/geral")
async def relatorio_geral_vasilhames(
    db: AsyncSession = Depends(get_db),
):
    """Relatório geral de vasilhames em comodato."""
    # Total por tipo de vasilhame
    query = select(
        Vasilhame.codigo,
        Vasilhame.descricao,
        func.coalesce(func.sum(ClienteVasilhame.quantidade), 0).label("total_em_comodato"),
        func.coalesce(func.sum(ClienteVasilhame.valor_caucao_pago), 0).label("total_caucao"),
        func.count(ClienteVasilhame.id).label("total_clientes"),
    ).outerjoin(
        ClienteVasilhame, ClienteVasilhame.vasilhame_id == Vasilhame.id
    ).where(
        Vasilhame.ativo == True
    ).group_by(
        Vasilhame.id, Vasilhame.codigo, Vasilhame.descricao
    ).order_by(Vasilhame.codigo)

    result = await db.execute(query)
    rows = result.all()

    itens = []
    total_geral = 0
    total_caucao_geral = Decimal("0.00")

    for row in rows:
        itens.append({
            "codigo": row.codigo,
            "descricao": row.descricao,
            "total_em_comodato": row.total_em_comodato,
            "total_caucao": float(row.total_caucao),
            "total_clientes": row.total_clientes,
        })
        total_geral += row.total_em_comodato
        total_caucao_geral += row.total_caucao

    return {
        "data_geracao": datetime.now().isoformat(),
        "total_vasilhames_em_comodato": total_geral,
        "total_caucao_em_aberto": float(total_caucao_geral),
        "por_tipo": itens,
    }


@router.get("/relatorio/clientes-com-vasilhames")
async def relatorio_clientes_com_vasilhames(
    min_quantidade: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Lista clientes com vasilhames em comodato."""
    query = select(
        Customer.id,
        Customer.name,
        Customer.phone,
        func.sum(ClienteVasilhame.quantidade).label("total_vasilhames"),
        func.sum(ClienteVasilhame.valor_caucao_pago).label("total_caucao"),
    ).join(
        ClienteVasilhame, ClienteVasilhame.customer_id == Customer.id
    ).group_by(
        Customer.id, Customer.name, Customer.phone
    ).having(
        func.sum(ClienteVasilhame.quantidade) >= min_quantidade
    ).order_by(
        func.sum(ClienteVasilhame.quantidade).desc()
    )

    result = await db.execute(query)
    rows = result.all()

    return {
        "data_geracao": datetime.now().isoformat(),
        "total_clientes": len(rows),
        "clientes": [
            {
                "id": str(row.id),
                "nome": row.name or "Sem nome",
                "telefone": row.phone,
                "total_vasilhames": row.total_vasilhames,
                "total_caucao": float(row.total_caucao),
            }
            for row in rows
        ],
    }
