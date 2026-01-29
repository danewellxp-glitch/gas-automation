"""
Admin System Health
Endpoint consolidado para status de serviços críticos.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict, Tuple

import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db, redis_manager
from app.integrations.waha import WAHAClient
from app.models.auth_models import User

router = APIRouter(prefix="/admin", tags=["Admin", "System"])

APP_STARTED_AT = time.time()


def _require_admin(user: User) -> None:
    if user.role != "admin":
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this resource",
        )


@router.get("/system-health")
async def system_health(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    _require_admin(current_user)

    now = datetime.now(timezone.utc).isoformat()
    health: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": now,
        "uptime_seconds": int(time.time() - APP_STARTED_AT),
        "services": {},
    }

    # ==================== Backend ====================
    health["services"]["backend"] = {"status": "online"}

    # ==================== Redis ====================
    redis_result: Dict[str, Any] = {}
    try:
        t0 = time.perf_counter()
        await redis_manager.client.ping()
        latency_ms = (time.perf_counter() - t0) * 1000.0
        info_memory = await redis_manager.client.info(section="memory")
        info_clients = await redis_manager.client.info(section="clients")

        redis_result.update(
            {
                "status": "online",
                "latency_ms": round(latency_ms, 2),
                "used_memory_bytes": info_memory.get("used_memory"),
                "used_memory_human": info_memory.get("used_memory_human"),
                "connected_clients": info_clients.get("connected_clients"),
            }
        )
    except Exception as e:
        health["status"] = "degraded"
        redis_result.update({"status": "offline", "error": str(e)})
    health["services"]["redis"] = redis_result

    # ==================== PostgreSQL ====================
    pg_result: Dict[str, Any] = {}
    try:
        await session.execute(text("SELECT 1"))
        active_conn = await session.execute(text("SELECT count(*) FROM pg_stat_activity"))
        active_connections = active_conn.scalar() or 0
        pg_result.update({"status": "online", "active_connections": int(active_connections)})
    except Exception as e:
        health["status"] = "degraded"
        pg_result.update({"status": "offline", "error": str(e)})
    health["services"]["postgres"] = pg_result

    # ==================== WAHA ====================
    waha_result: Dict[str, Any] = {}
    try:
        client = WAHAClient(timeout=10)
        status_data = await client.get_session_status()
        # tenta obter QR se desconectado (best-effort)
        qr_code: Optional[str] = None
        if isinstance(status_data, dict):
            st = (status_data.get("status") or "").lower()
            if st in ["disconnected", "stopped", "error", "auth_required"]:
                qr_code = await client.get_qr_code()
        waha_result.update(
            {
                "status": "online" if status_data.get("status") != "error" else "degraded",
                "session": status_data,
                "qr_code_base64": qr_code,
            }
        )
    except Exception as e:
        health["status"] = "degraded"
        waha_result.update({"status": "offline", "error": str(e)})
    health["services"]["waha"] = waha_result

    # ==================== Firebird Sync Service ====================
    sync_result: Dict[str, Any] = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.sync_service_url.rstrip('/')}/status")
            resp.raise_for_status()
            data = resp.json()
            sync_result.update({"status": "online", "data": data})
    except Exception as e:
        health["status"] = "degraded"
        sync_result.update({"status": "offline", "error": str(e)})
    health["services"]["firebird_sync"] = sync_result

    return health

