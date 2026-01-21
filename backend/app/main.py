"""
Aplicação principal FastAPI para automação de pedidos de gás via WhatsApp.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import redis_manager, AsyncSessionLocal, get_db
from app.models.auth_models import User
from app.auth import get_current_user
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import app.metrics as metrics

# Importar rotas
from app.api import webhooks, orders, products, customers, websocket, chats, auth, chatbot, images, users, drivers

# Importar serviços para delivery system
try:
    from app.services.customer_service import CustomerService
    from app.services.order_service import OrderService
    from app.services.delivery_service import DeliveryService
    from app.services.driver_service import DriverService
    from app.services.product_service import ProductService
    print("Serviços importados com sucesso!")
except ImportError as e:
    print(f"Erro ao importar serviços: {e}")
    # Fallback: definir classes vazias para evitar crashes
    class CustomerService:
        def __init__(self, session): pass
        def list_all(self): return []
    class OrderService:
        def __init__(self, session): pass
        def list_pending(self): return []
    class DeliveryService:
        def __init__(self, session): pass
        def list_active(self): return []
    class DriverService:
        def __init__(self, session): pass
        def list_all(self): return []
    class ProductService:
        def __init__(self, session): pass
        def list_all(self): return []


async def _metrics_updater(ws_manager, redis_bridge):
    """
    Task assíncrona que atualiza métricas periodicamente.
    Roda em background durante toda a vida da aplicação.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("📊 Iniciando atualizador de métricas")
    
    # Obter instance_id do redis_bridge
    instance_id = getattr(redis_bridge, 'instance_id', 'unknown')
    start_time = datetime.now(timezone.utc)
    
    try:
        while True:
            try:
                # Atualizar uptime
                uptime = (datetime.now(timezone.utc) - start_time).total_seconds()
                metrics.system_uptime_seconds.labels(instance_id=instance_id).set(uptime)
                
                # Atualizar métricas do WebSocket
                metrics.update_websocket_metrics(ws_manager, instance_id)
                
                # Atualizar métricas do Event Batcher
                metrics.update_event_batcher_metrics(ws_manager.event_batcher, instance_id)
                
                # Atualizar métricas do Redis Bridge
                metrics.update_redis_bridge_metrics(redis_bridge, instance_id)
                
                logger.debug(f"📊 Métricas atualizadas (uptime={uptime:.0f}s)")
            
            except Exception as e:
                logger.error(f"❌ Erro ao atualizar métricas: {e}")
            
            # Atualizar a cada 30 segundos
            await asyncio.sleep(30)
    
    except asyncio.CancelledError:
        logger.info("📊 Atualizador de métricas cancelado")
    except Exception as e:
        logger.error(f"❌ Erro fatal no atualizador de métricas: {e}")


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
    
    # Iniciar monitor de heartbeat WebSocket
    from app.api.websocket import manager as ws_manager
    heartbeat_task = asyncio.create_task(ws_manager.heartbeat_monitor())
    print("✅ Monitor de heartbeat WebSocket iniciado")
    
    # Iniciar Redis WebSocket Bridge para escala horizontal (FASE 3)
    from app.core.redis_websocket_bridge import redis_ws_bridge
    await redis_ws_bridge.start()
    print("✅ Redis WebSocket Bridge iniciado (escala horizontal)")
    
    # Iniciar Event Batcher para agrupar eventos (FASE 3)
    await ws_manager.enable_batching()
    print("✅ Event Batcher iniciado (agrupamento de eventos)")
    
    # Inicializar métricas Prometheus (FASE 3)
    metrics.init_system_info(version=settings.app_version, environment=settings.environment)
    print("✅ Métricas Prometheus inicializadas")
    
    # Iniciar task de atualização periódica de métricas
    from app.core.redis_websocket_bridge import redis_ws_bridge
    metrics_task = asyncio.create_task(_metrics_updater(ws_manager, redis_ws_bridge))
    print("✅ Monitor de métricas iniciado")

    # TODO: Pré-carregar modelo Ollama se necessário
    # TODO: Verificar conexão com Firebird se habilitado

    yield

    # Shutdown
    print("🔄 Encerrando aplicação...")
    
    # Cancelar task de heartbeat
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    
    # Cancelar task de métricas
    metrics_task.cancel()
    try:
        await metrics_task
    except asyncio.CancelledError:
        pass
    
    # Parar Event Batcher
    await ws_manager.disable_batching()
    
    # Parar Redis WebSocket Bridge
    await redis_ws_bridge.stop()
    
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

