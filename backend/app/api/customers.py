"""
API de Clientes.
"""

from typing import Optional, List, Dict, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import Customer
from app.models.auth_models import User
from app.auth import get_current_user
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate

router = APIRouter()


@router.get("", response_model=List[CustomerResponse])
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None, description="Buscar por nome ou telefone"),
    phone: Optional[str] = Query(None, description="Buscar por telefone exato"),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os clientes."""
    query = select(Customer).order_by(Customer.created_at.desc())

    # Busca exata por telefone tem prioridade
    if phone:
        cleaned_phone = "".join(filter(str.isdigit, phone))
        query = query.where(Customer.phone == cleaned_phone)
    elif search:
        query = query.where(
            (Customer.name.ilike(f"%{search}%")) | (Customer.phone.contains(search))
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Busca cliente por ID."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return customer


@router.get("/phone/{phone}", response_model=CustomerResponse)
async def get_customer_by_phone(
    phone: str,
    db: AsyncSession = Depends(get_db),
):
    """Busca cliente por telefone."""
    # Limpa o telefone
    cleaned = "".join(filter(str.isdigit, phone))

    result = await db.execute(select(Customer).where(Customer.phone == cleaned))
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return customer


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria um novo cliente."""
    # Verifica se já existe
    result = await db.execute(select(Customer).where(Customer.phone == data.phone))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Cliente já existe com este telefone")

    customer = Customer(
        phone=data.phone,
        name=data.name,
        email=data.email,
        cpf_cnpj=data.cpf_cnpj,
        address=data.address.model_dump() if data.address else None,
        notes=data.notes,
    )

    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza um cliente."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "address" and value:
            value = value.model_dump() if hasattr(value, "model_dump") else value
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)

    return customer


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove um cliente."""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    await db.delete(customer)
    await db.commit()
