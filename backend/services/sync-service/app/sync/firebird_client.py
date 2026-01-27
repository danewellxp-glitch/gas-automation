"""
Cliente Firebird para sincronização com sistema legado (Gasmaster).

Schema real do Firebird:
- ITEM: Produtos
- ITEMPRECO: Preços dos produtos
- ITEMSALDO: Saldos de estoque
- PESSOA: Clientes/Pessoas
- PESSOAFISICA: Dados de pessoa física (CPF)
- PESSOAJURIDICA: Dados de pessoa jurídica (CNPJ)
- ENDERECO: Endereços
- FONE: Telefones
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
    Cliente para conexão com banco Firebird (sistema legado Gasmaster).

    Usado para:
    - Importar produtos e preços
    - Importar clientes existentes
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

    def get_products(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Busca produtos do sistema legado (Gasmaster).

        Tabelas:
        - ITEM: Dados do produto
        - ITEMPRECO: Preços (TIPOPRECO_ID=1 = preço padrão)

        Returns:
            Lista de produtos com código, nome, preço, peso
        """
        if not self.is_available:
            return []

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT
                        I.ID,
                        I.REFERENCIA,
                        I.NOME,
                        I.REDUZIDO,
                        I.PESOLIQ,
                        I.PESOBRUTO,
                        I.IS_BLOQUEARVENDA,
                        I.CLASTRIB,
                        (SELECT FIRST 1 IP.PRECO
                         FROM ITEMPRECO IP
                         WHERE IP.ITEM_ID = I.ID
                           AND IP.TIPOPRECO_ID = 1
                         ORDER BY IP.DATAREAJ DESC) AS PRECO,
                        (SELECT FIRST 1 IP.DATAREAJ
                         FROM ITEMPRECO IP
                         WHERE IP.ITEM_ID = I.ID
                           AND IP.TIPOPRECO_ID = 1
                         ORDER BY IP.DATAREAJ DESC) AS PRECO_DATA
                    FROM ITEM I
                    WHERE I.ITEMSERVICO = 'I'
                      AND I.CONTESTOQUE = 'S'
                """

                if active_only:
                    query += " AND I.IS_BLOQUEARVENDA = 'N'"

                query += " ORDER BY I.REFERENCIA"

                cursor.execute(query)

                products = []
                for row in cursor.fetchall():
                    # Preço em centavos, converter para reais
                    preco_centavos = row[8] or 0
                    preco_reais = Decimal(str(preco_centavos)) / 100 if preco_centavos else Decimal("0")

                    code = (row[1] or "").strip()
                    if not code:
                        continue

                    products.append({
                        "firebird_id": row[0],
                        "code": code,
                        "name": (row[2] or "").strip(),
                        "name_short": (row[3] or "").strip(),
                        "price": preco_reais,
                        "weight_kg": float(row[4]) if row[4] else None,
                        "weight_bruto_kg": float(row[5]) if row[5] else None,
                        "active": (row[6] or "N") == "N",
                        "classification": (row[7] or "").strip(),
                        "price_date": row[9],
                    })

                logger.info(f"Produtos carregados do Firebird: {len(products)}")
                return products

        except Exception as e:
            logger.error(f"Erro ao buscar produtos do Firebird: {e}")
            return []

    # ==================== Clientes ====================

    def get_customers(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Busca clientes do sistema legado (Gasmaster).

        Tabelas:
        - PESSOA: Dados principais
        - PESSOAFISICA: CPF
        - PESSOAJURIDICA: CNPJ
        - ENDERECO: Endereço (ISCOBRANCA='S' = principal)
        - FONE: Telefones

        Returns:
            Lista de clientes com dados completos
        """
        if not self.is_available:
            return []

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT
                        P.ID,
                        P.NOME,
                        P.PESSOANOME,
                        P.EMAIL,
                        P.NUMEROSMS,
                        P.FISJUR,
                        P.DTCAD,
                        PF.CPF,
                        PJ.CNPJ,
                        E.LOGRADOURO,
                        E.NUMERO,
                        E.COMPLEMENTO,
                        E.BAIRRO,
                        E.CEP,
                        F.NUMEROPURO
                    FROM PESSOA P
                    LEFT JOIN PESSOAFISICA PF ON PF.PESSOA_ID = P.ID
                    LEFT JOIN PESSOAJURIDICA PJ ON PJ.PESSOA_ID = P.ID
                    LEFT JOIN ENDERECO E ON E.PESSOA_ID = P.ID AND E.ISCOBRANCA = 'S'
                    LEFT JOIN FONE F ON F.PESSOA_ID = P.ID
                """

                if active_only:
                    query += " WHERE P.DTINATIVO IS NULL"

                query += " ORDER BY P.ID"

                cursor.execute(query)

                customers = []
                seen_ids = set()

                for row in cursor.fetchall():
                    # Evitar duplicatas (pode ter múltiplos telefones)
                    pessoa_id = row[0]
                    if pessoa_id in seen_ids:
                        continue
                    seen_ids.add(pessoa_id)

                    phone = (row[14] or row[4] or "").strip()

                    customers.append({
                        "firebird_id": pessoa_id,
                        "name": (row[1] or row[2] or "").strip(),
                        "name_short": (row[2] or "").strip(),
                        "email": (row[3] or "").strip() if row[3] else None,
                        "phone": phone if phone else None,
                        "fisjur": row[5],
                        "cpf": (row[7] or "").strip() if row[7] else None,
                        "cnpj": (row[8] or "").strip() if row[8] else None,
                        "address": {
                            "street": (row[9] or "").strip() if row[9] else None,
                            "number": (row[10] or "").strip() if row[10] else None,
                            "complement": (row[11] or "").strip() if row[11] else None,
                            "neighborhood": (row[12] or "").strip() if row[12] else None,
                            "postal_code": (row[13] or "").strip() if row[13] else None,
                        },
                        "created_at": row[6],
                    })

                logger.info(f"Clientes carregados do Firebird: {len(customers)}")
                return customers

        except Exception as e:
            logger.error(f"Erro ao buscar clientes do Firebird: {e}")
            return []

    # ==================== Estoque ====================

    def get_stock_levels(
        self,
        estlocal_id: int = 1,
        esttipo_id: int = 1,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca níveis de estoque atuais.

        Tabelas:
        - ITEMSALDO: Saldos por local/tipo/período
        - ITEM: Dados do produto

        Args:
            estlocal_id: ID do local de estoque (1 = padrão)
            esttipo_id: ID do tipo de estoque (1 = físico)
            year: Ano (None = atual)
            month: Mês (None = atual)

        Returns:
            Lista com código do produto e quantidade em estoque
        """
        if not self.is_available:
            return []

        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT
                        I.REFERENCIA,
                        I.NOME,
                        ITS.SALDO
                    FROM ITEMSALDO ITS
                    JOIN ITEM I ON ITS.ITEM_ID = I.ID
                    WHERE ITS.ESTLOCAL_ID = ?
                      AND ITS.ESTTIPO_ID = ?
                      AND ITS.ANO = ?
                      AND ITS.MES = ?
                    ORDER BY I.REFERENCIA
                """

                cursor.execute(query, (estlocal_id, esttipo_id, year, month))

                stock = []
                for row in cursor.fetchall():
                    code = (row[0] or "").strip()
                    if not code:
                        continue

                    stock.append({
                        "product_code": code,
                        "product_name": (row[1] or "").strip(),
                        "quantity": int(row[2]) if row[2] else 0,
                    })

                logger.info(f"Estoque carregado do Firebird: {len(stock)} itens")
                return stock

        except Exception as e:
            logger.error(f"Erro ao buscar estoque do Firebird: {e}")
            return []


# Instância global
firebird_client = FirebirdClient()
