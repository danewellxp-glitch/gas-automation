"""
Customer Service - Gerenciamento de Clientes
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


class CustomerService:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> List[Customer]:
        """Lista todos os clientes"""
        return self.session.exec(select(Customer)).all()

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        """Busca cliente por ID"""
        return self.session.get(Customer, customer_id)

    def get_by_phone(self, phone: str) -> Optional[Customer]:
        """Busca cliente por telefone (com limpeza automática)"""
        # Limpa telefone removendo caracteres especiais
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        return self.session.exec(
            select(Customer).where(Customer.phone == clean_phone)
        ).first()

    def create(self, **data) -> Customer:
        """Cria novo cliente"""
        # Limpa telefone se fornecido
        if 'phone' in data and data['phone']:
            data['phone'] = data['phone'].replace("+", "").replace(" ", "").replace("-", "")

        customer = Customer(**data)
        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def update(self, customer_id: int, **data) -> Optional[Customer]:
        """Atualiza cliente"""
        customer = self.get_by_id(customer_id)
        if not customer:
            return None

        for key, value in data.items():
            setattr(customer, key, value)

        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def delete(self, customer_id: int) -> bool:
        """Remove cliente"""
        customer = self.get_by_id(customer_id)
        if not customer:
            return False

        self.session.delete(customer)
        self.session.commit()
        return True

    def get_or_create(self, phone: str, name: str = "Cliente") -> tuple[Customer, bool]:
        """Busca cliente ou cria um novo básico

        Returns:
            tuple: (customer, created) - customer é o objeto, created é True se foi criado agora
        """
        customer = self.get_by_phone(phone)
        if customer:
            return customer, False

        # Cria cliente básico (sem endereço completo ainda)
        customer = Customer(
            name=name,
            phone=phone.replace("+", "").replace(" ", "").replace("-", ""),
            address="A definir",
            neighborhood="A definir",
        )
        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer, True