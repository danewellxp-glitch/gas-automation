"""
Serviços para Central de Erros (ErrorEvent).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_event import ErrorEvent


def make_fingerprint(*, service: str, error_type: str, message: str) -> str:
    raw = f"{service}|{error_type}|{message}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:32]


async def upsert_error_event(
    session: AsyncSession,
    *,
    service: str,
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> ErrorEvent:
    fp = make_fingerprint(service=service, error_type=error_type, message=message)
    now = datetime.now(timezone.utc)

    res = await session.execute(select(ErrorEvent).where(ErrorEvent.fingerprint == fp))
    existing = res.scalar_one_or_none()
    if existing:
        existing.count = int(existing.count or 0) + 1
        existing.last_seen = now
        # se estava known/incident, não mexer; se open, manter open
        if details:
            existing.details_json = details
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return existing

    ev = ErrorEvent(
        service=service,
        error_type=error_type,
        fingerprint=fp,
        message=message[:500],
        details_json=details,
        count=1,
        first_seen=now,
        last_seen=now,
        status="open",
    )
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return ev

