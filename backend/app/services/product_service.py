"""
Product Service - Gerenciamento de Produtos
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product


class ProductService:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> List[Product]:
        """Lista todos os produtos"""
        return self.session.exec(select(Product)).all()

    def list_available(self) -> List[Product]:
        """Lista produtos disponíveis em estoque"""
        return self.session.exec(
            select(Product).where(
                Product.active == True,
                Product.stock_quantity > 0
            )
        ).all()

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Busca produto por ID"""
        return self.session.get(Product, product_id)

    def create(self, **data) -> Product:
        """Cria novo produto"""
        product = Product(**data)
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return product

    def update(self, product_id: int, **data) -> Optional[Product]:
        """Atualiza produto"""
        product = self.get_by_id(product_id)
        if not product:
            return None

        for key, value in data.items():
            setattr(product, key, value)

        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return product

    def delete(self, product_id: int) -> bool:
        """Remove produto (soft delete)"""
        product = self.get_by_id(product_id)
        if not product:
            return False

        product.active = False
        self.session.add(product)
        self.session.commit()
        return True

    # REMOVIDO: create_default_products
    # Produtos devem ser sincronizados do Firebird (Gerente.fdb)
    # Usar script de sincronização: backend/scripts/sync_products_from_firebird.py