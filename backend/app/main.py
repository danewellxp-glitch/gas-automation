"""
Aplicação principal FastAPI para automação de pedidos de gás via WhatsApp.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import redis_manager, AsyncSessionLocal

# Importar rotas
from app.api import webhooks, orders, products, customers, test_flow, websocket, chats, auth, chatbot, images


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Executa na inicialização e finalização.
    """
    # Startup
    print(f"🚀 Iniciando {settings.app_name} v{settings.app_version}")
    print(f"📍 Ambiente: {settings.environment}")

    # Conectar Redis
    await redis_manager.connect()
    print("✅ Redis conectado")

    # TODO: Pré-carregar modelo Ollama se necessário
    # TODO: Verificar conexão com Firebird se habilitado

    yield

    # Shutdown
    print("🔄 Encerrando aplicação...")
    await redis_manager.disconnect()
    print("✅ Conexões encerradas")


# Criar aplicação FastAPI
# Docs são habilitados em qualquer ambiente que não seja produção
_enable_docs = not settings.is_production

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    API de automação de pedidos de gás via WhatsApp.

    ## Funcionalidades

    - **Webhooks**: Recebe mensagens do WhatsApp (WAHA) e notificações de pagamento (Asaas)
    - **Pedidos**: CRUD completo de pedidos
    - **Clientes**: Gerenciamento de clientes
    - **Produtos**: Catálogo de produtos (P13, P20, P45)
    - **Pagamentos**: Integração com Asaas (Pix, Cartão, Boleto)
    - **Analytics**: Métricas e relatórios
    - **WebSocket**: Atualizações em tempo real
    """,
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    lifespan=lifespan,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware de métricas Prometheus
from app.metrics import MetricsMiddleware, metrics_endpoint
app.add_middleware(MetricsMiddleware)


# ==================== Rotas Base ====================

@app.get("/", tags=["Health"])
async def root():
    """Rota raiz - informações básicas da API."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Verifica saúde da aplicação e dependências.
    Usado para monitoramento e load balancers.
    """
    from sqlalchemy import text

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {}
    }

    # Verificar Redis
    try:
        await redis_manager.client.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Verificar PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health_status["services"]["postgres"] = "healthy"
    except Exception as e:
        health_status["services"]["postgres"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


@app.get("/api/info", tags=["Health"])
async def api_info():
    """Retorna informações detalhadas da API."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "features": {
            "whatsapp": True,
            "payments": bool(settings.asaas_api_key),
            "ai": True,
            "firebird": settings.firebird_enabled,
        },
        "supported_bairros": settings.supported_bairros,
    }


# ==================== Handlers de Erro ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global de exceções não tratadas."""
    # Em produção, não expor detalhes do erro
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor"}
        )

    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
        }
    )


# ==================== Incluir Rotas ====================

app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(customers.router, prefix="/api/customers", tags=["Customers"])
app.include_router(test_flow.router, prefix="/api/test", tags=["Test Flow"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(chats.router, prefix="/api/chats", tags=["Chats"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["Chatbot"])


# ==================== Métricas Prometheus ====================

@app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
async def prometheus_metrics():
    """Endpoint de métricas para Prometheus."""
    return await metrics_endpoint()


# ==================== Execução Local ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
