"""
Endpoints de teste para o Flow Engine.
Permite testar o fluxo de conversa sem precisar do WhatsApp.
"""

import logging
from typing import Optional, List, Dict, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.flow_engine import flow_engine
from app.database import redis_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class SimulateMessageRequest(BaseModel):
    """Request para simular uma mensagem."""
    phone: str
    message: str
    message_id: Optional[str] = None


class SimulateMessageResponse(BaseModel):
    """Resposta da simulação."""
    success: bool
    current_state: str
    new_state: str
    responses: List[dict]
    context: dict
    error: Optional[str] = None


@router.post("/simulate-message", response_model=SimulateMessageResponse)
async def simulate_message(request: SimulateMessageRequest):
    """
    Simula o envio de uma mensagem de WhatsApp.

    Útil para testar o fluxo sem precisar do WhatsApp real.
    As respostas que seriam enviadas são retornadas no campo 'responses'.
    """
    try:
        # Carregar contexto atual
        context_before = await flow_engine.get_context(request.phone)
        current_state = context_before.state.value

        # Processar mensagem
        result = await flow_engine.process_message(
            phone=request.phone,
            message=request.message,
            message_id=request.message_id,
        )

        # Formatar respostas
        responses = []
        for resp in result.responses:
            responses.append({
                "text": resp.text,
                "buttons": resp.buttons,
                "image_url": resp.image_url,
                "footer": resp.footer,
            })

        return SimulateMessageResponse(
            success=result.success,
            current_state=current_state,
            new_state=result.new_state.value,
            responses=responses,
            context=result.context.to_dict(),
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Erro ao simular mensagem: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/{phone}")
async def get_context(phone: str):
    """
    Retorna o contexto atual de uma conversa.
    """
    try:
        context = await flow_engine.get_context(phone)
        return {
            "phone": phone,
            "context": context.to_dict(),
        }
    except Exception as e:
        logger.error(f"Erro ao buscar contexto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/context/{phone}")
async def reset_context(phone: str):
    """
    Reseta o contexto de uma conversa (útil para testes).
    """
    try:
        await redis_manager.delete_conversation_state(phone)
        return {
            "phone": phone,
            "message": "Contexto resetado com sucesso",
        }
    except Exception as e:
        logger.error(f"Erro ao resetar contexto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flow-states")
async def list_flow_states():
    """
    Lista todos os estados disponíveis no fluxo.
    """
    from app.core.state_machine import ConversationState, StateTransition

    states = {}
    for state in ConversationState:
        transitions = StateTransition.get_valid_transitions(state)
        states[state.value] = {
            "name": state.name,
            "valid_transitions": [t.value for t in transitions],
        }

    return {"states": states}
