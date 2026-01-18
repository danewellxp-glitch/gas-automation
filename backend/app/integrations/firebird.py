"""
Cliente Firebird (Sistema Legado).
Conexão somente leitura para sincronização de dados.

Usa biblioteca fdb para conexão com Firebird.
"""

import logging
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Tentar importar fdb (pode não estar disponível em todos os ambientes)
try:
    import fdb
    FDB_AVAILABLE = True
except ImportError:
    FDB_AVAILABLE = False
    logger.warning("Biblioteca fdb não disponível. Integração Firebird desabilitada.")


class FirebirdError(Exception):
    """Exceção para erros de conexão/consulta Firebird."""
    pass


class FirebirdClient:
    """
    Cliente para conexão com banco Firebird (sistema legado).

    Suporta apenas operações de LEITURA para sincronização de dados.
    NÃO escrever dados no Firebird para evitar conflitos.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        charset: Optional[str] = None,
    ):
        self.host = host or settings.firebird_host
        self.database = database or settings.firebird_database
        self.user = user or settings.firebird_user
        self.password = password or settings.firebird_password
        self.charset = charset or settings.firebird_charset
        self._connection = None

    @property
    def is_configured(self) -> bool:
        """Verifica se a conexão está configurada."""
        return bool(self.host and self.database)

    @property
    def is_available(self) -> bool:
        """Verifica se Firebird está disponível."""
        return FDB_AVAILABLE and self.is_configured

    def _get_connection_string(self) -> str:
        """Monta string de conexão."""
        return f"{self.host}:{self.database}"

    @contextmanager
    def get_connection(self):
        """
        Context manager para conexão.
        Garante que a conexão seja fechada após uso.
        """
        if not self.is_available:
            raise FirebirdError("Firebird não está configurado ou disponível")

        conn = None
        try:
            conn = fdb.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                charset=self.charset,
            )
            yield conn
        except Exception as e:
            logger.error(f"Erro de conexão Firebird: {e}")
            raise FirebirdError(f"Erro de conexão: {str(e)}")
        finally:
            if conn:
                conn.close()

    def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch_all: bool = True,
    ) -> list[dict]:
        """
        Executa query SELECT e retorna resultados como lista de dicionários.

        Args:
            query: SQL SELECT
            params: Parâmetros da query (tupla)
            fetch_all: Se True, retorna todos os resultados

        Returns:
            Lista de dicionários com os resultados
        """
        if not self.is_available:
            logger.warning("Firebird não disponível, retornando lista vazia")
            return []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                # Obter nomes das colunas
                columns = [desc[0].lower() for desc in cursor.description]

                # Converter para lista de dicionários
                if fetch_all:
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    row = cursor.fetchone()
                    return [dict(zip(columns, row))] if row else []

            except Exception as e:
                logger.error(f"Erro ao executar query: {e}")
                raise FirebirdError(f"Erro na query: {str(e)}")
            finally:
                cursor.close()

    # ==================== Produtos ====================

    def get_products(self, active_only: bool = True) -> list[dict]:
        """
        Busca catálogo de produtos do sistema legado.

        Retorna:
            Lista de produtos com código, nome, preço, etc.
        """
        # NOTA: Ajustar query conforme estrutura real do Firebird
        query = """
            SELECT
                CODIGO,
                DESCRICAO,
                PRECO_VENDA,
                UNIDADE,
                ATIVO
            FROM PRODUTOS
            WHERE TIPO = 'GAS'
        """

        if active_only:
            query += " AND ATIVO = 'S'"

        query += " ORDER BY CODIGO"

        try:
            results = self.execute_query(query)
            return [
                {
                    "code": row.get("codigo"),
                    "name": row.get("descricao"),
                    "price": Decimal(str(row.get("preco_venda", 0))),
                    "unit": row.get("unidade"),
                    "is_active": row.get("ativo") == "S",
                }
                for row in results
            ]
        except FirebirdError:
            # Retornar lista vazia se não conseguir conectar
            return []

    def get_product_by_code(self, code: str) -> Optional[dict]:
        """Busca produto específico por código."""
        query = """
            SELECT
                CODIGO,
                DESCRICAO,
                PRECO_VENDA,
                UNIDADE,
                ATIVO
            FROM PRODUTOS
            WHERE CODIGO = ?
        """

        results = self.execute_query(query, (code,), fetch_all=False)
        if results:
            row = results[0]
            return {
                "code": row.get("codigo"),
                "name": row.get("descricao"),
                "price": Decimal(str(row.get("preco_venda", 0))),
                "unit": row.get("unidade"),
                "is_active": row.get("ativo") == "S",
            }
        return None

    # ==================== Clientes ====================

    def get_customer_by_phone(self, phone: str) -> Optional[dict]:
        """
        Busca cliente por telefone.

        Args:
            phone: Telefone (será limpo para apenas números)
        """
        # Limpar telefone
        cleaned_phone = "".join(filter(str.isdigit, phone))

        # Buscar com diferentes formatos
        query = """
            SELECT
                CODIGO,
                NOME,
                TELEFONE,
                CELULAR,
                ENDERECO,
                NUMERO,
                COMPLEMENTO,
                BAIRRO,
                CIDADE,
                UF,
                CEP,
                CPF_CNPJ,
                EMAIL
            FROM CLIENTES
            WHERE REPLACE(REPLACE(REPLACE(TELEFONE, '(', ''), ')', ''), '-', '') LIKE ?
               OR REPLACE(REPLACE(REPLACE(CELULAR, '(', ''), ')', ''), '-', '') LIKE ?
        """

        # Buscar com os últimos 8-9 dígitos
        search_phone = f"%{cleaned_phone[-9:]}" if len(cleaned_phone) >= 9 else f"%{cleaned_phone}"

        results = self.execute_query(query, (search_phone, search_phone), fetch_all=False)

        if results:
            row = results[0]
            return {
                "firebird_id": row.get("codigo"),
                "name": row.get("nome"),
                "phone": row.get("celular") or row.get("telefone"),
                "cpf_cnpj": row.get("cpf_cnpj"),
                "email": row.get("email"),
                "address": {
                    "street": row.get("endereco"),
                    "number": row.get("numero"),
                    "complement": row.get("complemento"),
                    "bairro": row.get("bairro"),
                    "city": row.get("cidade") or "Curitiba",
                    "state": row.get("uf") or "PR",
                    "cep": row.get("cep"),
                },
            }
        return None

    def get_customer_by_id(self, customer_id: int) -> Optional[dict]:
        """Busca cliente por ID do Firebird."""
        query = """
            SELECT
                CODIGO,
                NOME,
                TELEFONE,
                CELULAR,
                ENDERECO,
                NUMERO,
                COMPLEMENTO,
                BAIRRO,
                CIDADE,
                UF,
                CEP,
                CPF_CNPJ,
                EMAIL
            FROM CLIENTES
            WHERE CODIGO = ?
        """

        results = self.execute_query(query, (customer_id,), fetch_all=False)

        if results:
            row = results[0]
            return {
                "firebird_id": row.get("codigo"),
                "name": row.get("nome"),
                "phone": row.get("celular") or row.get("telefone"),
                "cpf_cnpj": row.get("cpf_cnpj"),
                "email": row.get("email"),
                "address": {
                    "street": row.get("endereco"),
                    "number": row.get("numero"),
                    "complement": row.get("complemento"),
                    "bairro": row.get("bairro"),
                    "city": row.get("cidade") or "Curitiba",
                    "state": row.get("uf") or "PR",
                    "cep": row.get("cep"),
                },
            }
        return None

    # ==================== Entregadores ====================

    def get_drivers(self, active_only: bool = True) -> list[dict]:
        """Busca lista de entregadores."""
        query = """
            SELECT
                CODIGO,
                NOME,
                TELEFONE,
                ATIVO
            FROM ENTREGADORES
        """

        if active_only:
            query += " WHERE ATIVO = 'S'"

        query += " ORDER BY NOME"

        try:
            results = self.execute_query(query)
            return [
                {
                    "id": row.get("codigo"),
                    "name": row.get("nome"),
                    "phone": row.get("telefone"),
                    "is_active": row.get("ativo") == "S",
                }
                for row in results
            ]
        except FirebirdError:
            return []

    # ==================== Sincronização ====================

    def sync_products_to_postgres(self, db_session) -> int:
        """
        Sincroniza produtos do Firebird para PostgreSQL.

        Args:
            db_session: Sessão SQLAlchemy

        Returns:
            Número de produtos sincronizados
        """
        # Esta função seria chamada por um job de sincronização
        # Implementação futura
        raise NotImplementedError("Sincronização ainda não implementada")

    def test_connection(self) -> bool:
        """Testa conexão com o Firebird."""
        if not self.is_available:
            return False

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM RDB$DATABASE")
                cursor.fetchone()
                cursor.close()
                return True
        except Exception as e:
            logger.error(f"Teste de conexão falhou: {e}")
            return False


# Instância global (singleton)
firebird_client = FirebirdClient()


# Funções de conveniência
def get_products_from_legacy() -> list[dict]:
    """Busca produtos do sistema legado."""
    return firebird_client.get_products()


def get_customer_from_legacy(phone: str) -> Optional[dict]:
    """Busca cliente do sistema legado por telefone."""
    return firebird_client.get_customer_by_phone(phone)


def is_firebird_available() -> bool:
    """Verifica se Firebird está disponível."""
    return firebird_client.is_available
