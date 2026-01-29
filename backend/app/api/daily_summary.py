"""
API para Daily Business Summary.

Permite gerar e enviar resumos diários de negócios.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models.auth_models import User
from app.api.websocket import UserRole
from app.services.daily_summary_service import daily_summary_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate")
async def generate_daily_summary(
    date: Optional[str] = Query(None, description="Data no formato YYYY-MM-DD (default: hoje)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gera resumo diário de negócios.
    
    Apenas owner e admin podem acessar.
    """
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Parse date
    summary_date = None
    if date:
        try:
            summary_date = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")
    
    summary = await daily_summary_service.generate_summary(db, summary_date)
    return summary


@router.post("/send")
async def send_daily_summary(
    owner_phone: Optional[str] = Query(None, description="Telefone do owner (para WhatsApp)"),
    owner_email: Optional[str] = Query(None, description="Email do owner"),
    date: Optional[str] = Query(None, description="Data no formato YYYY-MM-DD (default: hoje)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gera e envia resumo diário via WhatsApp/Email.
    
    Apenas owner e admin podem acessar.
    """
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Parse date
    summary_date = None
    if date:
        try:
            summary_date = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")
    
    # Se não fornecido, usar dados do usuário atual (se owner)
    if not owner_phone and not owner_email:
        if current_user.role == UserRole.OWNER:
            # Tentar obter do perfil do usuário (se existir campo phone/email)
            # Por enquanto, requerer explicitamente
            raise HTTPException(
                status_code=400,
                detail="Forneça owner_phone ou owner_email"
            )
    
    success = await daily_summary_service.send_summary(
        db,
        owner_phone=owner_phone,
        owner_email=owner_email,
        date=summary_date,
    )
    
    if success:
        return {"message": "Resumo diário enviado com sucesso"}
    else:
        raise HTTPException(status_code=500, detail="Erro ao enviar resumo diário")