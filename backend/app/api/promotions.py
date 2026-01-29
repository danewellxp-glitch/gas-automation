"""
API de Promoções.

CRUD de promoções e cupons de desconto.
"""
import logging
from datetime import date
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models.auth_models import User
from app.api.websocket import UserRole
from app.models.promotion import Promotion
from app.schemas.promotion import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[PromotionResponse])
async def list_promotions(
    active_only: bool = Query(False, description="Apenas promoções ativas"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista todas as promoções.
    
    Apenas owner e admin podem acessar.
    """
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    query = select(Promotion)
    
    if active_only:
        today = date.today()
        query = query.where(
            and_(
                Promotion.is_active == True,
                Promotion.valid_from <= today,
                or_(
                    Promotion.valid_until.is_(None),
                    Promotion.valid_until >= today,
                ),
            )
        )
    
    query = query.order_by(Promotion.created_at.desc())
    
    result = await db.execute(query)
    promotions = result.scalars().all()
    
    return promotions


@router.get("/{promotion_id}", response_model=PromotionResponse)
async def get_promotion(
    promotion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca uma promoção específica."""
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    result = await db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    )
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promoção não encontrada")
    
    return promotion


@router.get("/code/{code}", response_model=PromotionResponse)
async def get_promotion_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Busca promoção por código.
    Público (para validação de cupons).
    """
    result = await db.execute(
        select(Promotion).where(Promotion.code == code.upper())
    )
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    
    return promotion


@router.post("", response_model=PromotionResponse, status_code=201)
async def create_promotion(
    data: PromotionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cria uma nova promoção.
    
    Apenas owner e admin podem criar.
    """
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Verificar se código já existe
    existing = await db.execute(
        select(Promotion).where(Promotion.code == data.code.upper())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Código de cupom já existe")
    
    # Criar promoção
    promotion = Promotion(
        code=data.code.upper(),
        name=data.name,
        description=data.description,
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        min_order_value=data.min_order_value,
        max_discount=data.max_discount,
        usage_limit=data.usage_limit,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        is_active=data.is_active if data.is_active is not None else True,
        applies_to_all_products=data.applies_to_all_products if data.applies_to_all_products is not None else True,
    )
    
    db.add(promotion)
    await db.commit()
    await db.refresh(promotion)
    
    return promotion


@router.patch("/{promotion_id}", response_model=PromotionResponse)
async def update_promotion(
    promotion_id: UUID,
    data: PromotionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Atualiza uma promoção.
    
    Apenas owner e admin podem atualizar.
    """
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    result = await db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    )
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promoção não encontrada")
    
    # Atualizar campos
    update_data = data.model_dump(exclude_unset=True)
    
    # Se código está sendo atualizado, verificar duplicatas
    if "code" in update_data:
        code = update_data["code"].upper()
        existing = await db.execute(
            select(Promotion).where(
                Promotion.code == code,
                Promotion.id != promotion_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Código de cupom já existe")
        update_data["code"] = code
    
    for field, value in update_data.items():
        setattr(promotion, field, value)
    
    await db.commit()
    await db.refresh(promotion)
    
    return promotion


@router.delete("/{promotion_id}")
async def delete_promotion(
    promotion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deleta uma promoção.
    
    Apenas owner e admin podem deletar.
    """
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    result = await db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    )
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promoção não encontrada")
    
    await db.delete(promotion)
    await db.commit()
    
    return {"message": "Promoção deletada com sucesso"}


@router.post("/{promotion_id}/validate")
async def validate_promotion(
    promotion_id: UUID,
    order_value: Decimal = Query(..., description="Valor total do pedido"),
    db: AsyncSession = Depends(get_db),
):
    """
    Valida uma promoção para um pedido.
    Público (para validação de cupons).
    """
    result = await db.execute(
        select(Promotion).where(Promotion.id == promotion_id)
    )
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promoção não encontrada")
    
    is_valid, error_message = promotion.is_valid(order_value)
    
    if not is_valid:
        return {
            "valid": False,
            "error": error_message,
            "discount": 0,
        }
    
    discount = promotion.calculate_discount(order_value)
    
    return {
        "valid": True,
        "discount": float(discount),
        "discount_type": promotion.discount_type,
        "final_value": float(order_value - discount),
    }