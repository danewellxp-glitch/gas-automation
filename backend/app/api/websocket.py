"""
WebSocket para atualizações em tempo real - VERSÃO ESCALÁVEL.

Suporta:
- Broadcast filtrado por papel/bairro/região
- Rate limiting (10 broadcasts/segundo)
- Heartbeat para limpeza de conexões mortas
- Metadados por conexão para autorização
"""

import asyncio
import json
import logging
from typing import Set, Dict, Callable, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.auth import get_current_user_ws
from app.models.auth_models import User
from app.core.redis_websocket_bridge import redis_ws_bridge
from app.core.event_batcher import EventBatcher
from app.core.message_store import message_store

logger = logging.getLogger(__name__)

router = APIRouter()


class UserRole(str, Enum):
    """Papéis de usuário do sistema"""
    ADMIN = "admin"
    OPERATOR = "operator"
    OWNER = "owner"
    MANAGER = "manager"
    DRIVER = "driver"  # Role para entregadores
    USER = "user"


class ConnectionMetadata:
    """Metadados sobre cada conexão WebSocket"""
    
    def __init__(self, websocket: WebSocket, user_id: str, user_role: UserRole, 
                 bairro: Optional[str] = None, region: Optional[str] = None):
        self.websocket = websocket
        self.user_id = user_id
        self.user_role = user_role
        self.bairro = bairro
        self.region = region
        self.connected_at = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)
        self.session_id = None  # Para deduplicação de abas


