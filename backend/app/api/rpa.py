"""
API para controle do Robô RPA Gasmaster.

Endpoints para verificar status, executar exportações e calibrar posições.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.auth import get_current_user
from app.models.auth_models import User
from app.services.rpa_gasmaster_service import (
    gasmaster_rpa,
    check_rpa_available,
    RPAStatus,
    OrderToExport,
    GasmasterConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schemas ====================

class RPAStatusResponse(BaseModel):
    available: bool
    pyautogui: bool
    pywinauto: bool
    gasmaster_open: bool


class ExportOrderRequest(BaseModel):
    order_id: str
    order_number: int
    customer_firebird_id: int
    customer_name: str
    total_amount: float
    payment_method: Optional[str] = None
    items: list  # [{product_code, quantity, unit_price}]
    notes: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    window_title: Optional[str] = None
    action_delay: Optional[float] = None
    typing_delay: Optional[float] = None
    screen_vendas: Optional[dict] = None


# ==================== Endpoints ====================

@router.get("/status", response_model=RPAStatusResponse)
async def get_rpa_status(
    current_user: User = Depends(get_current_user),
):
    """
    Verifica status do robô RPA.

    Retorna se as bibliotecas estão instaladas e se o Gasmaster está aberto.
    """
    status = check_rpa_available()
    return status


@router.post("/check-gasmaster")
async def check_gasmaster_window(
    current_user: User = Depends(get_current_user),
):
    """
    Verifica se a janela do Gasmaster está aberta.
    """
    if not gasmaster_rpa.is_available:
        raise HTTPException(
            status_code=503,
            detail="Bibliotecas de automação não instaladas. Execute: pip install pyautogui pywinauto"
        )

    is_open = gasmaster_rpa.is_gasmaster_open()

    return {
        "gasmaster_open": is_open,
        "message": "Gasmaster encontrado!" if is_open else "Gasmaster não encontrado. Verifique se está aberto."
    }


@router.post("/focus")
async def focus_gasmaster(
    current_user: User = Depends(get_current_user),
):
    """
    Traz a janela do Gasmaster para frente.
    """
    if not gasmaster_rpa.is_available:
        raise HTTPException(status_code=503, detail="RPA não disponível")

    success = gasmaster_rpa.focus_gasmaster()

    if success:
        return {"success": True, "message": "Gasmaster em foco"}
    else:
        raise HTTPException(status_code=404, detail="Não foi possível focar no Gasmaster")


@router.post("/screenshot")
async def take_screenshot(
    current_user: User = Depends(get_current_user),
):
    """
    Tira screenshot da tela atual (para debug/calibração).
    """
    if not gasmaster_rpa.is_available:
        raise HTTPException(status_code=503, detail="RPA não disponível")

    try:
        filepath = gasmaster_rpa.take_screenshot()
        return {"success": True, "filepath": filepath}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-order")
async def export_single_order(
    request: ExportOrderRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Exporta um pedido via RPA.

    O robô irá:
    1. Encontrar a janela do Gasmaster
    2. Navegar até a tela de vendas
    3. Preencher os dados do pedido
    4. Finalizar a venda
    """
    if not gasmaster_rpa.is_available:
        raise HTTPException(status_code=503, detail="RPA não disponível")

    order = OrderToExport(
        order_id=UUID(request.order_id),
        order_number=request.order_number,
        customer_firebird_id=request.customer_firebird_id,
        customer_name=request.customer_name,
        total_amount=request.total_amount,
        payment_method=request.payment_method,
        items=request.items,
        notes=request.notes,
    )

    status = gasmaster_rpa.export_order(order)

    if status == RPAStatus.SUCCESS:
        return {
            "success": True,
            "status": status.value,
            "message": f"Pedido #{request.order_number} exportado com sucesso!"
        }
    else:
        return {
            "success": False,
            "status": status.value,
            "message": f"Falha ao exportar pedido. Status: {status.value}"
        }


@router.get("/config")
async def get_rpa_config(
    current_user: User = Depends(get_current_user),
):
    """
    Retorna configuração atual do RPA.
    """
    config = gasmaster_rpa.config
    return {
        "window_title": config.window_title,
        "window_timeout": config.window_timeout,
        "action_delay": config.action_delay,
        "typing_delay": config.typing_delay,
        "screen_vendas": config.screen_vendas,
    }


@router.put("/config")
async def update_rpa_config(
    request: ConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Atualiza configuração do RPA (coordenadas dos controles, etc).
    """
    config = gasmaster_rpa.config

    if request.window_title:
        config.window_title = request.window_title

    if request.action_delay is not None:
        config.action_delay = request.action_delay

    if request.typing_delay is not None:
        config.typing_delay = request.typing_delay

    if request.screen_vendas:
        config.screen_vendas.update(request.screen_vendas)

    return {
        "success": True,
        "message": "Configuração atualizada",
        "config": {
            "window_title": config.window_title,
            "action_delay": config.action_delay,
            "typing_delay": config.typing_delay,
            "screen_vendas": config.screen_vendas,
        }
    }


@router.post("/test-click")
async def test_click(
    x: int,
    y: int,
    current_user: User = Depends(get_current_user),
):
    """
    Testa um clique em uma posição específica (para calibração).
    """
    if not gasmaster_rpa.is_available:
        raise HTTPException(status_code=503, detail="RPA não disponível")

    try:
        gasmaster_rpa.click(x, y)
        return {"success": True, "message": f"Clique em ({x}, {y}) executado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-type")
async def test_type(
    text: str,
    current_user: User = Depends(get_current_user),
):
    """
    Testa digitação de texto (para calibração).
    """
    if not gasmaster_rpa.is_available:
        raise HTTPException(status_code=503, detail="RPA não disponível")

    try:
        gasmaster_rpa.type_text(text)
        return {"success": True, "message": f"Texto '{text}' digitado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
