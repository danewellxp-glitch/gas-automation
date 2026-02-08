from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.auth_models import User
from app.config import settings
from app.database import get_db

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

def credentials_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

def verify_password(plain_password, hashed_password):
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password using Argon2.
    
    Valida comprimento antes de hash para prevenir truncamento silencioso.
    """
    # Validar comprimento mínimo
    if len(password) < 8:
        raise ValueError("Senha deve ter no mínimo 8 caracteres")
    
    # Validar comprimento máximo (limite do Argon2)
    if len(password) > 72:
        raise ValueError(
            "Senha não pode ter mais de 72 caracteres "
            "(limitação do algoritmo Argon2)"
        )
    
    return pwd_context.hash(password)

async def authenticate_user(session: AsyncSession, username: str, password: str):
    """Authenticate a user by username and password"""
    result = await session.execute(
        # Aceita login por username OU email (melhora UX do frontend)
        select(User).where(or_(User.username == username, User.email == username))
    )
    user = result.scalar_one_or_none()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

async def create_user(session: AsyncSession, username: str, email: str, full_name: str, password: str, role: str = "user"):
    """Create a new user"""
    hashed_password = get_password_hash(password)
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        role=role,
        must_change_password=False,
        temp_password_issued_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_db)) -> User:
    """Get current user from JWT token"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token sem 'sub' (username)")
            raise credentials_exception()
    except JWTError as e:
        logger.warning(f"Erro ao decodificar JWT: {e}")
        raise credentials_exception()

    result = await session.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(f"Usuário não encontrado: {username}")
        raise credentials_exception()

    # Verificar se usuário está ativo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o administrador."
        )

    return user


async def get_current_user_ws(token: str, session: AsyncSession) -> Optional[User]:
    """
    Get current user from JWT token for WebSocket connections.
    Returns None if token is invalid or user is inactive.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    result = await session.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    # Verificar se usuário está ativo
    if user and not user.is_active:
        return None

    return user


# Import get_db from database module