# Configurar Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

# Métricas Prometheus estão disponíveis no endpoint /metrics


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


# ==================== Endpoints Principais ====================

@app.get("/metrics", tags=["Monitoring"], response_class=PlainTextResponse)
def metrics_endpoint():
    """
    Endpoint de métricas Prometheus (FASE 3).
    
    Expõe métricas customizadas para coleta pelo Prometheus:
    - Conexões WebSocket ativas por role e instância
    - Mensagens enviadas/recebidas
    - Latência de broadcasts
    - Redis Pub/Sub (mensagens publicadas/recebidas)
    - Event batching (buffer, batch size)
    - Message Store (replay requests, mensagens armazenadas)
    - Erros e desconexões
    - Uptime do sistema
    
    Formato: Prometheus text-based exposition format
    """
    return PlainTextResponse(
        content=generate_latest().decode('utf-8'),
        media_type=CONTENT_TYPE_LATEST
    )


# ==================== Incluir Rotas ====================

app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(customers.router, prefix="/api/customers", tags=["Customers"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(chats.router, prefix="/api", tags=["Chats"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["Chatbot"])
app.include_router(drivers.router, prefix="/api/drivers", tags=["Drivers"])


# ==================== DASHBOARD STATISTICS ENDPOINTS ====================

@app.get("/api/stats")
async def get_owner_stats(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Estatísticas para dashboard do owner"""
    try:
        # Usuários
        from app.models.auth_models import User
        total_users = len(await session.execute(select(User)))
        active_users = len(await session.execute(select(User).where(User.is_active == True)))

        # Conversas (aproximado)
        from app.models.auth_models import Conversation
        total_conversations = len(await session.execute(select(Conversation)))

        # Pedidos (se existir tabela orders)
        try:
            from app.models.order import Order
            total_orders = len(await session.execute(select(Order)))
            # Pedidos hoje
            from datetime import datetime, timedelta
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_orders = len(await session.execute(
                select(Order).where(Order.created_at >= today)
            ))
        except:
            total_orders = 0
            today_orders = 0

        # Receita aproximada (R$ 100 por pedido)
        revenue = total_orders * 100

        # Operadores ativos (aproximado)
        active_operators = len(await session.execute(
            select(User).where(User.role.in_(["admin", "operator", "owner"]))
        ))

        return {
            "totalConversations": total_conversations,
            "totalOrders": total_orders,
            "revenue": revenue,
            "activeOperators": active_operators,
            "totalUsers": total_users,
            "activeUsers": active_users,
            "todayOrders": today_orders
        }

    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return {
            "totalConversations": 0,
            "totalOrders": 0,
            "revenue": 0,
            "activeOperators": 0,
            "totalUsers": 0,
            "activeUsers": 0,
            "todayOrders": 0
        }

@app.get("/api/admin/stats")
async def get_admin_stats(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Estatísticas para dashboard do admin"""
    try:
        from app.models.auth_models import User, Conversation, AuditLog

        # Usuários
        total_users = len(await session.execute(select(User)))
        active_users = len(await session.execute(select(User).where(User.is_active == True)))

        # Conversas
        total_conversations = len(await session.execute(select(Conversation)))
        pending_conversations = len(await session.execute(
            select(Conversation).where(Conversation.status == "pending")
        ))

        # Mensagens (aproximado)
        total_messages = total_conversations * 5  # estimativa

        # Mensagens hoje (aproximado)
        from datetime import datetime
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        messages_today = total_messages // 30  # estimativa

        # Logs de auditoria
        audit_logs = len(await session.execute(select(AuditLog)))

        return {
            "users": {
                "total": total_users,
                "active": active_users
            },
            "conversations": {
                "total": total_conversations,
                "pending": pending_conversations
            },
            "messages": {
                "total": total_messages,
                "today": messages_today
            },
            "audit_logs": audit_logs
        }

    except Exception as e:
        print(f"Erro ao buscar estatísticas admin: {e}")
        return {
            "users": {"total": 0, "active": 0},
            "conversations": {"total": 0, "pending": 0},
            "messages": {"total": 0, "today": 0},
            "audit_logs": 0
        }

# ==================== REPORTS & FINANCIAL ENDPOINTS ====================

@app.get("/api/reports/financial")
async def get_financial_report(
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Relatório financeiro detalhado"""
    try:
        # Simulação de dados financeiros
        from datetime import datetime, timedelta
        import random

        # Se não especificar datas, usar último mês
        if not end_date:
            end_date = datetime.now()
        else:
            end_date = datetime.fromisoformat(end_date)

        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromisoformat(start_date)

        # Dados simulados
        days_diff = (end_date - start_date).days
        daily_revenue = {}
        total_revenue = 0

        for i in range(days_diff + 1):
            day = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            day_revenue = random.randint(500, 2000)
            daily_revenue[day] = day_revenue
            total_revenue += day_revenue

        # Gastos simulados (70% da receita)
        total_expenses = total_revenue * 0.7
        net_profit = total_revenue - total_expenses

        # Pedidos simulados
        total_orders = len(daily_revenue) * random.randint(8, 15)

        return {
            "period": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d')
            },
            "summary": {
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "net_profit": net_profit,
                "total_orders": total_orders,
                "average_ticket": total_revenue / total_orders if total_orders > 0 else 0,
                "profit_margin": (net_profit / total_revenue * 100) if total_revenue > 0 else 0
            },
            "daily_revenue": daily_revenue,
            "charts": {
                "revenue_trend": list(daily_revenue.values()),
                "dates": list(daily_revenue.keys())
            }
        }

    except Exception as e:
        print(f"Erro no relatório financeiro: {e}")
        return {
            "period": {"start_date": "", "end_date": ""},
            "summary": {"total_revenue": 0, "total_expenses": 0, "net_profit": 0},
            "daily_revenue": {},
            "charts": {"revenue_trend": [], "dates": []}
        }

@app.get("/api/reports/orders")
async def get_orders_report(
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Relatório de pedidos"""
    try:
        # Simulação de dados de pedidos
        import random
        from datetime import datetime, timedelta

        if not end_date:
            end_date = datetime.now()
        else:
            end_date = datetime.fromisoformat(end_date)

        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromisoformat(start_date)

        # Dados simulados
        status_counts = {
            "completed": random.randint(50, 100),
            "pending": random.randint(10, 30),
            "cancelled": random.randint(5, 15)
        }

        total_orders = sum(status_counts.values())

        return {
            "period": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d')
            },
            "summary": {
                "total_orders": total_orders,
                "completed_rate": (status_counts["completed"] / total_orders * 100) if total_orders > 0 else 0,
                "by_status": status_counts
            },
            "orders": [
                {
                    "id": i+1,
                    "status": random.choice(["completed", "pending", "cancelled"]),
                    "total": random.randint(50, 200),
                    "created_at": (start_date + timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d'),
                    "customer": f"Cliente {i+1}"
                }
                for i in range(min(10, total_orders))  # Máximo 10 pedidos na listagem
            ]
        }

    except Exception as e:
        print(f"Erro no relatório de pedidos: {e}")
        return {
            "period": {"start_date": "", "end_date": ""},
            "summary": {"total_orders": 0, "completed_rate": 0, "by_status": {}},
            "orders": []
        }

@app.get("/api/reports/export/orders")
async def export_orders_csv(
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(get_current_user)
):
    """Exportar pedidos em CSV"""
    from fastapi.responses import Response

    # Simulação de dados CSV
    csv_content = """ID,Status,Total,Data,Customer
1,completed,150.00,2024-01-15,Cliente 1
2,pending,89.90,2024-01-16,Cliente 2
3,completed,200.00,2024-01-17,Cliente 3
4,cancelled,75.50,2024-01-18,Cliente 4
5,completed,120.00,2024-01-19,Cliente 5
"""

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pedidos.csv"}
    )

@app.get("/api/reports/export/financial")
async def export_financial_csv(
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(get_current_user)
):
    """Exportar relatório financeiro em CSV"""
    from fastapi.responses import Response

    csv_content = """Data,Receita,Despesas,Lucro
2024-01-15,1200.00,840.00,360.00
2024-01-16,950.00,665.00,285.00
2024-01-17,1450.00,1015.00,435.00
2024-01-18,1100.00,770.00,330.00
2024-01-19,1350.00,945.00,405.00
"""

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=relatorio_financeiro.csv"}
    )

# ==================== DELIVERY SYSTEM ENDPOINTS ====================

# --- Customers ---
@app.get("/api/customers")
async def list_customers(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Lista todos os clientes"""
    service = CustomerService(session)
    return service.list_all()

@app.get("/api/customers/{customer_id}")
async def get_customer(customer_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Busca cliente por ID"""
    service = CustomerService(session)
    customer = service.get_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return customer

@app.get("/api/customers/phone/{telefone}")
async def get_customer_by_phone(telefone: str, session: AsyncSession = Depends(get_db)):
    """Busca cliente por telefone"""
    service = CustomerService(session)
    customer = service.get_by_phone(telefone)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return customer

# --- Drivers ---
@app.get("/api/drivers")
async def list_drivers(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Lista todos os entregadores"""
    service = DriverService(session)
    return await service.list_all()

@app.get("/api/drivers/available")
async def list_available_drivers(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Lista entregadores disponíveis"""
    service = DriverService(session)
    return await service.list_available()

# --- Orders ---
@app.get("/api/orders/pending")
async def list_pending_orders(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Lista pedidos pendentes"""
    service = OrderService(session)
    return service.list_pending()

@app.get("/api/orders/in-delivery")
async def list_orders_in_delivery(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Lista pedidos em entrega"""
    service = OrderService(session)
    return service.list_in_delivery()

@app.get("/api/orders/{order_id}")
async def get_order(order_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Busca pedido por ID"""
    service = OrderService(session)
    order = service.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return order

@app.post("/api/orders/{order_id}/confirm")
async def confirm_order(order_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Confirma pedido"""
    service = OrderService(session)
    order = service.confirm(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Broadcast atualização
    await manager.broadcast({
        "type": "order_update",
        "order_id": order_id,
        "status": "confirmado",
        "action": "confirm"
    })

    return order

# --- Deliveries ---
@app.get("/api/deliveries/active")
async def list_active_deliveries(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Lista entregas ativas"""
    service = DeliveryService(session)
    return service.list_active()

@app.post("/api/orders/{order_id}/assign-driver")
async def assign_driver_to_order(order_id: int, data: dict, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Atribui entregador ao pedido"""
    driver_id = data.get("driver_id")
    if not driver_id:
        raise HTTPException(status_code=400, detail="driver_id é obrigatório")

    delivery_service = DeliveryService(session)
    delivery = delivery_service.create_delivery(order_id, driver_id)
    if not delivery:
        raise HTTPException(status_code=400, detail="Erro ao criar entrega")

    # Broadcast
    await manager.broadcast({
        "type": "order_update",
        "order_id": order_id,
        "status": "em_preparo",
        "action": "assign_driver",
        "driver_id": driver_id,
        "driver_name": delivery.driver.name if delivery.driver else None
    })

    return delivery

@app.post("/api/deliveries/{delivery_id}/start")
async def start_delivery(delivery_id: int, session: AsyncSession = Depends(get_db)):
    """Inicia entrega (saiu para entrega)"""
    service = DeliveryService(session)
    delivery = service.start_delivery(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    # Broadcast
    await manager.broadcast({
        "type": "order_update",
        "order_id": delivery.order_id,
        "status": "saiu_entrega",
        "action": "start_delivery",
        "delivery_id": delivery_id
    })

    return delivery

@app.post("/api/deliveries/{delivery_id}/complete")
async def complete_delivery(delivery_id: int, session: AsyncSession = Depends(get_db)):
    """Finaliza entrega"""
    service = DeliveryService(session)
    delivery = service.complete_delivery(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    # Broadcast
    await manager.broadcast({
        "type": "order_update",
        "order_id": delivery.order_id,
        "status": "entregue",
        "action": "complete_delivery",
        "delivery_id": delivery_id
    })

    return delivery

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
