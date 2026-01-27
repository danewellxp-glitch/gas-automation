"""
API de Chatbot - Processamento de mensagens com IA multi-tier
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.database import get_db
from app.services.enhanced_chatbot_service import EnhancedClaudeChatbotService
from app.auth import get_current_user
from app.models.auth_models import User, BotInteraction

router = APIRouter()


class ChatRequest(BaseModel):
    phone_number: str
    message: str
    profile_name: Optional[str] = "Cliente"


class ChatResponse(BaseModel):
    bot_response: str
    bot_service: str
    should_escalate: bool
    escalation_reason: Optional[str] = None
    response_time_ms: int


@router.post("/chat", response_model=ChatResponse)
async def process_chat_message(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process a chat message through the enhanced chatbot service"""
    try:
        chatbot_service = EnhancedClaudeChatbotService(session)
        result = await chatbot_service.process_message(
            phone_number=request.phone_number,
            message=request.message,
            profile_name=request.profile_name
        )

        return ChatResponse(
            bot_response=result['bot_response'],
            bot_service=result['bot_service'],
            should_escalate=result['should_escalate'],
            escalation_reason=result.get('escalation_reason'),
            response_time_ms=result['response_time_ms']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")


# REMOVIDO: Endpoint /test - Não usar em produção
# Chat deve ser processado apenas através do webhook do WhatsApp
# Para testes, usar ambiente de desenvolvimento com autenticação adequada


@router.delete("/context/{phone_number}")
async def clear_chat_context(
    phone_number: str,
    session: AsyncSession = Depends(get_db)
):
    """Clear conversation context for a phone number"""
    try:
        chatbot_service = EnhancedClaudeChatbotService(session)
        chatbot_service.clear_context(phone_number)
        return {"message": f"Context cleared for {phone_number}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing context: {str(e)}")


@router.post("/cleanup-contexts")
async def cleanup_expired_contexts(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clean up expired conversation contexts"""
    try:
        chatbot_service = EnhancedClaudeChatbotService(session)
        count = chatbot_service.cleanup_expired_contexts()
        return {"message": f"Cleaned up {count} expired contexts"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up contexts: {str(e)}")


@router.get("/status")
async def chatbot_status():
    """Get chatbot service status"""
    import os

    claude_available = bool(os.getenv("ANTHROPIC_API_KEY"))

    try:
        import anthropic
        anthropic_installed = True
    except ImportError:
        anthropic_installed = False

    return {
        "status": "ok",
        "services": {
            "claude": {
                "available": claude_available and anthropic_installed,
                "api_key_configured": claude_available,
                "package_installed": anthropic_installed
            },
            "ollama": {
                "available": True,
                "url": os.getenv("OLLAMA_URL", "http://ollama:11434")
            },
            "fallback": {
                "available": True,
                "type": "rule-based"
            }
        }
    }


class ChatbotAnalyticsResponse(BaseModel):
    total_interactions: int
    escalated_interactions: int
    success_rate: float
    bot_type_distribution: Dict[str, int]
    escalation_reasons: Dict[str, int]
    interactions_last_24h: int
    average_response_time_ms: Optional[float]
    analytics_period: str


@router.get("/analytics", response_model=ChatbotAnalyticsResponse)
async def get_chatbot_analytics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retorna analytics de performance do chatbot.

    Metricas incluem:
    - Total de interacoes
    - Taxa de escalation
    - Distribuicao por tipo de bot (Claude/Ollama/Fallback)
    - Razoes de escalation
    - Interacoes nas ultimas 24h
    - Tempo medio de resposta
    """
    if current_user.role not in ["admin", "owner", "operator"]:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado"
        )

    try:
        # Total de interacoes
        total_result = await session.execute(
            select(func.count(BotInteraction.id))
        )
        total_interactions = total_result.scalar() or 0

        # Interacoes escaladas
        escalated_result = await session.execute(
            select(func.count(BotInteraction.id))
            .where(BotInteraction.escalated == True)
        )
        escalated_interactions = escalated_result.scalar() or 0

        # Distribuicao por tipo de bot
        bot_type_result = await session.execute(
            select(BotInteraction.bot_type, func.count(BotInteraction.id))
            .group_by(BotInteraction.bot_type)
        )
        bot_type_distribution = {}
        for row in bot_type_result:
            bot_type_distribution[row[0] or "unknown"] = row[1]

        # Razoes de escalation
        escalation_reasons_result = await session.execute(
            select(BotInteraction.escalation_reason, func.count(BotInteraction.id))
            .where(BotInteraction.escalated == True)
            .where(BotInteraction.escalation_reason != None)
            .group_by(BotInteraction.escalation_reason)
        )
        escalation_reasons = {}
        for row in escalation_reasons_result:
            escalation_reasons[row[0] or "unknown"] = row[1]

        # Interacoes ultimas 24h
        yesterday = datetime.now() - timedelta(days=1)
        recent_result = await session.execute(
            select(func.count(BotInteraction.id))
            .where(BotInteraction.timestamp >= yesterday)
        )
        interactions_last_24h = recent_result.scalar() or 0

        # Tempo medio de resposta
        avg_time_result = await session.execute(
            select(func.avg(BotInteraction.response_time_ms))
            .where(BotInteraction.response_time_ms != None)
        )
        average_response_time_ms = avg_time_result.scalar()

        # Calcular taxa de sucesso
        success_rate = 0.0
        if total_interactions > 0:
            success_rate = round(
                ((total_interactions - escalated_interactions) / total_interactions) * 100,
                2
            )

        return ChatbotAnalyticsResponse(
            total_interactions=total_interactions,
            escalated_interactions=escalated_interactions,
            success_rate=success_rate,
            bot_type_distribution=bot_type_distribution,
            escalation_reasons=escalation_reasons,
            interactions_last_24h=interactions_last_24h,
            average_response_time_ms=round(average_response_time_ms, 2) if average_response_time_ms else None,
            analytics_period="all_time"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar analytics: {str(e)}"
        )
