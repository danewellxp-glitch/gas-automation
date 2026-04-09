"""
Model: ProductPriceHistory
Registra o histórico de alterações de preço dos produtos.

Destino: app/models/product_price_history.py
"""

from sqlalchemy import Column, DateTime, Integer, Numeric, String, func

from app.models.base import Base


class ProductPriceHistory(Base):
    """
    Histórico de preços de produtos.

    Cada linha representa uma alteração de preço: guarda o preço anterior,
    o novo preço, quando ocorreu e quem fez a alteração.
    """

    __tablename__ = "product_price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Referência ao produto (por código, não FK, para evitar cascata)
    product_code = Column(String(50), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)

    # Preços
    old_price = Column(Numeric(10, 2), nullable=False)
    new_price = Column(Numeric(10, 2), nullable=False)

    # Auditoria
    changed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    changed_by = Column(String(200), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ProductPriceHistory product={self.product_code} "
            f"{self.old_price}→{self.new_price} at={self.changed_at}>"
        )
