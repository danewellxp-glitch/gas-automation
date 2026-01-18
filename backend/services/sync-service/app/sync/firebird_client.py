"""
Cliente Firebird para conexão com sistema legado.
"""

import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

# Firebird SDK é opcional
try:
    import fdb
    FIREBIRD_AVAILABLE = True
except ImportError:
    FIREBIRD_AVAILABLE = False
    logger.warning("FDB (Firebird) não instalado")


class FirebirdClient:
    """
    Cliente para conexão com banco Firebird (sistema legado).

    Usado para:
    - Importar produtos e preços
    - Importar clientes existentes
    - Exportar pedidos para faturamento
    - Consultar estoque
    """

    def __init__(self):
        self._connection = None

    @property
    def is_available(self) -> bool:
        """Verifica se Firebird está disponível e configurado."""
        return FIREBIRD_AVAILABLE and settings.firebird_enabled

    @contextmanager
    def get_connection(self):
        """Context manager para conexão Firebird."""
        if not self.is_available:
            raise RuntimeError("Firebird não disponível ou não configurado")

        conn = None
        try:
            conn = fdb.connect(
                dsn=settings.firebird_dsn,
                user=settings.firebird_user,
                password=settings.firebird_password,
                charset=settings.firebird_charset,
            )
            yield conn
        finally:
            if conn:
                conn.close()

    def test_connection(self) -> bool:
        """Testa conexão com Firebird."""
        if not self.is_available:
            return False

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM RDB$DATABASE")
                cursor.fetchone()
                return True
        except Exception as e:
            logger.error(f"Erro ao testar conexão Firebird: {e}")
            return False

    # ==================== Produtos ====================

    def get_products(self, updated_after: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Busca produtos do sistema legado.

        Args:
            updated_after: Filtrar apenas alterados após esta data

        Returns:
            Lista de produtos com campos mapeados
        """
        if not self.is_available:
            return []

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Query exemplo - ajustar conforme schema do Firebird
                query = """
                    SELECT
                        CODIGO,
                        DESCRICAO,
                        PRECO_VENDA,
                        PESO,
                        ESTOQUE_ATUAL,
                        ATIVO,
                        DATA_ALTERACAO
                    FROM PRODUTOS
                    WHERE 1=1
                """
                params = []

                if updated_after:
                    query += " AND DATA_ALTERACAO > ?"
                    params.append(updated_after)

                query += " ORDER BY CODIGO"

                cursor.execute(query, params)

                products = []
                for row in cursor.fetchall():
                    products.append({
                        "code": row[0].strip() if row[0] else None,
                        "name": row[1].strip() if row[1] else None,
                        "price": Decimal(str(row[2])) if row[2] else Decimal("0"),
                        "weight_kg": float(row[3]) if row[3] else None,
                        "stock_quantity": int(row[4]) if row[4] else 0,
                        "active": bool(row[5]) if row[5] is not None else True,
                        "updated_at": row[6],
                    })

                logger.info(f"Produtos carregados do Firebird: {len(products)}")
                return products

        except Exception as e:
            logger.error(f"Erro ao buscar produtos do Firebird: {e}")
            return []

    # ==================== Clientes ====================

    def get_customers(self, updated_after: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Busca clientes do sistema legado.

        Returns:
            Lista de clientes com campos mapeados
        """
        if not self.is_available:
            return []

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT
                        CODIGO,
                        NOME,
                        CPF_CNPJ,
                        TELEFONE,
                        EMAIL,
                        ENDERECO,
                        NUMERO,
                        BAIRRO,
                        CIDADE,
                        CEP,
                        DATA_CADASTRO,
                        DATA_ALTERACAO
                    FROM CLIENTES
                    WHERE ATIVO = 1
                """
                params = []

                if updated_after:
                    query += " AND DATA_ALTERACAO > ?"
                    params.append(updated_after)

                cursor.execute(query, params)

                customers = []
                for row in cursor.fetchall():
                    customers.append({
                        "legacy_id": row[0],
                        "name": row[1].strip() if row[1] else None,
                        "cpf_cnpj": row[2].strip() if row[2] else None,
                        "phone": row[3].strip() if row[3] else None,
                        "email": row[4].strip() if row[4] else None,
                        "address": {
                            "street": row[5].strip() if row[5] else None,
                            "number": row[6].strip() if row[6] else None,
                            "neighborhood": row[7].strip() if row[7] else None,
                            "city": row[8].strip() if row[8] else None,
                            "postal_code": row[9].strip() if row[9] else None,
                        },
                        "created_at": row[10],
                        "updated_at": row[11],
                    })

                logger.info(f"Clientes carregados do Firebird: {len(customers)}")
                return customers

        except Exception as e:
            logger.error(f"Erro ao buscar clientes do Firebird: {e}")
            return []

    # ==================== Estoque ====================

    def get_stock_levels(self) -> List[Dict[str, Any]]:
        """
        Busca níveis de estoque atuais.

        Returns:
            Lista com código do produto e quantidade em estoque
        """
        if not self.is_available:
            return []

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT
                        CODIGO,
                        ESTOQUE_ATUAL,
                        ESTOQUE_MINIMO
                    FROM PRODUTOS
                    WHERE ATIVO = 1
                """

                cursor.execute(query)

                stock = []
                for row in cursor.fetchall():
                    stock.append({
                        "product_code": row[0].strip() if row[0] else None,
                        "quantity": int(row[1]) if row[1] else 0,
                        "min_quantity": int(row[2]) if row[2] else 0,
                    })

                return stock

        except Exception as e:
            logger.error(f"Erro ao buscar estoque do Firebird: {e}")
            return []

    # ==================== Exportar Pedidos ====================

    def export_order(self, order_data: Dict[str, Any]) -> Optional[int]:
        """
        Exporta pedido para o sistema legado (faturamento).

        Args:
            order_data: Dados do pedido a exportar

        Returns:
            ID do pedido no sistema legado ou None se falhar
        """
        if not self.is_available:
            logger.warning("Firebird não disponível para exportar pedido")
            return None

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Inserir cabeçalho do pedido
                cursor.execute("""
                    INSERT INTO PEDIDOS (
                        CLIENTE_CODIGO,
                        DATA_PEDIDO,
                        VALOR_TOTAL,
                        STATUS,
                        FORMA_PAGAMENTO,
                        OBSERVACAO,
                        REFERENCIA_EXTERNA
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    RETURNING CODIGO
                """, (
                    order_data.get("customer_legacy_id"),
                    order_data.get("created_at", datetime.now()),
                    float(order_data.get("total_amount", 0)),
                    "P",  # Pendente
                    order_data.get("payment_method", "PIX"),
                    order_data.get("notes", ""),
                    order_data.get("order_id"),  # ID do nosso sistema
                ))

                order_id = cursor.fetchone()[0]

                # Inserir itens do pedido
                for item in order_data.get("items", []):
                    cursor.execute("""
                        INSERT INTO PEDIDOS_ITENS (
                            PEDIDO_CODIGO,
                            PRODUTO_CODIGO,
                            QUANTIDADE,
                            PRECO_UNITARIO,
                            SUBTOTAL
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        order_id,
                        item.get("product_code"),
                        item.get("quantity"),
                        float(item.get("unit_price", 0)),
                        float(item.get("subtotal", 0)),
                    ))

                conn.commit()
                logger.info(f"Pedido exportado para Firebird: {order_id}")
                return order_id

        except Exception as e:
            logger.error(f"Erro ao exportar pedido para Firebird: {e}")
            return None

    def update_order_status(self, legacy_id: int, status: str) -> bool:
        """
        Atualiza status de pedido no sistema legado.

        Args:
            legacy_id: ID do pedido no Firebird
            status: Novo status (P=Pendente, F=Faturado, C=Cancelado)
        """
        if not self.is_available:
            return False

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE PEDIDOS SET STATUS = ? WHERE CODIGO = ?",
                    (status, legacy_id)
                )
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Erro ao atualizar status do pedido: {e}")
            return False


# Instância global
firebird_client = FirebirdClient()
