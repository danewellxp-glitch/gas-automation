"""
Admin Errors API
Central de Logs & Erros (baseado em banco).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth import get_current_user
from app.database import get_db
from app.models.auth_models import User
from app.models.error_event import ErrorEvent

router = APIRouter(prefix="/admin/errors", tags=["Admin", "Errors"])


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this resource")


class ErrorEventResponse(BaseModel):
    id: int
    service: str
    error_type: str
    fingerprint: str
    message: str
    count: int
    first_seen: datetime
    last_seen: datetime
    status: str
    known_reason: Optional[str] = None
    incident_title: Optional[str] = None
    incident_id: Optional[str] = None


class MarkKnownRequest(BaseModel):
    known_reason: str


class CreateIncidentRequest(BaseModel):
    incident_title: str
    incident_id: Optional[str] = None


@router.get("", response_model=list[ErrorEventResponse])
async def list_errors(
    service: Optional[str] = None,
    error_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    q: Optional[str] = None,
    since_hours: Optional[int] = 72,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    where = []
    if service:
        where.append(ErrorEvent.service == service)
    if error_type:
        where.append(ErrorEvent.error_type == error_type)
    if status_filter:
        where.append(ErrorEvent.status == status_filter)
    if q:
        where.append(ErrorEvent.message.ilike(f"%{q}%"))
    if since_hours is not None:
        since_dt = datetime.now(timezone.utc) - timedelta(hours=int(since_hours))
        where.append(ErrorEvent.last_seen >= since_dt)

    stmt = select(ErrorEvent)
    if where:
        stmt = stmt.where(and_(*where))
    stmt = stmt.order_by(desc(ErrorEvent.last_seen)).offset(offset).limit(limit)

    res = await session.execute(stmt)
    rows = res.scalars().all()

    return [
        ErrorEventResponse(
            id=r.id,
            service=r.service,
            error_type=r.error_type,
            fingerprint=r.fingerprint,
            message=r.message,
            count=r.count,
            first_seen=r.first_seen,
            last_seen=r.last_seen,
            status=r.status,
            known_reason=r.known_reason,
            incident_title=r.incident_title,
            incident_id=r.incident_id,
        )
        for r in rows
    ]


@router.get("/{error_id}")
async def get_error_details(
    error_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    res = await session.execute(select(ErrorEvent).where(ErrorEvent.id == error_id))
    ev = res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Error not found")
    return {
        "id": ev.id,
        "service": ev.service,
        "error_type": ev.error_type,
        "fingerprint": ev.fingerprint,
        "message": ev.message,
        "details_json": ev.details_json,
        "count": ev.count,
        "first_seen": ev.first_seen,
        "last_seen": ev.last_seen,
        "status": ev.status,
        "known_reason": ev.known_reason,
        "incident_title": ev.incident_title,
        "incident_id": ev.incident_id,
    }


@router.post("/{error_id}/mark-known")
async def mark_known(
    error_id: int,
    body: MarkKnownRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    res = await session.execute(select(ErrorEvent).where(ErrorEvent.id == error_id))
    ev = res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Error not found")
    ev.status = "known"
    ev.known_reason = body.known_reason
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return {"message": "Marked as known", "id": ev.id}


@router.post("/{error_id}/create-incident")
async def create_incident(
    error_id: int,
    body: CreateIncidentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    res = await session.execute(select(ErrorEvent).where(ErrorEvent.id == error_id))
    ev = res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Error not found")
    ev.status = "incident"
    ev.incident_title = body.incident_title
    ev.incident_id = body.incident_id
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return {"message": "Incident created", "id": ev.id}

