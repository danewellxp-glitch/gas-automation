"""
Admin Users API
- CRUD de usuários (admin-only)
- Criação com senha temporária (troca obrigatória no 1º login)
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field as PydField
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth import get_current_user, get_password_hash
from app.database import get_db
from app.models.auth_models import AuditLog, User

router = APIRouter(prefix="/admin/users", tags=["Admin", "Users"])


def _require_admin(current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this resource",
        )


def _generate_temporary_password(length: int = 12) -> str:
    # 12+ caracteres, sem caracteres ambíguos (0/O, 1/l)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _write_audit_log(
    session: AsyncSession,
    *,
    action: str,
    actor_user_id: Optional[int],
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    audit = AuditLog(
        action=action,
        user_id=actor_user_id,
        details=details,
        timestamp=datetime.utcnow(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(audit)
    await session.commit()


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime


class CreateUserRequest(BaseModel):
    username: str = PydField(min_length=3, max_length=64)
    email: str
    full_name: str = PydField(min_length=1, max_length=120)
    role: str = "user"
    is_active: bool = True


class CreateUserResponse(BaseModel):
    user: AdminUserResponse
    temporary_password: str


class UpdateUserRequest(BaseModel):
    username: Optional[str] = PydField(default=None, min_length=3, max_length=64)
    email: Optional[str] = None
    full_name: Optional[str] = PydField(default=None, min_length=1, max_length=120)
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordResponse(BaseModel):
    user_id: int
    temporary_password: str


@router.post("", response_model=CreateUserResponse)
async def admin_create_user(
    body: CreateUserRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    request: Request = None,
):
    _require_admin(current_user)

    # validar role
    valid_roles = ["admin", "operator", "owner", "user", "driver"]
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {', '.join(valid_roles)}",
        )

    # checar duplicidade username/email
    res = await session.execute(select(User).where(User.username == body.username))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    if "@" not in body.email:
        raise HTTPException(status_code=400, detail="Invalid email")

    res = await session.execute(select(User).where(User.email == body.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    temporary_password = _generate_temporary_password()

    user = User(
        username=body.username,
        email=str(body.email),
        full_name=body.full_name,
        hashed_password=get_password_hash(temporary_password),
        role=body.role,
        is_active=body.is_active,
        must_change_password=True,
        temp_password_issued_at=datetime.utcnow(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    await _write_audit_log(
        session,
        action="USER_CREATE",
        actor_user_id=current_user.id,
        details=f"Created user_id={user.id} role={user.role}",
        ip_address=(request.headers.get("x-forwarded-for", "").split(",")[0].strip() if request else None)
        or (request.client.host if request and request.client else None),
        user_agent=request.headers.get("user-agent") if request else None,
    )

    return {
        "user": AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
        "temporary_password": temporary_password,
    }


@router.put("/{user_id}", response_model=AdminUserResponse)
async def admin_update_user(
    user_id: int,
    body: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    request: Request = None,
):
    _require_admin(current_user)

    res = await session.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # admin não pode alterar a própria role (mantendo regra existente)
    if body.role is not None and current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot modify your own role")

    if body.role is not None:
        valid_roles = ["admin", "operator", "owner", "user", "driver"]
        if body.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Valid roles: {', '.join(valid_roles)}",
            )
        user.role = body.role

    if body.username is not None and body.username != user.username:
        res = await session.execute(select(User).where(User.username == body.username))
        if res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already registered")
        user.username = body.username

    if body.email is not None and str(body.email) != user.email:
        if "@" not in body.email:
            raise HTTPException(status_code=400, detail="Invalid email")

        res = await session.execute(select(User).where(User.email == body.email))
        if res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = str(body.email)

    if body.full_name is not None:
        user.full_name = body.full_name

    if body.is_active is not None:
        user.is_active = body.is_active

    user.updated_at = datetime.now()
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await _write_audit_log(
        session,
        action="USER_UPDATE",
        actor_user_id=current_user.id,
        details=f"Updated user_id={user.id}",
        ip_address=(request.headers.get("x-forwarded-for", "").split(",")[0].strip() if request else None)
        or (request.client.host if request and request.client else None),
        user_agent=request.headers.get("user-agent") if request else None,
    )

    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def admin_reset_password(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    request: Request = None,
):
    _require_admin(current_user)

    res = await session.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    temporary_password = _generate_temporary_password()
    user.hashed_password = get_password_hash(temporary_password)
    user.must_change_password = True
    user.temp_password_issued_at = datetime.utcnow()
    user.updated_at = datetime.now()

    session.add(user)
    await session.commit()
    await session.refresh(user)

    await _write_audit_log(
        session,
        action="PASSWORD_RESET",
        actor_user_id=current_user.id,
        details=f"Reset password for user_id={user.id}",
        ip_address=(request.headers.get("x-forwarded-for", "").split(",")[0].strip() if request else None)
        or (request.client.host if request and request.client else None),
        user_agent=request.headers.get("user-agent") if request else None,
    )

    return {"user_id": user.id, "temporary_password": temporary_password}

