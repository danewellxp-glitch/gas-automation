"""
Schemas de autenticação.
"""

from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator


class UserCreate(BaseModel):
    """Schema para criar usuário."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=8, max_length=72)
    role: Optional[str] = Field("user", regex="^(admin|operator|owner|manager|user|driver)$")
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Valida força da senha."""
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        
        if len(v) > 72:
            raise ValueError("Senha não pode ter mais de 72 caracteres")
        
        # Validar complexidade
        if not any(c.isupper() for c in v):
            raise ValueError("Senha deve conter pelo menos uma letra maiúscula")
        
        if not any(c.islower() for c in v):
            raise ValueError("Senha deve conter pelo menos uma letra minúscula")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Senha deve conter pelo menos um número")
        
        # Opcional: caractere especial
        # if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
        #     raise ValueError("Senha deve conter pelo menos um caractere especial")
        
        return v


class UserResponse(BaseModel):
    """Schema de resposta de usuário."""
    
    id: int
    username: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema de token JWT."""
    
    access_token: str
    token_type: str = "bearer"
    role: Optional[str] = None
    email: Optional[str] = None


class TokenData(BaseModel):
    """Dados contidos no token."""
    
    username: Optional[str] = None
