"""
Aplicação principal FastAPI para automação de pedidos de gás via WhatsApp.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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
from app.core.secure_logging import get_secure_logger

# Logger seguro para este módulo (sanitiza dados sensíveis automaticamente)
secure_logger = get_secure_logger(__name__)

# Importar rotas
from app.api import webhooks, orders, products, customers, websocket, chats, auth, chatbot, users, drivers, cargas
from app.api import admin_users
from app.api import admin_errors
from app.api import admin_system_health
from app.api import admin_debug
from app.api import owner_dashboard
from app.api import images, tipos_preco, vasilhames, locations, exports, firebird_schema, rpa, daily_summary, promotions, whatsapp_broadcast

# Importar serviços para delivery system
try:
    from app.services.customer_service import CustomerService
    from app.services.order_service import OrderService
    from app.services.delivery_service import DeliveryService
    from app.services.driver_service import DriverService
    from app.services.product_service import ProductService
    secure_logger.info("Serviços importados com sucesso")
except ImportError as e:
    secure_logger.error("Erro ao importar serviços", exc=e)
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
    print(f"[START] Iniciando {settings.app_name} v{settings.app_version}")
    print(f"[ENV] Ambiente: {settings.environment}")

    # Conectar Redis
    await redis_manager.connect()
    print("[OK] Redis conectado")
    
    # Iniciar monitor de heartbeat WebSocket
    from app.api.websocket import manager as ws_manager
    heartbeat_task = asyncio.create_task(ws_manager.heartbeat_monitor())
    print("[OK] Monitor de heartbeat WebSocket iniciado")
    
    # Iniciar Redis WebSocket Bridge para escala horizontal (FASE 3)
    from app.core.redis_websocket_bridge import redis_ws_bridge
    await redis_ws_bridge.start()
    print("[OK] Redis WebSocket Bridge iniciado (escala horizontal)")
    
    # Iniciar Event Batcher para agrupar eventos (FASE 3)
    await ws_manager.enable_batching()
    print("[OK] Event Batcher iniciado (agrupamento de eventos)")
    
    # Inicializar métricas Prometheus (FASE 3)
    metrics.init_system_info(version=settings.app_version, environment=settings.environment)
    print("[OK] Métricas Prometheus inicializadas")
    
    # Iniciar task de atualização periódica de métricas
    from app.core.redis_websocket_bridge import redis_ws_bridge
    metrics_task = asyncio.create_task(_metrics_updater(ws_manager, redis_ws_bridge))
    print("[OK] Monitor de métricas iniciado")

    # TODO: Pré-carregar modelo Ollama se necessário
    # TODO: Verificar conexão com Firebird se habilitado

    yield

    # Shutdown
    print("[STOP] Encerrando aplicação...")
    
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
    print("[OK] Conexões encerradas")


# Criar aplicação FastAPI
# Docs são habilitados em qualquer ambiente que não seja produção
_enable_docs = not settings.is_production

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    API de automação de pedidos de gás via WhatsApp.

    ## Funcionalidades

    - **Webhooks**: Recebe mensagens do WhatsApp (WAHA)
    - **Pedidos**: CRUD completo de pedidos
    - **Clientes**: Gerenciamento de clientes
    - **Produtos**: Catálogo de produtos (P13, P20, P45)
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

# Configurar CORS (web + mobile Capacitor/Android)
# allow_origin_regex: capacitor://, ionic://, https://localhost, Origin: null (Android WebView)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^(capacitor://|ionic://)localhost(:\d+)?$|^https://localhost(:\d+)?$|^null$",
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
            "payments": False,
            "ai": True,
            "firebird": settings.firebird_enabled,
        },
        "supported_bairros": settings.supported_bairros,
    }


# ==================== Handlers de Erro ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global de exceções não tratadas."""
    # Central de erros (best-effort). Não deve causar cascata.
    try:
        from app.database import AsyncSessionLocal
        from app.services.error_center import upsert_error_event

        async with AsyncSessionLocal() as s:
            await upsert_error_event(
                s,
                service="backend",
                error_type=type(exc).__name__,
                message=str(exc) or type(exc).__name__,
                details={
                    "path": getattr(request, "url", None).path if getattr(request, "url", None) else None,
                    "method": getattr(request, "method", None),
                },
            )
    except Exception:
        # Nunca falhar o handler por causa do error center
        pass

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
def metrics_endpoint(x_metrics_token: str = Header(..., alias="X-Metrics-Token")):
    """
    Endpoint de métricas Prometheus (FASE 3) - PROTEGIDO.
    
    Expõe métricas customizadas para coleta pelo Prometheus:
    - Conexões WebSocket ativas por role e instância
    - Mensagens enviadas/recebidas
    - Latência de broadcasts
    - Redis Pub/Sub (mensagens publicadas/recebidas)
    - Event batching (buffer, batch size)
    - Message Store (replay requests, mensagens armazenadas)
    - Erros e desconexões
    - Uptime do sistema
    
    Segurança:
    - Requer token de autenticação no header X-Metrics-Token
    - Token configurado via variável de ambiente METRICS_TOKEN
    
    Formato: Prometheus text-based exposition format
    """
    # Validar token
    if not settings.metrics_token or x_metrics_token != settings.metrics_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing metrics token. Set METRICS_TOKEN environment variable."
        )
    
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
app.include_router(admin_users.router, prefix="/api", tags=["Admin Users"])
app.include_router(admin_system_health.router, prefix="/api", tags=["Admin System Health"])
app.include_router(admin_errors.router, prefix="/api", tags=["Admin Errors"])
app.include_router(admin_debug.router, prefix="/api", tags=["Admin Debug"])
app.include_router(owner_dashboard.router, prefix="/api", tags=["Owner Dashboard"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["Chatbot"])
app.include_router(drivers.router, prefix="/api/drivers", tags=["Drivers"])
app.include_router(cargas.router, prefix="/api/cargas", tags=["Cargas"])
app.include_router(images.router, prefix="/api/images", tags=["Images"])
app.include_router(tipos_preco.router, prefix="/api/tipos-preco", tags=["Tipos de Preço"])
app.include_router(vasilhames.router, prefix="/api/vasilhames", tags=["Vasilhames"])
app.include_router(locations.router, prefix="/api/locations", tags=["Locations"])
app.include_router(exports.router, prefix="/api/exports", tags=["Exports"])
app.include_router(firebird_schema.router, prefix="/api/firebird", tags=["Firebird Schema"])
app.include_router(rpa.router, prefix="/api/rpa", tags=["RPA Gasmaster"])
app.include_router(daily_summary.router, prefix="/api/daily-summary", tags=["Daily Summary"])
app.include_router(promotions.router, prefix="/api/promotions", tags=["Promotions"])
app.include_router(whatsapp_broadcast.router, prefix="/api/whatsapp", tags=["WhatsApp Broadcast"])


# ==================== AUDIT LOGS (rota direta para compatibilidade) ====================

@app.get("/api/audit-logs", tags=["Audit"])
async def get_audit_logs_direct(
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Lista logs de auditoria (admin/owner only).
    Rota direta para compatibilidade com frontend.
    """
    from app.api.users import list_audit_logs
    return await list_audit_logs(limit=limit, offset=offset, current_user=user, session=session)


@app.get("/api/audit-logs/summary", tags=["Audit"])
async def get_audit_logs_summary_direct(
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Lista logs de auditoria com contagens por categoria.
    Rota direta para compatibilidade com frontend.
    """
    from app.api.users import audit_logs_summary

    return await audit_logs_summary(limit=limit, offset=offset, current_user=user, session=session)


@app.get("/api/audit-logs/{log_id}", tags=["Audit"])
async def get_audit_log_detail_direct(
    log_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Retorna um audit log específico (para modal de detalhes).
    """
    from app.api.users import get_audit_log

    return await get_audit_log(log_id=log_id, current_user=user, session=session)


# ==================== DASHBOARD STATISTICS ENDPOINTS ====================

@app.get("/api/stats")
async def get_owner_stats(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    """Estatísticas para dashboard do owner - DADOS REAIS"""
    try:
        from datetime import datetime, timezone, timedelta
        
        # Usuários - contagem real
        from app.models.auth_models import User
        total_users_result = await session.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0
        
        active_users_result = await session.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_users_result.scalar() or 0

        # Conversas - contagem real
        from app.models.auth_models import Conversation
        total_conversations_result = await session.execute(select(func.count(Conversation.id)))
        total_conversations = total_conversations_result.scalar() or 0

        # Pedidos - contagem e receita REAL
        try:
            from app.models.order import Order
            total_orders_result = await session.execute(select(func.count(Order.id)))
            total_orders = total_orders_result.scalar() or 0
            
            # Pedidos hoje - contagem real
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_orders_result = await session.execute(
                select(func.count(Order.id)).where(Order.created_at >= today)
            )
            today_orders = today_orders_result.scalar() or 0
            
            # Receita REAL - soma dos valores dos pedidos
            revenue_result = await session.execute(
                select(func.coalesce(func.sum(Order.total_amount), 0))
                .where(Order.status != 'cancelled')
            )
            revenue = float(revenue_result.scalar() or 0)
            
        except Exception as e:
            secure_logger.error("Erro ao buscar pedidos", exc=e)
            total_orders = 0
            today_orders = 0
            revenue = 0.0

        # Operadores ativos - contagem real
        active_operators_result = await session.execute(
            select(func.count(User.id)).where(
                User.role.in_(["admin", "operator", "owner"]),
                User.is_active == True
            )
        )
        active_operators = active_operators_result.scalar() or 0

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
        secure_logger.error("Erro ao buscar estatísticas", exc=e)
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

        # Mensagens reais da tabela message
        from app.models.auth_models import Message
        total_messages_result = await session.execute(select(func.count(Message.id)))
        total_messages = total_messages_result.scalar() or 0

        # Mensagens hoje (real)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        messages_today_result = await session.execute(
            select(func.count(Message.id)).where(Message.timestamp >= today)
        )
        messages_today = messages_today_result.scalar() or 0

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
        secure_logger.error("Erro ao buscar estatísticas admin", exc=e)
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
    """Relatório financeiro detalhado - DADOS REAIS"""
    try:
        from datetime import datetime, timezone, timedelta
        from app.models.order import Order

        # Se não especificar datas, usar último mês
        if not end_date:
            end_date = datetime.now(timezone.utc)
        else:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)

        # Receita REAL - soma dos pedidos no período
        revenue_result = await session.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0))
            .where(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status != 'cancelled'
            )
        )
        total_revenue = float(revenue_result.scalar() or 0)

        # Total de pedidos no período
        orders_count_result = await session.execute(
            select(func.count(Order.id))
            .where(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        )
        total_orders = orders_count_result.scalar() or 0

        # Receita diária REAL
        daily_revenue_result = await session.execute(
            select(
                func.date(Order.created_at).label('date'),
                func.coalesce(func.sum(Order.total_amount), 0).label('revenue')
            )
            .where(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status != 'cancelled'
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        
        daily_revenue = {}
        revenue_trend = []
        dates = []
        for row in daily_revenue_result:
            day_str = row.date.strftime('%Y-%m-%d')
            daily_revenue[day_str] = float(row.revenue or 0)
            revenue_trend.append(float(row.revenue or 0))
            dates.append(day_str)

        # Preencher dias sem pedidos com 0
        current_date = start_date.date()
        end_date_only = end_date.date()
        while current_date <= end_date_only:
            day_str = current_date.strftime('%Y-%m-%d')
            if day_str not in daily_revenue:
                daily_revenue[day_str] = 0.0
                revenue_trend.append(0.0)
                dates.append(day_str)
            current_date += timedelta(days=1)

        # Ordenar por data
        sorted_dates = sorted(daily_revenue.keys())
        revenue_trend = [daily_revenue[d] for d in sorted_dates]
        dates = sorted_dates

        # Despesas (por enquanto 0 - pode ser implementado depois)
        total_expenses = 0.0
        net_profit = total_revenue - total_expenses

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
                "revenue_trend": revenue_trend,
                "dates": dates
            }
        }

    except Exception as e:
        secure_logger.error("Erro no relatório financeiro", exc=e)
        return {
            "period": {"start_date": "", "end_date": ""},
            "summary": {"total_revenue": 0, "total_expenses": 0, "net_profit": 0, "total_orders": 0, "average_ticket": 0, "profit_margin": 0},
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
    """Relatório de pedidos - DADOS REAIS"""
    try:
        from datetime import datetime, timezone, timedelta
        from app.models.order import Order
        from app.models.customer import Customer

        if not end_date:
            end_date = datetime.now(timezone.utc)
        else:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)

        # Buscar pedidos reais do período
        orders_result = await session.execute(
            select(Order)
            .where(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
            .order_by(Order.created_at.desc())
            .limit(50)  # Últimos 50 pedidos
        )
        orders_list = orders_result.scalars().all()

        # Contar por status
        status_counts = {
            "completed": 0,
            "delivered": 0,
            "pending": 0,
            "paid": 0,
            "preparing": 0,
            "dispatched": 0,
            "cancelled": 0
        }

        orders_data = []
        for order in orders_list:
            status = order.status or "pending"
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts["pending"] += 1

            # Buscar nome do cliente
            customer_name = "Cliente"
            if order.customer_id:
                customer_result = await session.execute(
                    select(Customer).where(Customer.id == order.customer_id)
                )
                customer = customer_result.scalar_one_or_none()
                if customer:
                    customer_name = customer.name or f"Cliente {customer.phone}"

            orders_data.append({
                "id": str(order.id),
                "order_number": order.order_number,
                "status": status,
                "total": float(order.total_amount or 0),
                "created_at": order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else "",
                "customer": customer_name
            })

        total_orders = len(orders_list)
        # Concluídos = delivered (entregue)
        completed_count = status_counts.get("delivered", 0)
        # Pendentes = pending (aguardando pagamento) - NÃO incluir paid
        pending_count = status_counts.get("pending", 0)
        # Em processamento = paid, preparing, dispatched (não são pendentes nem concluídos)
        in_process_count = (
            status_counts.get("paid", 0) + 
            status_counts.get("preparing", 0) + 
            status_counts.get("dispatched", 0)
        )

        return {
            "period": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d')
            },
            "summary": {
                "total_orders": total_orders,
                "completed_rate": (completed_count / total_orders * 100) if total_orders > 0 else 0,
                "by_status": {
                    "completed": completed_count,
                    "pending": pending_count,
                    "in_process": in_process_count,
                    "cancelled": status_counts.get("cancelled", 0)
                }
            },
            "orders": orders_data
        }

    except Exception as e:
        secure_logger.error("Erro no relatório de pedidos", exc=e)
        return {
            "period": {"start_date": "", "end_date": ""},
            "summary": {"total_orders": 0, "completed_rate": 0, "by_status": {}},
            "orders": []
        }

@app.get("/api/reports/export/orders")
async def export_orders_csv(
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Exportar pedidos em CSV - DADOS REAIS"""
    from fastapi.responses import Response
    from datetime import datetime, timezone, timedelta
    from app.models.order import Order
    from app.models.customer import Customer
    import csv
    import io

    try:
        # Definir período
        if not end_date:
            end_date = datetime.now(timezone.utc)
        else:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)

        # Buscar pedidos reais
        orders_result = await session.execute(
            select(Order)
            .where(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
            .order_by(Order.created_at.desc())
        )
        orders = orders_result.scalars().all()

        # Gerar CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Número', 'Status', 'Total', 'Data', 'Cliente'])

        for order in orders:
            customer_name = "N/A"
            if order.customer_id:
                customer_result = await session.execute(
                    select(Customer).where(Customer.id == order.customer_id)
                )
                customer = customer_result.scalar_one_or_none()
                if customer:
                    customer_name = customer.name or customer.phone or "N/A"

            writer.writerow([
                str(order.id),
                order.order_number,
                order.status or "pending",
                f"{order.total_amount:.2f}" if order.total_amount else "0.00",
                order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else "",
                customer_name
            ])

        csv_content = output.getvalue()
        output.close()

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=pedidos.csv"}
        )

    except Exception as e:
        secure_logger.error("Erro ao exportar pedidos", exc=e)
        return Response(
            content="Erro ao gerar CSV",
            media_type="text/plain",
            status_code=500
        )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pedidos.csv"}
    )

@app.get("/api/reports/export/financial")
async def export_financial_csv(
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Exportar relatório financeiro em CSV - DADOS REAIS"""
    from fastapi.responses import Response
    from datetime import datetime, timezone, timedelta
    from app.models.order import Order
    import csv
    import io

    try:
        # Definir período
        if not end_date:
            end_date = datetime.now(timezone.utc)
        else:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)

        # Buscar receita diária real
        daily_revenue_result = await session.execute(
            select(
                func.date(Order.created_at).label('date'),
                func.coalesce(func.sum(Order.total_amount), 0).label('revenue')
            )
            .where(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.status != 'cancelled'
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )

        # Gerar CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Data', 'Receita', 'Despesas', 'Lucro'])

        for row in daily_revenue_result:
            date_str = row.date.strftime('%Y-%m-%d')
            revenue = float(row.revenue or 0)
            expenses = 0.0  # Por enquanto 0 - pode ser implementado depois
            profit = revenue - expenses
            writer.writerow([date_str, f"{revenue:.2f}", f"{expenses:.2f}", f"{profit:.2f}"])

        csv_content = output.getvalue()
        output.close()

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=relatorio_financeiro.csv"}
        )

    except Exception as e:
        secure_logger.error("Erro ao exportar relatório financeiro", exc=e)
        return Response(
            content="Erro ao gerar CSV",
            media_type="text/plain",
            status_code=500
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
