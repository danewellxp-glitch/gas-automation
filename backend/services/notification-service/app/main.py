"""
Notification Service - API Principal.

Serviço de notificações via SMS, Email e Push.
Consome eventos do Redis Streams.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.notify import router as notify_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida do serviço."""
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")

    # Iniciar worker de consumo de eventos em background
    from app.workers.event_consumer import start_consumer
    consumer_task = asyncio.create_task(start_consumer())

    yield

    # Cancelar consumer
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

    logger.info("Notification Service stopped")


app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    description="""
    Serviço de Notificações para o sistema Gas Automation.

    ## Funcionalidades

    - **SMS**: Envio via Twilio
    - **Email**: Envio via SendGrid
    - **Push**: Notificações push (Firebase)
    - **Eventos**: Consumo de eventos via Redis Streams
    """,
    lifespan=lifespan,
)

# CORS
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
        "integrations": {
            "twilio": settings.twilio_enabled,
            "sendgrid": settings.sendgrid_enabled,
        }
    }


@app.get("/")
async def root():
    """Informações do serviço."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
    }


# Incluir rotas
app.include_router(notify_router, prefix="/api/notifications", tags=["Notifications"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
