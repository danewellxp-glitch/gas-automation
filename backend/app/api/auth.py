from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.auth import authenticate_user, create_access_token, get_current_user, create_user, verify_password, get_password_hash
from app.models.auth_models import User
from app.config import settings

router = APIRouter()

# Configurar limiter para este router
limiter = Limiter(key_func=get_remote_address)

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: Optional[str] = "user"

class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    must_change_password: Optional[bool] = False

class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = "operator"
    email: Optional[str] = None
    must_change_password: Optional[bool] = False
    user: Optional[UserInfo] = None

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")  # 5 tentativas por minuto
async def login_by_email(
    request: Request,
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_db)
):
    """Login endpoint using email and password"""
    # Find user by email
    stmt = select(User).where(User.email == credentials.email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Verify password
    from app.auth import verify_password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Create token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "email": user.email,
        "must_change_password": getattr(user, "must_change_password", False),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "must_change_password": getattr(user, "must_change_password", False),
        }
    }

@router.post("/register", response_model=Token)
@limiter.limit("3/hour")  # 3 registros por hora
async def register_user(
    request: Request,
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # Check if user already exists
    result = await session.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Create user
    user = await create_user(
        session=session,
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        password=user_data.password,
        role=user_data.role
    )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
@limiter.limit("5/minute")  # 5 tentativas por minuto
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db)
):
    """Login endpoint"""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "email": user.email,
        "must_change_password": getattr(user, "must_change_password", False),
    }

class UserMeResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@router.get("/users/me", response_model=UserMeResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information (sem expor hashed_password)"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "must_change_password": getattr(current_user, "must_change_password", False),
        "created_at": current_user.created_at.isoformat() if getattr(current_user, "created_at", None) else None,
        "updated_at": current_user.updated_at.isoformat() if getattr(current_user, "updated_at", None) else None,
    }

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Troca senha do usuário autenticado.
    Usado para fluxo de senha temporária (troca obrigatória no 1º login).
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual inválida")

    # get_password_hash já valida min/max
    current_user.hashed_password = get_password_hash(body.new_password)
    current_user.must_change_password = False
    current_user.temp_password_issued_at = None
    current_user.updated_at = datetime.utcnow()

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return {"message": "Senha alterada com sucesso"}

@router.put("/users/me")
async def update_user(
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Update current user information"""
    if full_name:
        current_user.full_name = full_name
    if email:
        current_user.email = email

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return {"message": "User updated successfully"}


@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Gera novo access token para usuario autenticado.

    O usuario deve enviar o token atual no header Authorization.
    Se o token ainda for valido, um novo token e gerado.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario desativado"
        )

    # Criar novo token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    new_access_token = create_access_token(
        data={"sub": current_user.username},
        expires_delta=access_token_expires
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "role": current_user.role,
        "email": current_user.email
    }