from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel

from app.database import get_db
from app.auth import authenticate_user, create_access_token, get_current_user, create_user
from app.models.auth_models import User
from app.config import settings

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: Optional[str] = "user"

class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = "operator"
    email: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login", response_model=Token)
async def login_by_email(
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
        "email": user.email
    }

@router.post("/register", response_model=Token)
async def register_user(
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
async def login_for_access_token(
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
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

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