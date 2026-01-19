"""
API de Chatbot - Processamento de mensagens com IA multi-tier
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.enhanced_chatbot_service import EnhancedClaudeChatbotService
from app.auth import get_current_user
from app.models.auth_models import User

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


@router.post("/test", response_model=ChatResponse)
async def test_chat_message(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db)
):
    """Test endpoint for chat processing without authentication"""
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
