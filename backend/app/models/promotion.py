"""
Modelo de Promoção.

Sistema de cupons e descontos.
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Promotion(BaseModel):
    """
    Modelo de Promoção/Cupom.
    
    Attributes:
        code: Código do cupom (ex: DESCONTO10)
        name: Nome da promoção
        description: Descrição detalhada
        discount_type: Tipo de desconto (percentage ou fixed)
        discount_value: Valor do desconto (percentual ou valor fixo)
        min_order_value: Valor mínimo do pedido para aplicar
        max_discount: Desconto máximo (para percentual)
        usage_limit: Limite de usos totais
        usage_count: Quantidade de vezes usado
        valid_from: Data de início da validade
        valid_until: Data de fim da validade
        is_active: Se está ativa
        applies_to_all_products: Se aplica a todos os produtos
    """
    
    __tablename__ = "promotions"
    
    # Código do cupom (único)
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Código do cupom (ex: DESCONTO10)"
    )
    
    # Informações
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Nome da promoção"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Descrição detalhada"
    )
    
    # Tipo e valor do desconto
    discount_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="percentage",
        comment="Tipo: percentage ou fixed"
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Valor do desconto (percentual ou valor fixo)"
    )
    min_order_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Valor mínimo do pedido para aplicar"
    )
    max_discount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Desconto máximo (para percentual)"
    )
    
    # Limites de uso
    usage_limit: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Limite de usos totais (None = ilimitado)"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Quantidade de vezes usado"
    )
    
    # Validade
    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Data de início da validade"
    )
    valid_until: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Data de fim da validade"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Se está ativa"
    )
    
    # Aplicação
    applies_to_all_products: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Se aplica a todos os produtos"
    )
    
    # Índices
    __table_args__ = (
        Index("ix_promotions_code_active", "code", "is_active"),
        Index("ix_promotions_validity", "valid_from", "valid_until"),
    )
    
    def is_valid(self, order_value: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Verifica se a promoção é válida para um pedido.
        
        Args:
            order_value: Valor total do pedido
            
        Returns:
            Tupla (is_valid, error_message)
        """
        # Verificar se está ativa
        if not self.is_active:
            return False, "Promoção não está ativa"
        
        # Verificar validade
        today = date.today()
        if today < self.valid_from:
            return False, "Promoção ainda não está válida"
        
        if self.valid_until and today > self.valid_until:
            return False, "Promoção expirada"
        
        # Verificar limite de uso
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False, "Limite de usos atingido"
        
        # Verificar valor mínimo
        if self.min_order_value and order_value < self.min_order_value:
            return False, f"Valor mínimo do pedido: R$ {self.min_order_value:.2f}"
        
        return True, None
    
    def calculate_discount(self, order_value: Decimal) -> Decimal:
        """
        Calcula o valor do desconto para um pedido.
        
        Args:
            order_value: Valor total do pedido
            
        Returns:
            Valor do desconto
        """
        if self.discount_type == "percentage":
            discount = order_value * (self.discount_value / Decimal("100"))
            
            # Aplicar desconto máximo se definido
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            # Desconto fixo
            discount = self.discount_value
        
        # Não permitir desconto maior que o valor do pedido
        discount = min(discount, order_value)
        
        return discount.quantize(Decimal("0.01"))
    
    def __repr__(self) -> str:
        return f"<Promotion(code={self.code}, discount={self.discount_value}%)>"