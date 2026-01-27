"""
API de Sincronização.
Endpoints para controle manual e monitoramento.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.config import settings
from app.sync.firebird_client import firebird_client
from app.sync.scheduler import (
    run_full_sync,
    sync_products,
    sync_customers,
    sync_stock,
    SyncResult,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schemas ====================

class SyncEntity(str, Enum):
    """Entidades disponíveis para sincronização."""
    PRODUCTS = "products"
    CUSTOMERS = "customers"
    STOCK = "stock"
    ALL = "all"


class SyncRequest(BaseModel):
    """Request para iniciar sincronização."""
    entity: SyncEntity = Field(SyncEntity.ALL, description="Entidade a sincronizar")
    force: bool = Field(False, description="Forçar sincronização mesmo se recente")


class SyncStatusResponse(BaseModel):
    """Status da sincronização."""
    firebird_available: bool
    firebird_connected: bool
    sync_enabled: bool
    last_sync: Optional[str] = None
    next_sync: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    """Resultado do teste de conexão."""
    firebird: dict
    postgres: dict


# ==================== Endpoints ====================

@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """
    Retorna status atual da sincronização.
    """
    firebird_connected = False
    if firebird_client.is_available:
        firebird_connected = firebird_client.test_connection()

    return SyncStatusResponse(
        firebird_available=firebird_client.is_available,
        firebird_connected=firebird_connected,
        sync_enabled=settings.sync_enabled,
        last_sync=None,  # TODO: Buscar do Redis
        next_sync=None,  # TODO: Calcular próxima execução
    )


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_connections():
    """
    Testa conexões com Firebird e PostgreSQL.
    """
    # Testar Firebird
    firebird_result = {
        "available": firebird_client.is_available,
        "connected": False,
        "error": None,
    }

    if firebird_client.is_available:
        try:
            firebird_result["connected"] = firebird_client.test_connection()
        except Exception as e:
            firebird_result["error"] = str(e)

    # Testar PostgreSQL
    postgres_result = {
        "available": True,
        "connected": False,
        "error": None,
    }

    try:
        from app.sync.scheduler import get_postgres_engine
        from sqlalchemy import text

        engine, session_factory = get_postgres_engine()
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
            postgres_result["connected"] = True
    except Exception as e:
        postgres_result["error"] = str(e)

    return ConnectionTestResponse(
        firebird=firebird_result,
        postgres=postgres_result,
    )


@router.post("/run")
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
):
    """
    Inicia sincronização manual.

    A sincronização roda em background e pode ser monitorada via /status.
    """
    if not firebird_client.is_available:
        raise HTTPException(
            status_code=503,
            detail="Firebird não disponível. Configure as variáveis de ambiente."
        )

    # Executar em background
    if request.entity == SyncEntity.ALL:
        background_tasks.add_task(run_full_sync)
        return {
            "status": "started",
            "entity": "all",
            "message": "Sincronização completa iniciada em background",
        }
    elif request.entity == SyncEntity.PRODUCTS:
        background_tasks.add_task(sync_products)
    elif request.entity == SyncEntity.CUSTOMERS:
        background_tasks.add_task(sync_customers)
    elif request.entity == SyncEntity.STOCK:
        background_tasks.add_task(sync_stock)

    return {
        "status": "started",
        "entity": request.entity.value,
        "message": f"Sincronização de {request.entity.value} iniciada em background",
    }


@router.post("/run/sync")
async def trigger_sync_synchronous(request: SyncRequest):
    """
    Executa sincronização de forma síncrona (aguarda conclusão).

    Use com cuidado - pode demorar dependendo do volume de dados.
    """
    if not firebird_client.is_available:
        raise HTTPException(
            status_code=503,
            detail="Firebird não disponível"
        )

    if request.entity == SyncEntity.ALL:
        result = await run_full_sync()
    elif request.entity == SyncEntity.PRODUCTS:
        result = (await sync_products()).to_dict()
    elif request.entity == SyncEntity.CUSTOMERS:
        result = (await sync_customers()).to_dict()
    elif request.entity == SyncEntity.STOCK:
        result = (await sync_stock()).to_dict()
    else:
        raise HTTPException(status_code=400, detail="Entidade inválida")

    return {
        "status": "completed",
        "entity": request.entity.value,
        "result": result,
    }


@router.get("/products/preview")
async def preview_products(limit: int = 10):
    """
    Visualiza produtos que seriam sincronizados do Firebird.

    Útil para debug e validação antes de sincronizar.
    """
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    products = firebird_client.get_products()

    return {
        "total": len(products),
        "preview": products[:limit],
    }


@router.get("/customers/preview")
async def preview_customers(limit: int = 10):
    """
    Visualiza clientes que seriam sincronizados do Firebird.
    """
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    customers = firebird_client.get_customers()

    return {
        "total": len(customers),
        "preview": customers[:limit],
    }


@router.get("/stock/preview")
async def preview_stock(limit: int = 10):
    """
    Visualiza níveis de estoque do Firebird.
    """
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    stock = firebird_client.get_stock_levels()

    return {
        "total": len(stock),
        "preview": stock[:limit],
    }


@router.post("/export-order/{order_id}")
async def export_order_to_firebird(order_id: str):
    """
    Exporta um pedido específico para o Firebird (faturamento).
    """
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    # TODO: Buscar pedido do PostgreSQL e exportar
    # Por enquanto, retorna placeholder

    return {
        "status": "not_implemented",
        "message": "Exportação de pedidos será implementada na próxima versão",
        "order_id": order_id,
    }
