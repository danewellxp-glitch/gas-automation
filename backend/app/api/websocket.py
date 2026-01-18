"""
WebSocket para atualizações em tempo real.
"""

import asyncio
import json
import logging
from typing import Set
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Gerencia conexões WebSocket ativas."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Aceita nova conexão WebSocket."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove conexão WebSocket."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket desconectado. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Envia mensagem para todas as conexões ativas."""
        if not self.active_connections:
            return

        message_json = json.dumps(message, default=str)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Erro ao enviar mensagem WebSocket: {e}")
                disconnected.add(connection)

        # Remove conexões que falharam
        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Envia mensagem para uma conexão específica."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.warning(f"Erro ao enviar mensagem pessoal: {e}")


# Instância global
manager = ConnectionManager()


@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    WebSocket para atualizações do dashboard em tempo real.

    Eventos enviados:
    - new_order: Novo pedido criado
    - order_update: Status do pedido atualizado
    - new_message: Nova mensagem WhatsApp
    - metrics_update: Métricas atualizadas
    """
    await manager.connect(websocket)

    # Enviar estado inicial
    await manager.send_personal(websocket, {
        "type": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Conectado ao dashboard em tempo real",
    })

    try:
        while True:
            # Manter conexão ativa e processar mensagens do cliente
            data = await websocket.receive_text()

            # Processar comandos do cliente (se necessário)
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await manager.send_personal(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Funções para emitir eventos de outras partes do sistema

async def emit_new_order(order_data: dict):
    """Emite evento de novo pedido."""
    await manager.broadcast({
        "type": "new_order",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": order_data,
    })


async def emit_order_update(order_id: str, status: str, order_data: dict = None):
    """Emite evento de atualização de pedido."""
    await manager.broadcast({
        "type": "order_update",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "order_id": order_id,
            "status": status,
            "order": order_data,
        },
    })


async def emit_new_message(phone: str, message: str, direction: str = "incoming"):
    """Emite evento de nova mensagem WhatsApp."""
    await manager.broadcast({
        "type": "new_message",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "phone": phone,
            "message": message,
            "direction": direction,
        },
    })


async def emit_metrics_update(metrics: dict):
    """Emite atualização de métricas."""
    await manager.broadcast({
        "type": "metrics_update",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": metrics,
    })