class ScalableConnectionManager:
    """
    Gerenciador de conexões WebSocket otimizado para escala.
    
    Mudanças principais:
    1. Armazena metadados de cada conexão
    2. Suporta filtros para broadcast seletivo
    3. Implementa rate limiting
    4. Monitora heartbeat para limpar conexões mortas
    5. Redis Pub/Sub para comunicação entre instâncias (FASE 3)
    """

    def __init__(self, max_broadcasts_per_second: int = 10, enable_redis_bridge: bool = True):
        # Conexões agrupadas por user_id (para deduplicação)
        self.connections: Dict[str, Set[ConnectionMetadata]] = {}
        self.max_broadcasts_per_second = max_broadcasts_per_second
        self.broadcast_timestamps: list = []  # Para rate limiting
        self.heartbeat_timeout_seconds = 300  # 5 minutos
        
        # Redis Bridge para escala horizontal (FASE 3)
        self.enable_redis_bridge = enable_redis_bridge
        self.redis_bridge_initialized = False
        
        if enable_redis_bridge:
            # Registrar handler para receber eventos de outras instâncias
            redis_ws_bridge.register_handler(self._handle_redis_event)
        
        # Event Batcher para agrupar eventos (FASE 3)
        self.event_batcher = EventBatcher(
            flush_callback=self._batch_flush_callback,
            flush_interval_ms=100,  # Flush a cada 100ms
            max_batch_size=50       # Ou quando tiver 50 eventos
        )
        self.batching_enabled = False  # Será habilitado no startup

    async def connect(self, websocket: WebSocket, user_id: str, user_role: UserRole,
                     bairro: Optional[str] = None, region: Optional[str] = None):
        """
        Aceita nova conexão com metadados.
        
        Args:
            websocket: Conexão WebSocket
            user_id: ID do usuário
            user_role: Papel do usuário (admin, operator, owner, manager)
            bairro: Bairro (para operadores)
            region: Região (para managers)
        """
        await websocket.accept()
        
        # Criar metadados da conexão
        metadata = ConnectionMetadata(
            websocket=websocket,
            user_id=user_id,
            user_role=user_role,
            bairro=bairro,
            region=region
        )
        
        # Agrupar por user_id para deduplicação
        if user_id not in self.connections:
            self.connections[user_id] = set()
        
        self.connections[user_id].add(metadata)
        
        total_connections = sum(len(conns) for conns in self.connections.values())
        logger.info(
            f"WebSocket conectado: {user_id} ({user_role}) - "
            f"Total: {total_connections} conexões, "
            f"{len(self.connections)} usuários"
        )

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove uma conexão específica"""
        if user_id in self.connections:
            self.connections[user_id] = {
                conn for conn in self.connections[user_id]
                if conn.websocket is not websocket
            }
            if not self.connections[user_id]:
                del self.connections[user_id]
        
        total_connections = sum(len(conns) for conns in self.connections.values())
        logger.info(f"WebSocket desconectado. Total: {total_connections} conexões")

    async def broadcast(self, message: dict, filter_fn: Optional[Callable] = None, publish_to_redis: bool = True):
        """
        Envia mensagem com filtro opcional e rate limiting.
        
        Args:
            message: Mensagem a enviar
            filter_fn: Função de filtro que retorna True se deve enviar
                       Exemplo: lambda metadata: metadata.user_role == "admin"
            publish_to_redis: Se True, publica no Redis para outras instâncias (FASE 3)
        """
        # RATE LIMITING: Máximo 10 broadcasts por segundo
        now = datetime.now(timezone.utc).timestamp()
        self.broadcast_timestamps = [
            ts for ts in self.broadcast_timestamps
            if now - ts < 1.0  # Janela de 1 segundo
        ]
        
        if len(self.broadcast_timestamps) >= self.max_broadcasts_per_second:
            logger.warning(f"Rate limit atingido! Ignorando broadcast")
            return
        
        self.broadcast_timestamps.append(now)
        
        # FASE 3: Publicar no Redis para outras instâncias
        if publish_to_redis and self.enable_redis_bridge:
            await redis_ws_bridge.publish_event(
                event_type=message.get('type', 'unknown'),
                data=message
            )
            # Redis já vai propagar para esta instância também, então não precisamos fazer broadcast local
            return
        
        # Broadcast local (quando vem do Redis ou quando Redis está desabilitado)
        await self._broadcast_local(message, filter_fn)
    
    async def _broadcast_local(self, message: dict, filter_fn: Optional[Callable] = None, store_message: bool = True):
        """
        Faz broadcast apenas para conexões locais (desta instância).
        Usado quando mensagem vem do Redis ou quando Redis está desabilitado.
        
        Args:
            message: Mensagem a enviar
            filter_fn: Função de filtro opcional
            store_message: Se True, armazena no MessageStore para replay (FASE 3)
        """
        # Coletar todas as conexões a notificar
        connections_to_notify = []
        user_ids_to_store = set()
        
        for user_connections in self.connections.values():
            for metadata in user_connections:
                if filter_fn is None or filter_fn(metadata):
                    connections_to_notify.append(metadata)
                    user_ids_to_store.add(metadata.user_id)
        
        if not connections_to_notify:
            logger.debug(f"Nenhuma conexão local correspondeu ao filtro")
            return
        
        # Gerar sequence ID para a mensagem (FASE 3)
        seq_id = None
        if store_message:
            seq_id = await message_store.get_next_seq_id()
            message['seq_id'] = seq_id
        
        # Enviar para todas as conexões que passaram no filtro
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        logger.debug(
            f"Broadcasting local '{message.get('type')}' para "
            f"{len(connections_to_notify)} conexões (seq_id={seq_id})"
        )
        
        for metadata in connections_to_notify:
            try:
                await metadata.websocket.send_text(message_json)
                metadata.last_heartbeat = datetime.now(timezone.utc)
            except Exception as e:
                logger.warning(f"Erro ao enviar para {metadata.user_id}: {e}")
                disconnected.append((metadata.user_id, metadata.websocket))
        
        # Armazenar mensagem no MessageStore para cada usuário (FASE 3)
        if store_message and seq_id:
            for user_id in user_ids_to_store:
                try:
                    await message_store.store_message(
                        user_id=user_id,
                        event_type=message.get('type', 'unknown'),
                        data=message,
                        seq_id=seq_id
                    )
                except Exception as e:
                    logger.error(f"❌ Erro ao armazenar mensagem para {user_id}: {e}")
        
        # Remover conexões que falharam
        for user_id, websocket in disconnected:
            self.disconnect(websocket, user_id)
    
    async def _handle_redis_event(self, event_type: str, data: dict, source_instance_id: str):
        """
        Handler para eventos recebidos do Redis (de outras instâncias).
        Faz broadcast local para os clientes WebSocket conectados a esta instância.
        """
        # Fazer broadcast local (sem publicar no Redis novamente para evitar loop)
        await self._broadcast_local(data, filter_fn=None)
        
        logger.debug(
            f"📥 Evento Redis processado: {event_type} "
            f"(de instance={source_instance_id[:8]}, "
            f"{sum(len(conns) for conns in self.connections.values())} conexões locais)"
        )
    
    async def _batch_flush_callback(self, batched_events: dict):
        """
        Callback quando batch de eventos está pronto para enviar.
        Chamado pelo EventBatcher após flush_interval ou quando max_batch_size é atingido.
        """
        for event_type, data in batched_events.items():
            # Enviar cada tipo de evento via broadcast local
            await self._broadcast_local(data, filter_fn=None)
    
    async def enable_batching(self):
        """Habilita o event batching."""
        if not self.batching_enabled:
            await self.event_batcher.start()
            self.batching_enabled = True
            logger.info("📦 Event batching habilitado")
    
    async def disable_batching(self):
        """Desabilita o event batching."""
        if self.batching_enabled:
            await self.event_batcher.stop()
            self.batching_enabled = False
            logger.info("📦 Event batching desabilitado")

    async def broadcast_to_role(self, message: dict, required_role: UserRole):
        """Envia apenas para usuários com papel específico"""
        await self.broadcast(
            message,
            filter_fn=lambda metadata: metadata.user_role == required_role
        )

    async def broadcast_to_admin_only(self, message: dict):
        """Envia apenas para admins"""
        await self.broadcast(
            message,
            filter_fn=lambda metadata: metadata.user_role == UserRole.ADMIN
        )

    async def broadcast_to_neighborhood(self, message: dict, bairro: str):
        """Envia apenas para operadores de um bairro específico + admins"""
        await self.broadcast(
            message,
            filter_fn=lambda metadata: (
                metadata.user_role == UserRole.ADMIN or  # Admin vê tudo
                metadata.user_role == UserRole.OWNER or  # Owner vê tudo
                (metadata.user_role == UserRole.OPERATOR and metadata.bairro == bairro)
            )
        )

    async def broadcast_to_region(self, message: dict, region: str):
        """Envia apenas para managers de uma região específica + admins"""
        await self.broadcast(
            message,
            filter_fn=lambda metadata: (
                metadata.user_role == UserRole.ADMIN or
                metadata.user_role == UserRole.OWNER or
                (metadata.user_role == UserRole.MANAGER and metadata.region == region)
            )
        )

    async def heartbeat_monitor(self):
        """
        Monitor de heartbeat - remove conexões mortas.
        Execute com: asyncio.create_task(manager.heartbeat_monitor())
        """
        logger.info("⏰ Iniciando monitor de heartbeat WebSocket")
        while True:
            try:
                await asyncio.sleep(30)  # Verificar a cada 30 segundos
                
                now = datetime.now(timezone.utc)
                timeout = timedelta(seconds=self.heartbeat_timeout_seconds)
                
                # Verificar conexões mortas
                for user_id, user_connections in list(self.connections.items()):
                    for metadata in list(user_connections):
                        time_since_heartbeat = now - metadata.last_heartbeat
                        
                        if time_since_heartbeat > timeout:
                            logger.warning(
                                f"Conexão morta detectada: {user_id} "
                                f"({time_since_heartbeat.total_seconds():.0f}s sem resposta)"
                            )
                            try:
                                await metadata.websocket.close()
                            except Exception as e:
                                logger.debug(f"Erro ao fechar websocket: {e}")
                            self.disconnect(metadata.websocket, user_id)
                        else:
                            # Enviar ping para manter viva
                            try:
                                await metadata.websocket.send_json({
                                    "type": "ping",
                                    "timestamp": now.isoformat()
                                })
                            except Exception as e:
                                logger.debug(f"Erro ao enviar ping: {e}")
                                self.disconnect(metadata.websocket, user_id)
                
                # Log de estatísticas
                total_connections = sum(len(conns) for conns in self.connections.values())
                if total_connections > 0:
                    logger.debug(
                        f"📊 WebSocket Stats: {total_connections} conexões, "
                        f"{len(self.connections)} usuários"
                    )
                
            except Exception as e:
                logger.error(f"Erro no monitor de heartbeat: {e}")
                await asyncio.sleep(5)  # Esperar antes de tentar novamente

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Envia mensagem para uma conexão específica."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.warning(f"Erro ao enviar mensagem pessoal: {e}")


# Instância global
manager = ScalableConnectionManager(max_broadcasts_per_second=10)


@router.websocket("/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token obrigatório"),
    since_seq_id: Optional[int] = Query(None)
):
    """
    WebSocket para atualizações do dashboard em tempo real com filtros por papel/bairro.

    Eventos enviados:
    - new_order: Novo pedido criado
    - order_update: Status do pedido atualizado
    - new_message: Nova mensagem WhatsApp
    - metrics_update: Métricas atualizadas
    
    Query Parameters:
    - token: JWT token para autenticação (OBRIGATÓRIO)
    - since_seq_id: (FASE 3) Sequence ID da última mensagem recebida.
                     Se fornecido, faz replay de mensagens perdidas durante desconexão.
    
    Features:
    - Compressão automática (permessage-deflate)
    - Rate limiting (10 broadcasts/seg)
    - Heartbeat automático
    - Filtros por papel/bairro
    - Reconexão inteligente com replay (FASE 3)
    
    Segurança:
    - Token JWT validado ANTES de aceitar conexão
    - Conexões não autenticadas são rejeitadas imediatamente
    """
    from app.database import AsyncSessionLocal
    from app.auth import get_current_user_ws
    
    # VALIDAR TOKEN ANTES DE ACEITAR CONEXÃO
    async with AsyncSessionLocal() as session:
        user = await get_current_user_ws(token, session)
        
        if not user or not user.is_active:
            logger.warning(f"Tentativa de conexão WebSocket com token inválido")
            await websocket.close(code=1008, reason="Unauthorized: Invalid or expired token")
            return
        
        user_id = str(user.id)
        user_role = UserRole(user.role) if user.role in [r.value for r in UserRole] else UserRole.USER
        # TODO: Adicionar campos bairro/region ao modelo User quando necessário
        bairro = getattr(user, 'bairro', None)
        region = getattr(user, 'region', None)
        logger.info(f"WebSocket autenticado: user={user.username}, role={user_role}")
    
    # Conectar com metadados (apenas se autenticado)
    # Nota: Compressão é habilitada automaticamente pelo Uvicorn se o cliente suportar
    await manager.connect(
        websocket=websocket,
        user_id=user_id,
        user_role=user_role,
        bairro=bairro,
        region=region
    )

    # Enviar estado inicial
    current_seq_id = await message_store.get_latest_seq_id(user_id) or 0
    await manager.send_personal(websocket, {
        "type": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Conectado ao dashboard em tempo real",
        "user_role": user_role.value,
        "filters_enabled": True,
        "current_seq_id": current_seq_id,
    })
    
    # FASE 3: Replay de mensagens perdidas durante desconexão
    if since_seq_id is not None and since_seq_id > 0:
        try:
            missed_messages = await message_store.get_messages_since(
                user_id=user_id,
                since_seq_id=since_seq_id,
                limit=100  # Máximo 100 mensagens de replay
            )
            
            if missed_messages:
                logger.info(
                    f"🔄 Replay: enviando {len(missed_messages)} mensagens perdidas "
                    f"para user={user_id} (since={since_seq_id})"
                )
                
                # Enviar notificação de replay
                await manager.send_personal(websocket, {
                    "type": "replay_start",
                    "count": len(missed_messages),
                    "since_seq_id": since_seq_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                
                # Enviar mensagens perdidas
                for msg in missed_messages:
                    await manager.send_personal(websocket, msg.data)
                
                # Notificar fim do replay
                await manager.send_personal(websocket, {
                    "type": "replay_end",
                    "count": len(missed_messages),
                    "last_seq_id": missed_messages[-1].seq_id if missed_messages else since_seq_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                logger.info(f"✅ Nenhuma mensagem perdida para user={user_id}")
        
        except Exception as e:
            logger.error(f"❌ Erro ao fazer replay de mensagens: {e}")
            await manager.send_personal(websocket, {
                "type": "replay_error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    try:
        while True:
            # Manter conexão ativa e processar mensagens do cliente
            data = await websocket.receive_text()

            # Processar comandos do cliente
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await manager.send_personal(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                elif message.get("type") == "heartbeat":
                    # Cliente enviou heartbeat, atualizar timestamp
                    # Já atualizado automaticamente no broadcast
                    pass
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


# =====================================
# Funções para emitir eventos de outras partes do sistema
# COM FILTROS INTELIGENTES
# =====================================

async def emit_new_order(order_data: dict):
    """
    Emite evento de novo pedido com filtro inteligente.
    
    - Admins/Owners: Veem todos os pedidos
    - Operadores: Veem apenas pedidos do seu bairro
    - Managers: Veem pedidos da sua região
    """
    bairro = order_data.get("delivery_bairro") or order_data.get("bairro")
    
    if bairro:
        # Broadcast filtrado por bairro
        await manager.broadcast_to_neighborhood(
            {
                "type": "new_order",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": order_data,
            },
            bairro=bairro
        )
    else:
        # Se não tem bairro, envia para admins/owners apenas
        await manager.broadcast(
            {
                "type": "new_order",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": order_data,
            },
            filter_fn=lambda m: m.user_role in [UserRole.ADMIN, UserRole.OWNER]
        )


async def emit_order_update(order_id: str, status: str, order_data: dict = None):
    """
    Emite evento de atualização de pedido com filtro inteligente.
    
    Similar ao new_order, filtra por bairro quando disponível.
    """
    bairro = None
    if order_data:
        bairro = order_data.get("delivery_bairro") or order_data.get("bairro")
    
    message = {
        "type": "order_update",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "order_id": order_id,
            "status": status,
            "order": order_data,
        },
    }
    
    if bairro:
        await manager.broadcast_to_neighborhood(message, bairro=bairro)
    else:
        # Sem bairro, envia para todos (fallback)
        await manager.broadcast(message)


async def emit_new_message(phone: str, message: str, direction: str = "incoming", customer_data: dict = None):
    """
    Emite evento de nova mensagem WhatsApp.
    
    Mensagens são enviadas para todos, pois qualquer operador pode responder.
    Mas poderia filtrar por bairro do cliente se disponível.
    """
    # Obter trace_id do contexto
    from app.utils.structured_logging import get_message_context
    context_data = get_message_context()
    trace_id = context_data.get("trace_id")
    
    bairro = None
    if customer_data:
        bairro = customer_data.get("bairro")
    
    msg = {
        "type": "new_message",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "phone": phone,
            "message": message,
            "direction": direction,
        },
    }
    
    logger.info(
        f"[WEBSOCKET_PUBLISH_START] trace_id={trace_id} phone={phone} "
        f"event_type=new_message bairro={bairro}",
        extra={
            "trace_id": trace_id,
            "phone": phone,
            "event_type": "new_message",
            "bairro": bairro,
            "step": "websocket_publish_start"
        }
    )
    
    try:
        if bairro:
            await manager.broadcast_to_neighborhood(msg, bairro=bairro)
        else:
            # Broadcast geral para mensagens sem bairro
            await manager.broadcast(msg)
        
        logger.info(
            f"[WEBSOCKET_PUBLISH_COMPLETE] trace_id={trace_id} phone={phone} success=True",
            extra={
                "trace_id": trace_id,
                "phone": phone,
                "step": "websocket_publish_complete",
                "success": True
            }
        )
    except Exception as e:
        logger.error(
            f"[WEBSOCKET_PUBLISH_ERROR] trace_id={trace_id} phone={phone} error={e}",
            exc_info=True,
            extra={
                "trace_id": trace_id,
                "phone": phone,
                "step": "websocket_publish_error"
            }
        )
        # Não propagar exceção - evento não é crítico para resposta ao cliente


async def emit_metrics_update(metrics: dict):
    """
    Emite atualização de métricas.
    
    Métricas globais vão para admins/owners apenas.
    Métricas específicas podem ser filtradas por bairro/região.
    """
    metric_scope = metrics.get("scope", "global")
    
    if metric_scope == "global":
        # Métricas globais apenas para admins/owners
        await manager.broadcast(
            {
                "type": "metrics_update",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": metrics,
            },
            filter_fn=lambda m: m.user_role in [UserRole.ADMIN, UserRole.OWNER]
        )
    elif metric_scope == "bairro" and metrics.get("bairro"):
        # Métricas de bairro específico
        await manager.broadcast_to_neighborhood(
            {
                "type": "metrics_update",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": metrics,
            },
            bairro=metrics["bairro"]
        )
    else:
        # Fallback: broadcast para todos
        await manager.broadcast({
            "type": "metrics_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": metrics,
        })


# =====================================
# Eventos para DRIVER (Entregador)
# FASE 3.5 - Role de Entregador
# =====================================

async def emit_delivery_assigned(delivery_data: dict):
    """
    Notifica driver quando uma entrega é alocada para ele.
    
    Args:
        delivery_data: dict com delivery_id, driver_id, order_number, address, etc.
    
    Exemplo:
        await emit_delivery_assigned({
            "delivery_id": "uuid-123",
            "driver_id": "uuid-456",
            "order_number": 1234,
            "order_id": "uuid-789",
            "delivery_address": {...},
            "items": [...],
            "estimated_minutes": 40
        })
    """
    driver_id = delivery_data.get("driver_id")
    
    if not driver_id:
        logger.warning("emit_delivery_assigned chamado sem driver_id")
        return
    
    await manager.broadcast(
        message={
            "type": "delivery_assigned",
            "data": delivery_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        filter_fn=lambda m: (
            m.user_role == UserRole.DRIVER and 
            str(m.user_id) == str(driver_id)
        )
    )
    
    logger.info(f"📦 Entrega #{delivery_data.get('order_number')} alocada ao driver {driver_id}")


async def emit_delivery_updated(delivery_data: dict):
    """
    Notifica driver e operadores quando status da entrega muda.
    
    Args:
        delivery_data: dict com delivery_id, driver_id, status, etc.
    """
    driver_id = delivery_data.get("driver_id")
    
    # Notificar driver específico
    if driver_id:
        await manager.broadcast(
            message={
                "type": "delivery_updated",
                "data": delivery_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            filter_fn=lambda m: (
                m.user_role == UserRole.DRIVER and 
                str(m.user_id) == str(driver_id)
            )
        )
    
    # Notificar operadores e admins (monitoramento)
    await manager.broadcast(
        message={
            "type": "delivery_updated",
            "data": delivery_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        filter_fn=lambda m: m.user_role in [UserRole.ADMIN, UserRole.OPERATOR, UserRole.OWNER]
    )


async def emit_operator_message_to_driver(driver_id: str, message: str, from_user: str):
    """
    Envia mensagem do operador para o driver.
    
    Args:
        driver_id: ID do driver destinatário
        message: Texto da mensagem
        from_user: Nome do operador que enviou
    """
    await manager.broadcast(
        message={
            "type": "operator_message",
            "data": {
                "message": message,
                "from": from_user,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        filter_fn=lambda m: (
            m.user_role == UserRole.DRIVER and 
            str(m.user_id) == str(driver_id)
        )
    )
