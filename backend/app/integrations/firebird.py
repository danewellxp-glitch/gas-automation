"""
Cliente Firebird (Sistema Legado).
Conexão somente leitura para sincronização de dados.

Usa biblioteca fdb para conexão com Firebird.
"""

import logging
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Optional, List, Dict

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
        """Monta string de conexão no formato Firebird."""
        # Formato: host/port:database
        port = 3050  # Porta padrão do Firebird
        return f"{self.host}/{port}:{self.database}"

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
            # Formato de conexão: host/port:database
            dsn = f"{self.host}/3050:{self.database}"
            conn = fdb.connect(
                dsn=dsn,
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
    ) -> List[Dict]:
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

    def get_products(self, active_only: bool = True) -> List[Dict]:
        """
        Busca catálogo de produtos do sistema legado (Gasmaster).

        Retorna:
            Lista de produtos com código, nome, preço, peso, etc.
        """
        # Query baseada no schema real do Firebird Gasmaster
        # Tabela: ITEM (produtos) + ITEMPRECO (preços)
        # Usar subquery para pegar preço mais recente
        query = """
            SELECT 
                I.ID,
                I.REFERENCIA,
                I.NOME,
                I.REDUZIDO,
                I.PESOLIQ,
                I.PESOBRUTO,
                I.ITEMSERVICO,
                I.CONTESTOQUE,
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
              AND I.IS_BLOQUEARVENDA = 'N'
              AND I.CONTESTOQUE = 'S'
        """

        # Filtrar apenas produtos de GLP (se necessário)
        # WHERE I.CLASTRIB = 'GAS'  -- Descomentar se quiser apenas GLP

        query += " ORDER BY I.REFERENCIA"

        try:
            results = self.execute_query(query)
            products = []
            for row in results:
                # Preço está em centavos, converter para reais
                # Firebird retorna colunas em minúsculas (já convertido em execute_query)
                preco_centavos = row.get("preco") or 0
                preco_reais = Decimal(str(preco_centavos)) / 100 if preco_centavos else Decimal("0")
                
                # Filtrar apenas produtos com código válido
                code = (row.get("referencia") or "").strip()
                if not code:
                    continue  # Pular produtos sem código
                
                # Firebird retorna colunas em minúsculas (já convertido)
                products.append({
                    "firebird_id": row.get("id"),
                    "code": code,
                    "name": (row.get("nome") or "").strip(),
                    "name_short": (row.get("reduzido") or "").strip(),
                    "price": preco_reais,
                    "weight_kg": float(row.get("pesoliq") or 0) if row.get("pesoliq") else None,
                    "weight_bruto_kg": float(row.get("pesobruto") or 0) if row.get("pesobruto") else None,
                    "is_active": (row.get("is_bloquearvenda") or "N") == "N",
                    "classification": (row.get("clastrib") or "").strip(),
                    "price_date": row.get("preco_data"),
                })
            return products
        except FirebirdError as e:
            logger.error(f"Erro ao buscar produtos do Firebird: {e}")
            return []

    def get_product_by_code(self, code: str) -> Optional[dict]:
        """Busca produto específico por código (REFERENCIA)."""
        query = """
            SELECT 
                I.ID,
                I.REFERENCIA,
                I.NOME,
                I.REDUZIDO,
                I.PESOLIQ,
                I.PESOBRUTO,
                I.ITEMSERVICO,
                I.CONTESTOQUE,
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
            WHERE I.REFERENCIA = ?
              AND I.ITEMSERVICO = 'I'
              AND I.IS_BLOQUEARVENDA = 'N'
        """

        results = self.execute_query(query, (code.upper(),), fetch_all=False)
        if results:
            row = results[0]
            # Firebird retorna colunas em minúsculas
            preco_centavos = row.get("preco") or row.get("PRECO") or 0
            preco_reais = Decimal(str(preco_centavos)) / 100 if preco_centavos else Decimal("0")
            
            return {
                "firebird_id": row.get("ID"),
                "code": row.get("REFERENCIA", "").strip(),
                "name": row.get("NOME", "").strip(),
                "name_short": row.get("REDUZIDO", "").strip(),
                "price": preco_reais,
                "weight_kg": float(row.get("PESOLIQ", 0)) if row.get("PESOLIQ") else None,
                "weight_bruto_kg": float(row.get("PESOBRUTO", 0)) if row.get("PESOBRUTO") else None,
                "is_active": row.get("IS_BLOQUEARVENDA") == "N",
                "classification": row.get("CLASTRIB", "").strip(),
                "price_date": row.get("PRECO_DATA"),
            }
        return None

    # ==================== Clientes ====================

    def get_customer_by_phone(self, phone: str) -> Optional[dict]:
        """
        Busca cliente por telefone no Firebird Gasmaster.
        
        Schema real:
        - PESSOA: Tabela principal de clientes
        - PESSOAFISICA: CPF para pessoas físicas
        - PESSOAJURIDICA: CNPJ para pessoas jurídicas
        - ENDERECO: Endereços (ISCOBRANCA='S' = principal)
        - FONE: Telefones (NUMEROPURO = telefone limpo)

        Args:
            phone: Telefone (será limpo para apenas números)
        """
        # Limpar telefone - apenas números
        cleaned_phone = "".join(filter(str.isdigit, phone))
        
        if not cleaned_phone or len(cleaned_phone) < 8:
            return None

        # Query completa com todas as informações
        query = """
            SELECT FIRST 1
                P.ID AS PESSOA_ID,
                P.NOME,
                P.PESSOANOME,
                P.EMAIL,
                P.NUMEROSMS,
                P.FISJUR,
                C.ID AS CLIENTE_ID,
                C.LIMITE,
                PF.CPF,
                PJ.CNPJ,
                E.LOGRADOURO,
                E.NUMERO,
                E.COMPLEMENTO,
                E.BAIRRO,
                E.CEP,
                E.CIDADE_ID,
                F.NUMERO AS TELEFONE,
                F.NUMEROPURO
            FROM PESSOA P
            LEFT JOIN CLIENTE C ON C.PESSOA_ID = P.ID
            LEFT JOIN PESSOAFISICA PF ON PF.PESSOA_ID = P.ID
            LEFT JOIN PESSOAJURIDICA PJ ON PJ.PESSOA_ID = P.ID
            LEFT JOIN ENDERECO E ON E.PESSOA_ID = P.ID AND E.ISCOBRANCA = 'S'
            LEFT JOIN FONE F ON F.PESSOA_ID = P.ID
            WHERE P.DTINATIVO IS NULL
              AND (
                  F.NUMEROPURO LIKE ?
                  OR P.NUMEROSMS LIKE ?
              )
            ORDER BY P.ID
        """

        # Buscar com os últimos 8-10 dígitos (formato brasileiro)
        search_pattern = f"%{cleaned_phone[-10:]}" if len(cleaned_phone) >= 10 else f"%{cleaned_phone}"

        results = self.execute_query(query, (search_pattern, search_pattern), fetch_all=False)

        if results:
            row = results[0]
            
            # Montar endereço completo (Firebird retorna em minúsculas)
            logradouro = row.get("logradouro") or row.get("LOGRADOURO")
            address = {}
            if logradouro:
                address = {
                    "street": (row.get("logradouro") or row.get("LOGRADOURO") or "").strip(),
                    "number": (row.get("numero") or row.get("NUMERO") or "").strip() if (row.get("numero") or row.get("NUMERO")) else None,
                    "complement": (row.get("complemento") or row.get("COMPLEMENTO") or "").strip() if (row.get("complemento") or row.get("COMPLEMENTO")) else None,
                    "bairro": (row.get("bairro") or row.get("BAIRRO") or "").strip() if (row.get("bairro") or row.get("BAIRRO")) else None,
                    "city": "Curitiba",  # Padrão, pode buscar de CIDADE_ID se necessário
                    "state": "PR",
                    "cep": (row.get("cep") or row.get("CEP") or "").strip() if (row.get("cep") or row.get("CEP")) else None,
                }
            else:
                address = {
                    "city": "Curitiba",
                    "state": "PR",
                }
            
            # Firebird retorna colunas em minúsculas
            return {
                "firebird_id": row.get("pessoa_id") or row.get("PESSOA_ID"),
                "firebird_cliente_id": row.get("cliente_id") or row.get("CLIENTE_ID"),
                "name": (row.get("nome") or row.get("NOME") or "").strip() or (row.get("pessoanome") or row.get("PESSOANOME") or "").strip(),
                "name_short": (row.get("pessoanome") or row.get("PESSOANOME") or "").strip(),
                "phone": row.get("telefone") or row.get("TELEFONE") or row.get("numerosms") or row.get("NUMEROSMS"),
                "phone_clean": row.get("numeropuro") or row.get("NUMEROPURO"),
                "email": row.get("email") or row.get("EMAIL"),
                "fisjur": row.get("fisjur") or row.get("FISJUR"),  # 'F'=Física, 'J'=Jurídica
                "cpf": (row.get("cpf") or row.get("CPF") or "").strip() if (row.get("cpf") or row.get("CPF")) else None,
                "cnpj": (row.get("cnpj") or row.get("CNPJ") or "").strip() if (row.get("cnpj") or row.get("CNPJ")) else None,
                "cpf_cnpj": (row.get("cpf") or row.get("CPF") or "").strip() if (row.get("cpf") or row.get("CPF")) else ((row.get("cnpj") or row.get("CNPJ") or "").strip() if (row.get("cnpj") or row.get("CNPJ")) else None),
                "credit_limit": float(row.get("limite") or row.get("LIMITE") or 0) / 100 if (row.get("limite") or row.get("LIMITE")) else 0,
                "address": address,
            }
        return None

    def get_customer_by_id(self, customer_id: int) -> Optional[dict]:
        """
        Busca cliente por ID do Firebird (PESSOA_ID).
        
        Args:
            customer_id: ID da tabela PESSOA
        """
        query = """
            SELECT FIRST 1
                P.ID AS PESSOA_ID,
                P.NOME,
                P.PESSOANOME,
                P.EMAIL,
                P.NUMEROSMS,
                P.FISJUR,
                C.ID AS CLIENTE_ID,
                C.LIMITE,
                PF.CPF,
                PJ.CNPJ,
                E.LOGRADOURO,
                E.NUMERO,
                E.COMPLEMENTO,
                E.BAIRRO,
                E.CEP,
                F.NUMERO AS TELEFONE,
                F.NUMEROPURO
            FROM PESSOA P
            LEFT JOIN CLIENTE C ON C.PESSOA_ID = P.ID
            LEFT JOIN PESSOAFISICA PF ON PF.PESSOA_ID = P.ID
            LEFT JOIN PESSOAJURIDICA PJ ON PJ.PESSOA_ID = P.ID
            LEFT JOIN ENDERECO E ON E.PESSOA_ID = P.ID AND E.ISCOBRANCA = 'S'
            LEFT JOIN FONE F ON F.PESSOA_ID = P.ID
            WHERE P.ID = ?
              AND P.DTINATIVO IS NULL
        """

        results = self.execute_query(query, (customer_id,), fetch_all=False)

        if results:
            row = results[0]
            
            # Montar endereço (Firebird retorna em minúsculas)
            logradouro = row.get("logradouro") or row.get("LOGRADOURO")
            address = {}
            if logradouro:
                address = {
                    "street": (row.get("logradouro") or row.get("LOGRADOURO") or "").strip(),
                    "number": (row.get("numero") or row.get("NUMERO") or "").strip() if (row.get("numero") or row.get("NUMERO")) else None,
                    "complement": (row.get("complemento") or row.get("COMPLEMENTO") or "").strip() if (row.get("complemento") or row.get("COMPLEMENTO")) else None,
                    "bairro": (row.get("bairro") or row.get("BAIRRO") or "").strip() if (row.get("bairro") or row.get("BAIRRO")) else None,
                    "city": "Curitiba",
                    "state": "PR",
                    "cep": (row.get("cep") or row.get("CEP") or "").strip() if (row.get("cep") or row.get("CEP")) else None,
                }
            else:
                address = {"city": "Curitiba", "state": "PR"}
            
            return {
                "firebird_id": row.get("pessoa_id") or row.get("PESSOA_ID"),
                "firebird_cliente_id": row.get("cliente_id") or row.get("CLIENTE_ID"),
                "name": (row.get("nome") or row.get("NOME") or "").strip() or (row.get("pessoanome") or row.get("PESSOANOME") or "").strip(),
                "name_short": (row.get("pessoanome") or row.get("PESSOANOME") or "").strip(),
                "phone": row.get("telefone") or row.get("TELEFONE") or row.get("numerosms") or row.get("NUMEROSMS"),
                "phone_clean": row.get("numeropuro") or row.get("NUMEROPURO"),
                "email": row.get("email") or row.get("EMAIL"),
                "fisjur": row.get("fisjur") or row.get("FISJUR"),
                "cpf": (row.get("cpf") or row.get("CPF") or "").strip() if (row.get("cpf") or row.get("CPF")) else None,
                "cnpj": (row.get("cnpj") or row.get("CNPJ") or "").strip() if (row.get("cnpj") or row.get("CNPJ")) else None,
                "cpf_cnpj": (row.get("cpf") or row.get("CPF") or "").strip() if (row.get("cpf") or row.get("CPF")) else ((row.get("cnpj") or row.get("CNPJ") or "").strip() if (row.get("cnpj") or row.get("CNPJ")) else None),
                "credit_limit": float(row.get("limite") or row.get("LIMITE") or 0) / 100 if (row.get("limite") or row.get("LIMITE")) else 0,
                "address": address,
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

    def get_drivers(self, active_only: bool = True) -> List[Dict]:
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

    # ==================== Pontos de Venda ====================

    def get_sales_points(self, juridica_only: bool = False, fisica_only: bool = False) -> List[Dict]:
        """
        Busca pontos de venda do Firebird Gasmaster.
        
        Usa as views:
        - VPESSOAJURIDICA: Pontos de venda (pessoas jurídicas)
        - VPESSOAFISICASIMPLES: Pontos de venda (pessoas físicas)
        
        Args:
            juridica_only: Se True, retorna apenas jurídicas
            fisica_only: Se True, retorna apenas físicas
        """
        points = []
        
        # Buscar pontos jurídicos
        if not fisica_only:
            query_juridica = """
                SELECT
                    PESSOA_ID,
                    PESSOANOME,
                    POPULAR,
                    CNPJ,
                    INSCESTAD,
                    ATIVIDADENOME,
                    DTCAD
                FROM VPESSOAJURIDICA
                ORDER BY PESSOANOME
            """
            try:
                results = self.execute_query(query_juridica)
                for row in results:
                    points.append({
                        "firebird_id": row.get("PESSOA_ID"),
                        "name": row.get("PESSOANOME", "").strip(),
                        "name_short": row.get("POPULAR", "").strip(),
                        "cnpj": row.get("CNPJ", "").strip() if row.get("CNPJ") else None,
                        "insc_estadual": row.get("INSCESTAD", "").strip() if row.get("INSCESTAD") else None,
                        "activity": row.get("ATIVIDADENOME", "").strip() if row.get("ATIVIDADENOME") else None,
                        "type": "juridica",
                        "created_at": row.get("DTCAD"),
                    })
            except FirebirdError as e:
                logger.warning(f"Erro ao buscar pontos jurídicos: {e}")
        
        # Buscar pontos físicos
        if not juridica_only:
            query_fisica = """
                SELECT
                    ID,
                    NOME,
                    POPULAR
                FROM VPESSOAFISICASIMPLES
                ORDER BY NOME
            """
            try:
                results = self.execute_query(query_fisica)
                for row in results:
                    # Firebird retorna em minúsculas
                    points.append({
                        "firebird_id": row.get("id") or row.get("ID"),
                        "name": (row.get("nome") or row.get("NOME") or "").strip(),
                        "name_short": (row.get("popular") or row.get("POPULAR") or "").strip(),
                        "type": "fisica",
                    })
            except FirebirdError as e:
                logger.warning(f"Erro ao buscar pontos físicos: {e}")
        
        return points

    # ==================== Estoque ====================

    def get_stock_levels(
        self,
        estlocal_id: int = 1,
        esttipo_id: int = 1,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> List[Dict]:
        """
        Busca níveis de estoque atuais.
        
        Args:
            estlocal_id: ID do local de estoque (1 = GASMASTER - Fiscal)
            esttipo_id: ID do tipo de estoque (1 = FISICO - disponível)
            year: Ano (None = ano atual)
            month: Mês (None = mês atual)
        
        Returns:
            Lista com código do produto e quantidade em estoque
        """
        if not self.is_available:
            logger.warning("Firebird não disponível, retornando lista vazia")
            return []

        from datetime import datetime
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        query = """
            SELECT 
                I.REFERENCIA,
                I.NOME,
                ITS.SALDO,
                ITS.ANO,
                ITS.MES,
                ITS.ESTLOCAL_ID,
                ITS.ESTTIPO_ID
            FROM ITEMSALDO ITS
            JOIN ITEM I ON ITS.ITEM_ID = I.ID
            WHERE ITS.ESTLOCAL_ID = ?
              AND ITS.ESTTIPO_ID = ?
              AND ITS.ANO = ?
              AND ITS.MES = ?
            ORDER BY I.REFERENCIA
        """

        try:
            results = self.execute_query(query, (estlocal_id, esttipo_id, year, month))
            stock = []
            for row in results:
                stock.append({
                    "product_code": (row.get("referencia") or "").strip(),
                    "product_name": (row.get("nome") or "").strip(),
                    "quantity": int(row.get("saldo") or 0),
                    "year": int(row.get("ano") or year),
                    "month": int(row.get("mes") or month),
                    "estlocal_id": int(row.get("estlocal_id") or estlocal_id),
                    "esttipo_id": int(row.get("esttipo_id") or esttipo_id),
                })
            return stock
        except FirebirdError as e:
            logger.error(f"Erro ao buscar estoque do Firebird: {e}")
            return []

    # ==================== Rotas ====================

    def get_routes(self) -> List[Dict]:
        """
        Busca rotas de entrega.
        
        Returns:
            Lista de rotas com ID, nome e total de clientes
        """
        if not self.is_available:
            logger.warning("Firebird não disponível, retornando lista vazia")
            return []

        query = """
            SELECT 
                R.ID,
                R.NOME,
                COUNT(RP.PESSOA_ID) AS TOTAL_CLIENTES
            FROM ROTA R
            LEFT JOIN ROTAPESSOA RP ON R.ID = RP.ROTA_ID
            GROUP BY R.ID, R.NOME
            ORDER BY R.NOME
        """

        try:
            results = self.execute_query(query)
            routes = []
            for row in results:
                routes.append({
                    "firebird_id": int(row.get("id") or 0),
                    "name": (row.get("nome") or "").strip(),
                    "total_customers": int(row.get("total_clientes") or 0),
                })
            return routes
        except FirebirdError as e:
            logger.error(f"Erro ao buscar rotas do Firebird: {e}")
            return []

    def get_route_customers(self, route_id: int) -> List[Dict]:
        """
        Busca clientes de uma rota específica.
        
        Args:
            route_id: ID da rota
            
        Returns:
            Lista de clientes da rota com posição
        """
        if not self.is_available:
            logger.warning("Firebird não disponível, retornando lista vazia")
            return []

        query = """
            SELECT 
                RP.PESSOA_ID,
                RP.POSICAO,
                P.NOME AS PESSOANOME
            FROM ROTAPESSOA RP
            JOIN PESSOA P ON RP.PESSOA_ID = P.ID
            WHERE RP.ROTA_ID = ?
            ORDER BY RP.POSICAO
        """

        try:
            results = self.execute_query(query, (route_id,))
            customers = []
            for row in results:
                customers.append({
                    "firebird_id": int(row.get("pessoa_id") or 0),
                    "name": (row.get("pessoanome") or "").strip(),
                    "position": int(row.get("posicao") or 0),
                })
            return customers
        except FirebirdError as e:
            logger.error(f"Erro ao buscar clientes da rota: {e}")
            return []

    # ==================== Veículos ====================

    def get_vehicles(self, own_only: bool = True) -> List[Dict]:
        """
        Busca veículos de entrega.
        
        Args:
            own_only: Se True, retorna apenas veículos próprios
            
        Returns:
            Lista de veículos
        """
        if not self.is_available:
            logger.warning("Firebird não disponível, retornando lista vazia")
            return []

        query = """
            SELECT 
                V.ID,
                V.NOME,
                V.PLACA,
                V.PROPRIO,
                V.ESTAB_ID,
                V.TIPOVEIC_ID,
                V.RENAVAM,
                V.CHASSI
            FROM VEICULO V
        """
        
        if own_only:
            query += " WHERE V.PROPRIO = 'S'"
        
        query += " ORDER BY V.NOME"

        try:
            results = self.execute_query(query)
            vehicles = []
            for row in results:
                vehicles.append({
                    "firebird_id": int(row.get("id") or 0),
                    "name": (row.get("nome") or "").strip(),
                    "plate": (row.get("placa") or "").strip(),
                    "is_own": (row.get("proprio") or "N") == "S",
                    "estab_id": int(row.get("estab_id") or 0) if row.get("estab_id") else None,
                    "vehicle_type_id": int(row.get("tipoveic_id") or 0) if row.get("tipoveic_id") else None,
                    "renavam": (row.get("renavam") or "").strip() if row.get("renavam") else None,
                    "chassis": (row.get("chassi") or "").strip() if row.get("chassi") else None,
                })
            return vehicles
        except FirebirdError as e:
            logger.error(f"Erro ao buscar veículos do Firebird: {e}")
            return []

    def get_sales_point_by_id(self, pessoa_id: int) -> Optional[dict]:
        """
        Busca ponto de venda específico por ID.
        
        Args:
            pessoa_id: ID da PESSOA
        """
        # Tentar buscar como jurídica primeiro
        query = """
            SELECT FIRST 1
                PESSOA_ID,
                PESSOANOME,
                POPULAR,
                CNPJ,
                INSCESTAD,
                ATIVIDADENOME,
                DTCAD
            FROM VPESSOAJURIDICA
            WHERE PESSOA_ID = ?
        """
        
        results = self.execute_query(query, (pessoa_id,), fetch_all=False)
        if results:
            row = results[0]
            # Firebird retorna em minúsculas
            return {
                "firebird_id": row.get("pessoa_id") or row.get("PESSOA_ID"),
                "name": (row.get("pessoanome") or row.get("PESSOANOME") or "").strip(),
                "name_short": (row.get("popular") or row.get("POPULAR") or "").strip(),
                "cnpj": (row.get("cnpj") or row.get("CNPJ") or "").strip() if (row.get("cnpj") or row.get("CNPJ")) else None,
                "insc_estadual": (row.get("inscestad") or row.get("INSCESTAD") or "").strip() if (row.get("inscestad") or row.get("INSCESTAD")) else None,
                "activity": (row.get("atividadenome") or row.get("ATIVIDADENOME") or "").strip() if (row.get("atividadenome") or row.get("ATIVIDADENOME")) else None,
                "type": "juridica",
                "created_at": row.get("dtcad") or row.get("DTCAD"),
            }
        
        # Se não encontrou como jurídica, tentar como física
        query = """
            SELECT FIRST 1
                ID,
                NOME,
                POPULAR
            FROM VPESSOAFISICASIMPLES
            WHERE ID = ?
        """
        
        results = self.execute_query(query, (pessoa_id,), fetch_all=False)
        if results:
            row = results[0]
            # Firebird retorna em minúsculas
            return {
                "firebird_id": row.get("id") or row.get("ID"),
                "name": (row.get("nome") or row.get("NOME") or "").strip(),
                "name_short": (row.get("popular") or row.get("POPULAR") or "").strip(),
                "type": "fisica",
            }
        
        return None

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
def get_products_from_legacy() -> List[Dict]:
    """Busca produtos do sistema legado."""
    return firebird_client.get_products()


def get_customer_from_legacy(phone: str) -> Optional[dict]:
    """Busca cliente do sistema legado por telefone."""
    return firebird_client.get_customer_by_phone(phone)


def is_firebird_available() -> bool:
    """Verifica se Firebird está disponível."""
    return firebird_client.is_available
