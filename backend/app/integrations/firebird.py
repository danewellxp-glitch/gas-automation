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
            # execute_query converte colunas para minúsculas
            preco_centavos = row.get("preco") or 0
            preco_reais = Decimal(str(preco_centavos)) / 100 if preco_centavos else Decimal("0")

            return {
                "firebird_id": row.get("id"),
                "code": (row.get("referencia") or "").strip(),
                "name": (row.get("nome") or "").strip(),
                "name_short": (row.get("reduzido") or "").strip(),
                "price": preco_reais,
                "weight_kg": float(row.get("pesoliq") or 0) if row.get("pesoliq") else None,
                "weight_bruto_kg": float(row.get("pesobruto") or 0) if row.get("pesobruto") else None,
                "is_active": (row.get("is_bloquearvenda") or "N") == "N",
                "classification": (row.get("clastrib") or "").strip(),
                "price_date": row.get("preco_data"),
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

        # Buscar com os últimos 8 dígitos (formato brasileiro)
        # Telefones no Firebird podem ter 8-10 dígitos
        # WhatsApp envia com código país (55) + DDD + número
        search_digits = cleaned_phone[-8:] if len(cleaned_phone) >= 8 else cleaned_phone
        search_pattern = f"%{search_digits}"

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

    def get_customer_by_address(self, cep: str, numero: str) -> Optional[dict]:
        """
        Busca cliente por CEP + Número no Firebird.

        Args:
            cep: CEP (será limpo para apenas números)
            numero: Número do endereço

        Returns:
            Dados do cliente ou None se não encontrado/múltiplos resultados
        """
        # Limpar CEP - apenas números
        cleaned_cep = "".join(filter(str.isdigit, cep))
        cleaned_numero = numero.strip()

        if not cleaned_cep or len(cleaned_cep) < 8:
            return None

        if not cleaned_numero:
            return None

        # Buscar por CEP + NUMERO (campo separado) ou número dentro do LOGRADOURO
        query = """
            SELECT
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
              AND E.CEP = ?
              AND (
                  E.NUMERO = ?
                  OR E.LOGRADOURO LIKE ?
              )
            ORDER BY P.ID
        """

        # Padrão para buscar número no logradouro (ex: "RUA X - 245" ou "RUA X, 245")
        logradouro_pattern = f"%{cleaned_numero}%"

        try:
            results = self.execute_query(query, (cleaned_cep, cleaned_numero, logradouro_pattern))

            if not results:
                return None

            if len(results) > 1:
                # Múltiplos clientes encontrados - retornar lista para desambiguação
                logger.warning(f"Múltiplos clientes encontrados para CEP {cleaned_cep} número {cleaned_numero}")
                return {
                    "multiple": True,
                    "count": len(results),
                    "customers": [
                        {
                            "firebird_id": row.get("pessoa_id"),
                            "name": (row.get("nome") or "").strip(),
                            "logradouro": (row.get("logradouro") or "").strip(),
                            "numero": (row.get("numero") or "").strip() if row.get("numero") else None,
                        }
                        for row in results
                    ]
                }

            # Único resultado encontrado
            row = results[0]

            # Montar endereço completo
            address = {
                "street": (row.get("logradouro") or "").strip(),
                "number": (row.get("numero") or "").strip() if row.get("numero") else None,
                "complement": (row.get("complemento") or "").strip() if row.get("complemento") else None,
                "bairro": (row.get("bairro") or "").strip() if row.get("bairro") else None,
                "city": "Curitiba",
                "state": "PR",
                "cep": (row.get("cep") or "").strip() if row.get("cep") else None,
            }

            return {
                "firebird_id": row.get("pessoa_id"),
                "firebird_cliente_id": row.get("cliente_id"),
                "name": (row.get("nome") or "").strip() or (row.get("pessoanome") or "").strip(),
                "name_short": (row.get("pessoanome") or "").strip(),
                "phone": row.get("telefone") or row.get("numerosms"),
                "phone_clean": row.get("numeropuro"),
                "email": row.get("email"),
                "fisjur": row.get("fisjur"),
                "cpf": (row.get("cpf") or "").strip() if row.get("cpf") else None,
                "cnpj": (row.get("cnpj") or "").strip() if row.get("cnpj") else None,
                "cpf_cnpj": (row.get("cpf") or "").strip() if row.get("cpf") else ((row.get("cnpj") or "").strip() if row.get("cnpj") else None),
                "credit_limit": float(row.get("limite") or 0) / 100 if row.get("limite") else 0,
                "address": address,
            }

        except FirebirdError as e:
            logger.error(f"Erro ao buscar cliente por endereço: {e}")
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
                    # execute_query converte colunas para minúsculas
                    points.append({
                        "firebird_id": row.get("pessoa_id"),
                        "name": (row.get("pessoanome") or "").strip(),
                        "name_short": (row.get("popular") or "").strip(),
                        "cnpj": (row.get("cnpj") or "").strip() if row.get("cnpj") else None,
                        "insc_estadual": (row.get("inscestad") or "").strip() if row.get("inscestad") else None,
                        "activity": (row.get("atividadenome") or "").strip() if row.get("atividadenome") else None,
                        "type": "juridica",
                        "created_at": row.get("dtcad"),
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

    # ==================== Schema Discovery ====================

    def get_all_tables(self) -> List[Dict]:
        """
        Lista todas as tabelas do banco Firebird.

        Returns:
            Lista de tabelas com nome e tipo (TABLE, VIEW, etc.)
        """
        if not self.is_available:
            logger.warning("Firebird não disponível")
            return []

        query = """
            SELECT
                TRIM(RDB$RELATION_NAME) AS TABLE_NAME,
                CASE RDB$VIEW_SOURCE
                    WHEN NULL THEN 'TABLE'
                    ELSE 'VIEW'
                END AS TABLE_TYPE,
                RDB$DESCRIPTION AS DESCRIPTION
            FROM RDB$RELATIONS
            WHERE RDB$SYSTEM_FLAG = 0
              AND RDB$RELATION_NAME NOT STARTING WITH 'RDB$'
            ORDER BY RDB$RELATION_NAME
        """

        try:
            results = self.execute_query(query)
            tables = []
            for row in results:
                tables.append({
                    "name": (row.get("table_name") or "").strip(),
                    "type": (row.get("table_type") or "TABLE").strip(),
                    "description": (row.get("description") or "").strip() if row.get("description") else None,
                })
            return tables
        except FirebirdError as e:
            logger.error(f"Erro ao listar tabelas: {e}")
            return []

    def get_table_columns(self, table_name: str) -> List[Dict]:
        """
        Lista todas as colunas de uma tabela.

        Args:
            table_name: Nome da tabela

        Returns:
            Lista de colunas com nome, tipo, nullable, etc.
        """
        if not self.is_available:
            logger.warning("Firebird não disponível")
            return []

        query = """
            SELECT
                TRIM(RF.RDB$FIELD_NAME) AS COLUMN_NAME,
                TRIM(F.RDB$FIELD_TYPE) AS FIELD_TYPE_CODE,
                F.RDB$FIELD_LENGTH AS FIELD_LENGTH,
                F.RDB$FIELD_PRECISION AS FIELD_PRECISION,
                F.RDB$FIELD_SCALE AS FIELD_SCALE,
                RF.RDB$NULL_FLAG AS NOT_NULL,
                RF.RDB$DEFAULT_SOURCE AS DEFAULT_VALUE,
                RF.RDB$DESCRIPTION AS DESCRIPTION,
                CASE F.RDB$FIELD_TYPE
                    WHEN 7 THEN 'SMALLINT'
                    WHEN 8 THEN 'INTEGER'
                    WHEN 9 THEN 'QUAD'
                    WHEN 10 THEN 'FLOAT'
                    WHEN 12 THEN 'DATE'
                    WHEN 13 THEN 'TIME'
                    WHEN 14 THEN 'CHAR'
                    WHEN 16 THEN 'BIGINT'
                    WHEN 27 THEN 'DOUBLE PRECISION'
                    WHEN 35 THEN 'TIMESTAMP'
                    WHEN 37 THEN 'VARCHAR'
                    WHEN 40 THEN 'CSTRING'
                    WHEN 45 THEN 'BLOB_ID'
                    WHEN 261 THEN 'BLOB'
                    ELSE 'UNKNOWN'
                END AS FIELD_TYPE
            FROM RDB$RELATION_FIELDS RF
            JOIN RDB$FIELDS F ON RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
            WHERE RF.RDB$RELATION_NAME = ?
            ORDER BY RF.RDB$FIELD_POSITION
        """

        try:
            results = self.execute_query(query, (table_name.upper(),))
            columns = []
            for row in results:
                field_type = (row.get("field_type") or "UNKNOWN").strip()
                field_length = row.get("field_length")

                # Montar tipo completo (ex: VARCHAR(100))
                if field_type in ("VARCHAR", "CHAR") and field_length:
                    type_display = f"{field_type}({field_length})"
                elif field_type == "NUMERIC" and row.get("field_precision"):
                    scale = abs(row.get("field_scale") or 0)
                    type_display = f"NUMERIC({row.get('field_precision')},{scale})"
                else:
                    type_display = field_type

                columns.append({
                    "name": (row.get("column_name") or "").strip(),
                    "type": type_display,
                    "type_code": row.get("field_type_code"),
                    "length": field_length,
                    "precision": row.get("field_precision"),
                    "scale": row.get("field_scale"),
                    "nullable": row.get("not_null") != 1,
                    "default": (row.get("default_value") or "").strip() if row.get("default_value") else None,
                    "description": (row.get("description") or "").strip() if row.get("description") else None,
                })
            return columns
        except FirebirdError as e:
            logger.error(f"Erro ao listar colunas de {table_name}: {e}")
            return []

    def get_table_primary_key(self, table_name: str) -> List[str]:
        """
        Retorna colunas da chave primária de uma tabela.

        Args:
            table_name: Nome da tabela

        Returns:
            Lista de nomes das colunas que formam a PK
        """
        if not self.is_available:
            return []

        query = """
            SELECT
                TRIM(ISG.RDB$FIELD_NAME) AS COLUMN_NAME
            FROM RDB$RELATION_CONSTRAINTS RC
            JOIN RDB$INDEX_SEGMENTS ISG ON RC.RDB$INDEX_NAME = ISG.RDB$INDEX_NAME
            WHERE RC.RDB$RELATION_NAME = ?
              AND RC.RDB$CONSTRAINT_TYPE = 'PRIMARY KEY'
            ORDER BY ISG.RDB$FIELD_POSITION
        """

        try:
            results = self.execute_query(query, (table_name.upper(),))
            return [(row.get("column_name") or "").strip() for row in results]
        except FirebirdError:
            return []

    def get_table_foreign_keys(self, table_name: str) -> List[Dict]:
        """
        Retorna foreign keys de uma tabela.

        Args:
            table_name: Nome da tabela

        Returns:
            Lista de FKs com coluna local, tabela referenciada e coluna referenciada
        """
        if not self.is_available:
            return []

        query = """
            SELECT
                TRIM(RC.RDB$CONSTRAINT_NAME) AS FK_NAME,
                TRIM(ISG.RDB$FIELD_NAME) AS LOCAL_COLUMN,
                TRIM(RC2.RDB$RELATION_NAME) AS REFERENCED_TABLE,
                TRIM(ISG2.RDB$FIELD_NAME) AS REFERENCED_COLUMN
            FROM RDB$RELATION_CONSTRAINTS RC
            JOIN RDB$INDEX_SEGMENTS ISG ON RC.RDB$INDEX_NAME = ISG.RDB$INDEX_NAME
            JOIN RDB$REF_CONSTRAINTS REFC ON RC.RDB$CONSTRAINT_NAME = REFC.RDB$CONSTRAINT_NAME
            JOIN RDB$RELATION_CONSTRAINTS RC2 ON REFC.RDB$CONST_NAME_UQ = RC2.RDB$CONSTRAINT_NAME
            JOIN RDB$INDEX_SEGMENTS ISG2 ON RC2.RDB$INDEX_NAME = ISG2.RDB$INDEX_NAME
            WHERE RC.RDB$RELATION_NAME = ?
              AND RC.RDB$CONSTRAINT_TYPE = 'FOREIGN KEY'
            ORDER BY RC.RDB$CONSTRAINT_NAME, ISG.RDB$FIELD_POSITION
        """

        try:
            results = self.execute_query(query, (table_name.upper(),))
            fks = []
            for row in results:
                fks.append({
                    "name": (row.get("fk_name") or "").strip(),
                    "local_column": (row.get("local_column") or "").strip(),
                    "referenced_table": (row.get("referenced_table") or "").strip(),
                    "referenced_column": (row.get("referenced_column") or "").strip(),
                })
            return fks
        except FirebirdError:
            return []

    def get_full_schema(self) -> Dict:
        """
        Retorna schema completo do banco (todas as tabelas com colunas).

        Returns:
            Dicionário com todas as tabelas, colunas, PKs e FKs
        """
        if not self.is_available:
            return {"error": "Firebird não disponível", "tables": []}

        tables = self.get_all_tables()
        schema = {
            "database": self.database,
            "host": self.host,
            "tables_count": len(tables),
            "tables": []
        }

        for table in tables:
            table_name = table["name"]
            table_info = {
                "name": table_name,
                "type": table["type"],
                "columns": self.get_table_columns(table_name),
                "primary_key": self.get_table_primary_key(table_name),
                "foreign_keys": self.get_table_foreign_keys(table_name),
            }
            schema["tables"].append(table_info)

        return schema

    def describe_table(self, table_name: str) -> Dict:
        """
        Descreve uma tabela específica (colunas, PKs, FKs).

        Args:
            table_name: Nome da tabela

        Returns:
            Dicionário com informações da tabela
        """
        if not self.is_available:
            return {"error": "Firebird não disponível"}

        return {
            "name": table_name.upper(),
            "columns": self.get_table_columns(table_name),
            "primary_key": self.get_table_primary_key(table_name),
            "foreign_keys": self.get_table_foreign_keys(table_name),
        }

    def search_tables(self, pattern: str) -> List[Dict]:
        """
        Busca tabelas pelo nome (suporta wildcards).

        Args:
            pattern: Padrão de busca (ex: 'ITEM%', '%PESSOA%')

        Returns:
            Lista de tabelas que correspondem ao padrão
        """
        if not self.is_available:
            return []

        query = """
            SELECT
                TRIM(RDB$RELATION_NAME) AS TABLE_NAME,
                CASE RDB$VIEW_SOURCE
                    WHEN NULL THEN 'TABLE'
                    ELSE 'VIEW'
                END AS TABLE_TYPE
            FROM RDB$RELATIONS
            WHERE RDB$SYSTEM_FLAG = 0
              AND RDB$RELATION_NAME NOT STARTING WITH 'RDB$'
              AND RDB$RELATION_NAME LIKE ?
            ORDER BY RDB$RELATION_NAME
        """

        try:
            results = self.execute_query(query, (pattern.upper(),))
            return [
                {
                    "name": (row.get("table_name") or "").strip(),
                    "type": (row.get("table_type") or "TABLE").strip(),
                }
                for row in results
            ]
        except FirebirdError:
            return []

    def execute_raw_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        Executa query SQL raw (apenas SELECT).

        ATENÇÃO: Use com cuidado! Apenas para consultas ad-hoc.

        Args:
            query: SQL SELECT
            params: Parâmetros

        Returns:
            Resultados como lista de dicionários
        """
        if not self.is_available:
            return []

        # Validar que é apenas SELECT
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            raise FirebirdError("Apenas queries SELECT são permitidas")

        return self.execute_query(query, params)


# Instância global (singleton)
firebird_client = FirebirdClient()


# Funções de conveniência
def get_products_from_legacy() -> List[Dict]:
    """Busca produtos do sistema legado."""
    return firebird_client.get_products()


def get_customer_from_legacy(phone: str) -> Optional[dict]:
    """Busca cliente do sistema legado por telefone."""
    return firebird_client.get_customer_by_phone(phone)


def get_customer_by_address(cep: str, numero: str) -> Optional[dict]:
    """Busca cliente do sistema legado por CEP + número."""
    return firebird_client.get_customer_by_address(cep, numero)


def is_firebird_available() -> bool:
    """Verifica se Firebird está disponível."""
    return firebird_client.is_available
