"""
API de Comodatos (Empréstimo de Equipamentos).
"""

import logging
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel as _Pydantic
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.auth_models import User
from app.models.comodato import Comodato, ComodatoStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comodatos", tags=["Comodatos"])

ALLOWED_ROLES = ("admin", "owner", "operator")


def _require_operator(user: User):
    if user.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Acesso negado")


# ── Schemas ────────────────────────────────────────────────

class ComodatoCreate(_Pydantic):
    customer_id: UUID
    equipamento: str
    numero_serie: Optional[str] = None
    quantidade: int = 1
    valor_caucao: Optional[float] = None
    data_emprestimo: date
    data_prevista_devolucao: Optional[date] = None
    observacao: Optional[str] = None


class ComodatoUpdate(_Pydantic):
    equipamento: Optional[str] = None
    numero_serie: Optional[str] = None
    quantidade: Optional[int] = None
    valor_caucao: Optional[float] = None
    data_prevista_devolucao: Optional[date] = None
    observacao: Optional[str] = None


class DevolucaoBody(_Pydantic):
    data_devolucao: Optional[date] = None
    observacao: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────

@router.post("", status_code=201)
async def criar_comodato(
    body: ComodatoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra um novo empréstimo de equipamento."""
    _require_operator(current_user)

    from app.models.customer import Customer
    cust = await db.get(Customer, body.customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    comodato = Comodato(
        customer_id=body.customer_id,
        equipamento=body.equipamento,
        numero_serie=body.numero_serie,
        quantidade=body.quantidade,
        valor_caucao=body.valor_caucao,
        data_emprestimo=body.data_emprestimo,
        data_prevista_devolucao=body.data_prevista_devolucao,
        observacao=body.observacao,
        created_by=current_user.id,
    )
    db.add(comodato)
    await db.commit()
    await db.refresh(comodato)
    return _to_dict(comodato)


@router.get("")
async def listar_comodatos(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista comodatos com filtros opcionais."""
    _require_operator(current_user)

    filters = [Comodato.deleted_at == None]
    if customer_id:
        filters.append(Comodato.customer_id == customer_id)
    if status:
        filters.append(Comodato.status == status)

    result = await db.execute(
        select(Comodato).where(and_(*filters)).order_by(Comodato.data_emprestimo.desc())
    )
    return [_to_dict(c) for c in result.scalars().all()]


@router.get("/ativos/count")
async def count_ativos_por_equipamento(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Conta equipamentos ativos agrupados por tipo."""
    _require_operator(current_user)
    from sqlalchemy import func

    result = await db.execute(
        select(Comodato.equipamento, func.sum(Comodato.quantidade).label("total"))
        .where(and_(Comodato.status == ComodatoStatus.ATIVO.value, Comodato.deleted_at == None))
        .group_by(Comodato.equipamento)
        .order_by(func.sum(Comodato.quantidade).desc())
    )
    return [{"equipamento": r[0], "total": int(r[1])} for r in result.all()]


@router.get("/{comodato_id}")
async def detalhe_comodato(
    comodato_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_operator(current_user)
    comodato = await db.get(Comodato, comodato_id)
    if not comodato or comodato.deleted_at:
        raise HTTPException(status_code=404, detail="Comodato não encontrado")
    return _to_dict(comodato)


@router.patch("/{comodato_id}")
async def atualizar_comodato(
    comodato_id: UUID,
    body: ComodatoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_operator(current_user)
    comodato = await db.get(Comodato, comodato_id)
    if not comodato or comodato.deleted_at:
        raise HTTPException(status_code=404, detail="Comodato não encontrado")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(comodato, field, value)

    await db.commit()
    await db.refresh(comodato)
    return _to_dict(comodato)


@router.post("/{comodato_id}/devolver")
async def registrar_devolucao(
    comodato_id: UUID,
    body: DevolucaoBody = DevolucaoBody(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra a devolução de um equipamento emprestado."""
    _require_operator(current_user)
    comodato = await db.get(Comodato, comodato_id)
    if not comodato or comodato.deleted_at:
        raise HTTPException(status_code=404, detail="Comodato não encontrado")
    if comodato.status != ComodatoStatus.ATIVO.value:
        raise HTTPException(status_code=409, detail=f"Comodato já está {comodato.status}")

    comodato.status = ComodatoStatus.DEVOLVIDO.value
    comodato.data_devolucao = body.data_devolucao or date.today()
    if body.observacao:
        comodato.observacao = (comodato.observacao or "") + f"\n[Devolução] {body.observacao}"

    await db.commit()
    await db.refresh(comodato)
    return _to_dict(comodato)


@router.delete("/{comodato_id}", status_code=204)
async def deletar_comodato(
    comodato_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_operator(current_user)
    comodato = await db.get(Comodato, comodato_id)
    if not comodato or comodato.deleted_at:
        raise HTTPException(status_code=404, detail="Comodato não encontrado")

    comodato.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ── Helper ─────────────────────────────────────────────────

def _to_dict(c: Comodato) -> dict:
    return {
        "id": str(c.id),
        "customer_id": str(c.customer_id),
        "equipamento": c.equipamento,
        "numero_serie": c.numero_serie,
        "quantidade": c.quantidade,
        "valor_caucao": float(c.valor_caucao) if c.valor_caucao else None,
        "data_emprestimo": c.data_emprestimo.isoformat() if c.data_emprestimo else None,
        "data_prevista_devolucao": c.data_prevista_devolucao.isoformat() if c.data_prevista_devolucao else None,
        "data_devolucao": c.data_devolucao.isoformat() if c.data_devolucao else None,
        "status": c.status,
        "observacao": c.observacao,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
