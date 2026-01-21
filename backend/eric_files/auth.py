# -*- coding: utf-8 -*-
"""
Módulo centralizado de autenticação JWT
Todas as funções de auth devem ser importadas daqui
"""
from datetime import timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlmodel import Session, select
import jwt
from jwt import InvalidTokenError, DecodeError

from backend.models import User, brazilian_now
from backend.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, engine

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_session():
    """Dependency para obter sessão do banco de dados"""
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def hash_password(password: str) -> str:
    """Hash de senha usando bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha plain corresponde ao hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Cria um access token JWT

    Args:
        data: Dados para incluir no payload (geralmente {"sub": email})
        expires_delta: Tempo de expiração customizado (opcional)

    Returns:
        Token JWT encoded
    """
    to_encode = data.copy()
    expire = brazilian_now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Cria um refresh token JWT (validade maior)

    Args:
        data: Dados para incluir no payload (geralmente {"sub": email})

    Returns:
        Refresh token JWT encoded
    """
    to_encode = data.copy()
    expire = brazilian_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodifica e valida um token JWT

    Args:
        token: Token JWT para decodificar

    Returns:
        Payload do token

    Raises:
        HTTPException: Se token for inválido ou expirado
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (InvalidTokenError, DecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    """
    Dependency para obter o usuário atual a partir do token JWT

    Args:
        token: Token JWT do header Authorization
        session: Sessão do banco de dados

    Returns:
        User: Objeto do usuário autenticado

    Raises:
        HTTPException: Se token inválido ou usuário não encontrado/desativado
    """
    payload = decode_token(token)

    email = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: email não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado. Contate o administrador."
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency para garantir que o usuário está ativo"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário desativado"
        )
    return current_user


def require_role(allowed_roles: list):
    """
    Dependency factory para verificar role do usuário

    Args:
        allowed_roles: Lista de roles permitidas (ex: ["admin", "owner"])

    Returns:
        Dependency function que verifica a role

    Example:
        @app.get("/admin/users")
        def list_users(user: User = Depends(require_role(["admin", "owner"]))):
            ...
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Requer role: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


# Shortcuts para roles comuns
require_admin = require_role(["admin", "owner"])
require_owner = require_role(["owner"])
require_operador = require_role(["admin", "owner", "operador"])


def validate_refresh_token(refresh_token: str, session: Session) -> User:
    """
    Valida um refresh token e retorna o usuário

    Args:
        refresh_token: Token de refresh para validar
        session: Sessão do banco de dados

    Returns:
        User: Usuário associado ao token

    Raises:
        HTTPException: Se token inválido ou não for do tipo refresh
    """
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: não é um refresh token"
        )

    email = payload.get("sub")
    user = session.exec(select(User).where(User.email == email)).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou desativado"
        )

    return user
