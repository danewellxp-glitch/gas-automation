"""
API de Acerto de Turno do Entregador.

Fluxo:
1. Driver inicia turno: POST /api/turno/iniciar
2. Driver lança cada entrega: POST /api/turno/{turno_id}/lancar-entrega
3. Driver finaliza turno: POST /api/turno/{turno_id}/finalizar
4. Operador/owner aprova ou rejeita: POST /api/turno/{turno_id}/aprovar|rejeitar
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel as _Pydantic
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.auth_models import User
from app.models.delivery import Delivery
from app.models.driver import Driver
from app.models.driver_turno import AcertoItemEntrega, DriverTurno, TurnoStatus
from app.models.order import Order

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/turno", tags=["Acerto de Turno"])


# ── Schemas ────────────────────────────────────────────────

class LancarEntregaBody(_Pydantic):
    delivery_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    valor_cobrado: Decimal
    payment_method: Optional[str] = None
    observacao: Optional[str] = None
    entregue: bool = True


class FinalizarTurnoBody(_Pydantic):
    observacao: Optional[str] = None


class AprovarTurnoBody(_Pydantic):
    observacao: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────

async def _get_driver_for_user(db: AsyncSession, user: User) -> Driver:
    result = await db.execute(
        select(Driver).where(Driver.phone == user.username)
    )
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail="Entregador não encontrado para este usuário")
    return driver


async def _get_turno_or_404(db: AsyncSession, turno_id: UUID) -> DriverTurno:
    result = await db.execute(
        select(DriverTurno).where(DriverTurno.id == turno_id)
    )
    turno = result.scalar_one_or_none()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno não encontrado")
    return turno


# ── Endpoints driver ───────────────────────────────────────

@router.post("/iniciar", status_code=201)
async def iniciar_turno(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Driver inicia um novo turno. Apenas um turno aberto por vez."""
    driver = await _get_driver_for_user(db, current_user)

    # Verificar turno aberto existente
    existing = await db.execute(
        select(DriverTurno).where(
            and_(
                DriverTurno.driver_id == driver.id,
                DriverTurno.status == TurnoStatus.ABERTO.value,
            )
        )
    )
    turno_aberto = existing.scalar_one_or_none()
    if turno_aberto:
        raise HTTPException(
            status_code=409,
            detail=f"Já existe um turno aberto (id={turno_aberto.id}). Finalize-o antes de iniciar outro.",
        )

    turno = DriverTurno(driver_id=driver.id)
    db.add(turno)
    await db.commit()
    await db.refresh(turno)
    return {"turno_id": str(turno.id), "status": turno.status, "iniciado_em": turno.iniciado_em}


