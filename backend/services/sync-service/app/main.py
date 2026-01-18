"""
Sync Service - API Principal.

Serviço de sincronização bidirecional entre Firebird (ERP legado) e PostgreSQL.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.api.sync_api import router as sync_router
from app.sync.scheduler import run_full_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Scheduler para sincronização automática
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida do serviço."""
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")

    # Iniciar scheduler se sincronização automática habilitada
    if settings.sync_enabled and settings.firebird_enabled:
        scheduler.add_job(
            run_full_sync,
            trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
            id="full_sync",
            name="Sincronização Completa",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(f"Scheduler iniciado - intervalo: {settings.sync_interval_minutes} minutos")
    else:
        logger.warning("Sincronização automática desabilitada ou Firebird não configurado")

    yield

    # Parar scheduler
    if scheduler.running:
        scheduler.shutdown()

    logger.info("Sync Service stopped")


app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    description="""
    Serviço de Sincronização Firebird ↔ PostgreSQL para o sistema Gas Automation.

    ## Funcionalidades

    - **Produtos**: Sincroniza catálogo de produtos do ERP
    - **Clientes**: Sincroniza cadastro de clientes
    - **Pedidos**: Exporta pedidos para o ERP fiscal
    - **Estoque**: Sincroniza níveis de estoque
    - **Agendamento**: Sincronização automática configurável
    """,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check do serviço."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "firebird_enabled": settings.firebird_enabled,
        "sync_enabled": settings.sync_enabled,
        "scheduler_running": scheduler.running if settings.sync_enabled else False,
    }


@app.get("/")
async def root():
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
    }


app.include_router(sync_router, prefix="/api/sync", tags=["Sync"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
