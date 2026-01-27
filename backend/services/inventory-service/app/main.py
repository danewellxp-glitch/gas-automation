"""
Inventory Service - API Principal.

Serviço de gestão de estoque de produtos.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.inventory import router as inventory_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida do serviço."""
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    yield
    logger.info("Inventory Service stopped")


app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    description="""
    Serviço de Gestão de Estoque para o sistema Gas Automation.

    ## Funcionalidades

    - **Produtos**: CRUD de produtos (P13, P20, P45, etc)
    - **Estoque**: Controle de quantidade disponível
    - **Movimentações**: Histórico de entradas e saídas
    - **Alertas**: Notificação de estoque baixo
    - **Reservas**: Reserva de estoque para pedidos
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
    }


@app.get("/")
async def root():
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
    }


app.include_router(inventory_router, prefix="/api/inventory", tags=["Inventory"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