@router.post("/{turno_id}/lancar-entrega", status_code=201)
async def lancar_entrega(
    turno_id: UUID,
    body: LancarEntregaBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Driver lança uma entrega no turno com o valor cobrado."""
    driver = await _get_driver_for_user(db, current_user)
    turno = await _get_turno_or_404(db, turno_id)

    if str(turno.driver_id) != str(driver.id):
        raise HTTPException(status_code=403, detail="Este turno não pertence a você")
    if turno.status != TurnoStatus.ABERTO.value:
        raise HTTPException(status_code=409, detail=f"Turno está {turno.status}, não pode lançar entregas")

    # Busca valor esperado do pedido
    valor_pedido = Decimal("0")
    if body.order_id:
        result = await db.execute(select(Order).where(Order.id == body.order_id))
        order = result.scalar_one_or_none()
        if order:
            valor_pedido = order.total_amount or Decimal("0")

    item = AcertoItemEntrega(
        turno_id=turno_id,
        delivery_id=body.delivery_id,
        order_id=body.order_id,
        valor_pedido=valor_pedido,
        valor_cobrado=body.valor_cobrado,
        payment_method=body.payment_method,
        observacao=body.observacao,
        entregue=body.entregue,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {
        "id": str(item.id),
        "valor_pedido": float(item.valor_pedido),
        "valor_cobrado": float(item.valor_cobrado),
        "entregue": item.entregue,
    }


@router.post("/{turno_id}/finalizar")
async def finalizar_turno(
    turno_id: UUID,
    body: FinalizarTurnoBody = FinalizarTurnoBody(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Driver finaliza o turno — calcula totais e envia para aprovação."""
    driver = await _get_driver_for_user(db, current_user)
    turno = await _get_turno_or_404(db, turno_id)

    if str(turno.driver_id) != str(driver.id):
        raise HTTPException(status_code=403, detail="Este turno não pertence a você")
    if turno.status != TurnoStatus.ABERTO.value:
        raise HTTPException(status_code=409, detail=f"Turno está {turno.status}")

    # Calcular totais
    itens_result = await db.execute(
        select(AcertoItemEntrega).where(AcertoItemEntrega.turno_id == turno_id)
    )
    itens = itens_result.scalars().all()

    total_cobrado = sum(i.valor_cobrado for i in itens)
    total_esperado = sum(i.valor_pedido for i in itens)

    turno.status = TurnoStatus.AGUARDANDO_APROVACAO.value
    turno.finalizado_em = datetime.now(timezone.utc)
    turno.total_cobrado = total_cobrado
    turno.total_esperado = total_esperado
    turno.diferenca = total_cobrado - total_esperado
    if body.observacao:
        turno.observacao = body.observacao

    await db.commit()
    await db.refresh(turno)

    return {
        "turno_id": str(turno.id),
        "status": turno.status,
        "total_cobrado": float(turno.total_cobrado),
        "total_esperado": float(turno.total_esperado),
        "diferenca": float(turno.diferenca),
        "qtd_itens": len(itens),
    }


@router.get("/meu-turno-ativo")
async def meu_turno_ativo(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna turno aberto do driver, se houver."""
    driver = await _get_driver_for_user(db, current_user)
    result = await db.execute(
        select(DriverTurno).where(
            and_(
                DriverTurno.driver_id == driver.id,
                DriverTurno.status == TurnoStatus.ABERTO.value,
            )
        )
    )
    turno = result.scalar_one_or_none()
    if not turno:
        return {"turno": None}

    itens_result = await db.execute(
        select(AcertoItemEntrega).where(AcertoItemEntrega.turno_id == turno.id)
    )
    itens = itens_result.scalars().all()

    return {
        "turno": {
            "id": str(turno.id),
            "status": turno.status,
            "iniciado_em": turno.iniciado_em,
            "qtd_itens": len(itens),
            "total_cobrado_parcial": float(sum(i.valor_cobrado for i in itens)),
        }
    }


# ── Endpoints operador/owner ───────────────────────────────

@router.get("/pendentes")
async def listar_turnos_pendentes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista turnos aguardando aprovação (operador/owner/admin)."""
    if current_user.role not in ("admin", "owner", "operator"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    result = await db.execute(
        select(DriverTurno)
        .where(DriverTurno.status == TurnoStatus.AGUARDANDO_APROVACAO.value)
        .order_by(DriverTurno.finalizado_em)
    )
    turnos = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "driver_id": str(t.driver_id),
            "status": t.status,
            "iniciado_em": t.iniciado_em,
            "finalizado_em": t.finalizado_em,
            "total_cobrado": float(t.total_cobrado) if t.total_cobrado else None,
            "total_esperado": float(t.total_esperado) if t.total_esperado else None,
            "diferenca": float(t.diferenca) if t.diferenca else None,
            "observacao": t.observacao,
        }
        for t in turnos
    ]


@router.get("/{turno_id}")
async def detalhe_turno(
    turno_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalhe de um turno com todos os itens."""
    turno = await _get_turno_or_404(db, turno_id)

    # Driver só vê o próprio turno
    if current_user.role == "driver":
        driver = await _get_driver_for_user(db, current_user)
        if str(turno.driver_id) != str(driver.id):
            raise HTTPException(status_code=403, detail="Acesso negado")

    itens_result = await db.execute(
        select(AcertoItemEntrega).where(AcertoItemEntrega.turno_id == turno_id)
    )
    itens = itens_result.scalars().all()

    return {
        "id": str(turno.id),
        "driver_id": str(turno.driver_id),
        "status": turno.status,
        "iniciado_em": turno.iniciado_em,
        "finalizado_em": turno.finalizado_em,
        "total_cobrado": float(turno.total_cobrado) if turno.total_cobrado else None,
        "total_esperado": float(turno.total_esperado) if turno.total_esperado else None,
        "diferenca": float(turno.diferenca) if turno.diferenca else None,
        "observacao": turno.observacao,
        "itens": [
            {
                "id": str(i.id),
                "order_id": str(i.order_id) if i.order_id else None,
                "delivery_id": str(i.delivery_id) if i.delivery_id else None,
                "valor_pedido": float(i.valor_pedido),
                "valor_cobrado": float(i.valor_cobrado),
                "payment_method": i.payment_method,
                "entregue": i.entregue,
                "observacao": i.observacao,
            }
            for i in itens
        ],
    }


@router.post("/{turno_id}/aprovar")
async def aprovar_turno(
    turno_id: UUID,
    body: AprovarTurnoBody = AprovarTurnoBody(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aprova turno — libera o acerto financeiro."""
    if current_user.role not in ("admin", "owner", "operator"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    turno = await _get_turno_or_404(db, turno_id)
    if turno.status != TurnoStatus.AGUARDANDO_APROVACAO.value:
        raise HTTPException(status_code=409, detail=f"Turno está {turno.status}")

    turno.status = TurnoStatus.APROVADO.value
    turno.aprovado_em = datetime.now(timezone.utc)
    turno.aprovado_por = current_user.id
    if body.observacao:
        turno.observacao = (turno.observacao or "") + f"\n[Aprovação] {body.observacao}"

    await db.commit()
    await db.refresh(turno)

    logger.info(f"Turno {turno_id} aprovado por {current_user.username}")
    return {"status": turno.status, "aprovado_em": turno.aprovado_em}


@router.post("/{turno_id}/rejeitar")
async def rejeitar_turno(
    turno_id: UUID,
    body: AprovarTurnoBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rejeita turno — driver deve corrigir e reenviar."""
    if current_user.role not in ("admin", "owner", "operator"):
        raise HTTPException(status_code=403, detail="Acesso negado")

    turno = await _get_turno_or_404(db, turno_id)
    if turno.status != TurnoStatus.AGUARDANDO_APROVACAO.value:
        raise HTTPException(status_code=409, detail=f"Turno está {turno.status}")

    turno.status = TurnoStatus.REJEITADO.value
    if body.observacao:
        turno.observacao = (turno.observacao or "") + f"\n[Rejeição] {body.observacao}"

    await db.commit()
    await db.refresh(turno)

    logger.info(f"Turno {turno_id} rejeitado por {current_user.username}: {body.observacao}")
    return {"status": turno.status}
