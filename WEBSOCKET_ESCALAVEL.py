"""
SOLUÇÃO DE ESCALABILIDADE - WebSocket para 9000+ pedidos/semana

Este arquivo contém implementações prontas das 3 soluções críticas:
1. Filtrar broadcast por papel/permissão
2. Rate limiting de eventos
3. Heartbeat para limpar conexões mortas
"""

import asyncio
import json
import logging
from typing import Set, Callable, Optional, Dict
from datetime import datetime, timezone, timedelta
from enum import Enum

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """Papéis de usuário do sistema"""
    ADMIN = "admin"
    OPERATOR = "operator"
    OWNER = "owner"
    MANAGER = "manager"


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
    """

    def __init__(self, max_broadcasts_per_second: int = 10):
        # Conexões agrupadas por user_id (para deduplicação)
        self.connections: Dict[str, Set[ConnectionMetadata]] = {}
        self.max_broadcasts_per_second = max_broadcasts_per_second
        self.broadcast_timestamps: list = []  # Para rate limiting
        self.heartbeat_timeout_seconds = 300  # 5 minutos

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

    async def broadcast(self, message: dict, filter_fn: Optional[Callable] = None):
        """
        Envia mensagem com filtro opcional e rate limiting.
        
        Args:
            message: Mensagem a enviar
            filter_fn: Função de filtro que retorna True se deve enviar
                       Exemplo: lambda metadata: metadata.user_role == "admin"
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
        
        # Coletar todas as conexões a notificar
        connections_to_notify = []
        for user_connections in self.connections.values():
            for metadata in user_connections:
                if filter_fn is None or filter_fn(metadata):
                    connections_to_notify.append(metadata)
        
        if not connections_to_notify:
            logger.debug(f"Nenhuma conexão correspondeu ao filtro")
            return
        
        # Enviar para todas as conexões que passaram no filtro
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        logger.debug(
            f"Broadcasting '{message.get('type')}' para "
            f"{len(connections_to_notify)} conexões"
        )
        
        for metadata in connections_to_notify:
            try:
                await metadata.websocket.send_text(message_json)
                metadata.last_heartbeat = datetime.now(timezone.utc)
            except Exception as e:
                logger.warning(f"Erro ao enviar para {metadata.user_id}: {e}")
                disconnected.append((metadata.user_id, metadata.websocket))
        
        # Remover conexões que falharam
        for user_id, websocket in disconnected:
            self.disconnect(websocket, user_id)

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
        """Envia apenas para operadores de um bairro específico"""
        await self.broadcast(
            message,
            filter_fn=lambda metadata: (
                metadata.user_role == UserRole.ADMIN or  # Admin vê tudo
                (metadata.user_role == UserRole.OPERATOR and metadata.bairro == bairro)
            )
        )

    async def broadcast_to_region(self, message: dict, region: str):
        """Envia apenas para managers de uma região específica"""
        await self.broadcast(
            message,
            filter_fn=lambda metadata: (
                metadata.user_role == UserRole.ADMIN or
                (metadata.user_role == UserRole.MANAGER and metadata.region == region)
            )
        )

    async def heartbeat_monitor(self):
        """
        Monitor de heartbeat - remove conexões mortas.
        Execute com: asyncio.create_task(manager.heartbeat_monitor())
        """
        logger.info("Iniciando monitor de heartbeat")
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
                            except:
                                pass
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
                logger.info(
                    f"Heartbeat monitor: {len(self.connections)} usuários ativos, "
                    f"{total_connections} conexões"
                )
            except Exception as e:
                logger.error(f"Erro no heartbeat monitor: {e}", exc_info=True)


# ============ EXEMPLO DE USO ==============

"""
# No seu arquivo websocket.py, substitua:

# ❌ ANTES (Ineficiente)
manager = ConnectionManager()

# ✅ DEPOIS (Escalável)
manager = ScalableConnectionManager(max_broadcasts_per_second=10)

# Na rota WebSocket, extrair dados do token:
@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    # Extrair user_id, role, bairro do token JWT
    user_id = payload.get("sub")
    user_role = UserRole(payload.get("role", "operator"))
    bairro = payload.get("bairro")
    
    await manager.connect(websocket, user_id, user_role, bairro)
    
    # Iniciar heartbeat (uma vez)
    asyncio.create_task(manager.heartbeat_monitor())
    
    try:
        while True:
            data = await websocket.receive_text()
            # Processar dados...
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# Usar os novos broadcasts:

# Enviar apenas para admins
await manager.broadcast_to_admin_only({
    "type": "new_order",
    "data": order_data
})

# Enviar apenas para operadores de um bairro
await manager.broadcast_to_neighborhood({
    "type": "new_order",
    "data": order_data
}, bairro="Vila Mariana")

# Enviar apenas para managers de uma região
await manager.broadcast_to_region({
    "type": "new_order",
    "data": order_data
}, region="São Paulo")

# Enviar com filtro customizado
await manager.broadcast({
    "type": "new_order",
    "data": order_data
}, filter_fn=lambda m: m.user_role in [UserRole.ADMIN, UserRole.OWNER])
"""
