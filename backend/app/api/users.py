"""Users API endpoints for role management and audit logs"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc
from sqlmodel import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.auth_models import User, AuditLog
from app.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UpdateRoleRequest(BaseModel):
    role: str

@router.get("", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """List all users (admin and owner only)"""
    # Verificar se é admin ou owner
    if current_user.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and owners can list users"
        )
    
    stmt = select(User).order_by(User.created_at.desc())
    result = await session.execute(stmt)
    users = result.scalars().all()
    
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            username=u.username,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=getattr(u, "created_at", None),
            updated_at=getattr(u, "updated_at", None),
        )
        for u in users
    ]

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=getattr(current_user, "created_at", None),
        updated_at=getattr(current_user, "updated_at", None),
    )

@router.put("/{user_id}/role")
async def update_user_role(
    user_id: int,
    request: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Update user role (admin only)"""
    # Verificar se é admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update user roles"
        )
    
    # Não permitir editar a própria role
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot modify your own role"
        )
    
    # Validar role
    valid_roles = ["admin", "operator", "owner", "user"]
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {', '.join(valid_roles)}"
        )
    
    # Encontrar usuário
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Atualizar role
    user.role = request.role
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return {
        "message": "Role updated successfully",
        "user": UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=getattr(user, "created_at", None),
            updated_at=getattr(user, "updated_at", None),
        )
    }

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get user details"""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Apenas admin ou o próprio usuário pode ver os detalhes
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=getattr(user, "created_at", None),
        updated_at=getattr(user, "updated_at", None),
    )


# ==================== AUDIT LOGS ====================

class AuditLogResponse(BaseModel):
    id: int
    action: str
    user_id: Optional[int]
    conversation_id: Optional[int]
    details: Optional[str]
    timestamp: datetime
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/audit-logs", response_model=List[AuditLogResponse], tags=["audit"])
async def list_audit_logs(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Lista logs de auditoria (admin/owner only).

    Retorna acoes realizadas no sistema como:
    - LOGIN, LOGOUT
    - USER_CREATE, USER_UPDATE, USER_DELETE
    - ROLE_CHANGE
    - PASSWORD_RESET
    """
    if current_user.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins e owners podem acessar logs de auditoria"
        )

    stmt = (
        select(AuditLog)
        .order_by(desc(AuditLog.timestamp))
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    logs = result.scalars().all()

    # Buscar emails dos usuarios
    response = []
    for log in logs:
        user_email = None
        if log.user_id:
            user_result = await session.execute(
                select(User).where(User.id == log.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user_email = user.email

        response.append(AuditLogResponse(
            id=log.id,
            action=log.action,
            user_id=log.user_id,
            conversation_id=log.conversation_id,
            details=log.details,
            timestamp=log.timestamp,
            user_email=user_email
        ))

    return response


async def create_audit_log(
    session: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    conversation_id: Optional[int] = None,
    details: Optional[str] = None
):
    """Helper para criar log de auditoria"""
    audit = AuditLog(
        action=action,
        user_id=user_id,
        conversation_id=conversation_id,
        details=details,
        timestamp=datetime.now()
    )
    session.add(audit)
    await session.commit()
    return audit
