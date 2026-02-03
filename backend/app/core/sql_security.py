"""
Módulo de segurança para validação de queries SQL Firebird.

Implementa:
- Allowlist de tabelas permitidas para consultas
- Validação de queries raw para bloquear comandos perigosos
- Sanitização de nomes de tabelas
"""

import re
from typing import Set

from app.core.secure_logging import get_secure_logger

logger = get_secure_logger(__name__)


class SQLSecurityError(Exception):
    """Exceção para violações de segurança SQL."""
    pass


# Allowlist de tabelas permitidas para consulta direta via API
# Adicione tabelas conforme necessário
ALLOWED_TABLES: Set[str] = {
    # Tabelas de produtos e preços
    "ITEM",
    "ITEMPRECO",
    "ITEMSALDO",
    "ITEMBARRAS",
    "ITEMTAMANHO",

    # Tabelas de pessoas/clientes
    "PESSOA",
    "PESSOAFISICA",
    "PESSOAJURIDICA",
    "CLIENTE",

    # Tabelas de endereço e telefone
    "ENDERECO",
    "FONE",
    "BAIRRO",
    "CIDADE",
    "ESTADO",
    "PAIS",

    # Views de pessoa
    "VPESSOAJURIDICA",
    "VPESSOAFISICASIMPLES",

    # Tabelas de rotas e veículos
    "ROTA",
    "ROTAPESSOA",
    "VEICULO",

    # Tabelas de estoque
    "ESTLOCAL",
    "ESTTIPO",
    "ESTLOCALITEM",

    # Tabelas de movimentação
    "MOVEST",
    "MOVESTITEM",

    # Tabelas de preço
    "TIPOPRECO",
    "PRECOITEM",

    # Metadados do sistema Firebird (somente leitura)
    "RDB$RELATIONS",
    "RDB$RELATION_FIELDS",
    "RDB$FIELDS",
    "RDB$RELATION_CONSTRAINTS",
    "RDB$INDEX_SEGMENTS",
    "RDB$REF_CONSTRAINTS",
    "RDB$INDICES",
    "RDB$TRIGGERS",
    "RDB$PROCEDURES",
    "RDB$GENERATORS",
}


# Palavras-chave SQL que indicam operações perigosas
DANGEROUS_KEYWORDS: Set[str] = {
    # DML perigoso
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",

    # DDL
    "DROP",
    "CREATE",
    "ALTER",
    "TRUNCATE",

    # DCL
    "GRANT",
    "REVOKE",

    # Execução de código
    "EXECUTE",
    "EXEC",

    # Operadores que podem ser usados para exfiltração
    "UNION",
    "INTO",

    # Comentários (podem ser usados para bypass)
    "--",
    "/*",
    "*/",
}

# Caracteres que indicam múltiplas queries
STATEMENT_SEPARATORS = {";"}


def validate_table_name(table_name: str) -> str:
    """
    Valida e sanitiza nome de tabela.

    Args:
        table_name: Nome da tabela a validar

    Returns:
        Nome da tabela em uppercase se válido

    Raises:
        SQLSecurityError se tabela não permitida ou nome inválido

    Examples:
        >>> validate_table_name("ITEM")
        'ITEM'

        >>> validate_table_name("ITEM; DROP TABLE")
        SQLSecurityError: Nome de tabela inválido
    """
    if not table_name:
        raise SQLSecurityError("Nome de tabela não pode ser vazio")

    # Remover espaços e converter para uppercase
    clean_name = table_name.strip().upper()

    # Validar caracteres (apenas alfanuméricos, underscore e $ para tabelas de sistema)
    if not re.match(r'^[A-Z][A-Z0-9_$]*$', clean_name):
        logger.warning(f"Tentativa de acesso com nome de tabela inválido: {table_name}")
        raise SQLSecurityError(f"Nome de tabela inválido: caracteres não permitidos")

    # Verificar comprimento máximo (nomes Firebird limitados a 31 caracteres)
    if len(clean_name) > 31:
        raise SQLSecurityError("Nome de tabela muito longo (máximo 31 caracteres)")

    # Verificar se está na allowlist
    if clean_name not in ALLOWED_TABLES:
        logger.warning(f"Tentativa de acesso a tabela não permitida: {clean_name}")
        raise SQLSecurityError(
            f"Tabela '{clean_name}' não está na lista de tabelas permitidas. "
            f"Contate o administrador para solicitar acesso."
        )

    return clean_name


def validate_raw_query(query: str) -> str:
    """
    Valida query SQL raw para execução segura.

    Verifica:
    - Deve começar com SELECT
    - Não pode conter palavras-chave perigosas (INSERT, DROP, etc.)
    - Não pode conter separadores de statement (;)
    - Não pode conter comentários SQL

    Args:
        query: Query SQL a validar

    Returns:
        Query validada (inalterada) se segura

    Raises:
        SQLSecurityError se query contém elementos perigosos

    Examples:
        >>> validate_raw_query("SELECT * FROM ITEM")
        'SELECT * FROM ITEM'

        >>> validate_raw_query("SELECT * FROM ITEM; DROP TABLE ITEM")
        SQLSecurityError: Query contém separador de statement não permitido
    """
    if not query:
        raise SQLSecurityError("Query não pode ser vazia")

    query_upper = query.strip().upper()

    # Deve começar com SELECT
    if not query_upper.startswith("SELECT"):
        logger.warning(f"Query bloqueada: não começa com SELECT")
        raise SQLSecurityError("Apenas queries SELECT são permitidas")

    # Verificar separadores de statement (múltiplas queries)
    for separator in STATEMENT_SEPARATORS:
        if separator in query:
            logger.warning(f"Query bloqueada: contém separador '{separator}'")
            raise SQLSecurityError(
                f"Query contém separador de statement não permitido: {separator}"
            )

    # Verificar palavras-chave perigosas
    for keyword in DANGEROUS_KEYWORDS:
        # Para comentários, verificar presença direta
        if keyword in ["--", "/*", "*/"]:
            if keyword in query:
                logger.warning(f"Query bloqueada: contém comentário SQL")
                raise SQLSecurityError(f"Query contém elemento não permitido: {keyword}")
        else:
            # Para palavras-chave, usar word boundary para evitar falsos positivos
            # Ex: "SELECTED" não deve dar match com "SELECT"
            pattern = rf'\b{keyword}\b'
            if re.search(pattern, query_upper):
                logger.warning(f"Query bloqueada: contém palavra-chave '{keyword}'")
                raise SQLSecurityError(f"Query contém palavra-chave não permitida: {keyword}")

    return query


def is_table_allowed(table_name: str) -> bool:
    """
    Verifica se uma tabela está na allowlist.

    Args:
        table_name: Nome da tabela a verificar

    Returns:
        True se tabela permitida, False caso contrário
    """
    return table_name.strip().upper() in ALLOWED_TABLES


def add_table_to_allowlist(table_name: str) -> None:
    """
    Adiciona tabela à allowlist em runtime.

    Útil para configuração dinâmica, mas alterações
    não persistem após reinício.

    Args:
        table_name: Nome da tabela a adicionar
    """
    clean_name = table_name.strip().upper()
    ALLOWED_TABLES.add(clean_name)
    logger.info(f"Tabela adicionada à allowlist: {clean_name}")


def get_allowed_tables() -> Set[str]:
    """
    Retorna cópia da allowlist de tabelas.

    Returns:
        Set com nomes das tabelas permitidas
    """
    return ALLOWED_TABLES.copy()
