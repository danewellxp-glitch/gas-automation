"""
API para exploração do schema Firebird.

Endpoints para visualizar tabelas, colunas e estrutura do banco legado.
Somente leitura - não modifica dados.

Segurança:
- Validação de nomes de tabela via allowlist
- Bloqueio de queries perigosas (INSERT, DROP, UNION, etc.)
"""

import logging
from typing import Optional, List, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user
from app.models.auth_models import User
from app.integrations.firebird import firebird_client, FirebirdError
from app.core.sql_security import (
    validate_table_name,
    validate_raw_query,
    SQLSecurityError,
    get_allowed_tables,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schemas ====================

class TableInfo(BaseModel):
    name: str
    type: str
    description: Optional[str] = None


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    default: Optional[str] = None
    description: Optional[str] = None


class ForeignKeyInfo(BaseModel):
    name: str
    local_column: str
    referenced_table: str
    referenced_column: str


class TableDetailResponse(BaseModel):
    name: str
    columns: List[ColumnInfo]
    primary_key: List[str]
    foreign_keys: List[ForeignKeyInfo]


# ==================== Endpoints ====================

@router.get("/status")
async def firebird_status(
    current_user: User = Depends(get_current_user),
):
    """
    Verifica status da conexão com Firebird.
    """
    is_configured = firebird_client.is_configured
    is_available = firebird_client.is_available

    if not is_configured:
        return {
            "status": "not_configured",
            "message": "Firebird não está configurado. Configure FIREBIRD_HOST e FIREBIRD_DATABASE.",
            "host": None,
            "database": None,
        }

    if not is_available:
        return {
            "status": "unavailable",
            "message": "Biblioteca fdb não instalada ou conexão indisponível.",
            "host": firebird_client.host,
            "database": firebird_client.database,
        }

    # Testar conexão
    try:
        connected = firebird_client.test_connection()
        if connected:
            return {
                "status": "connected",
                "message": "Conexão com Firebird OK",
                "host": firebird_client.host,
                "database": firebird_client.database,
            }
        else:
            return {
                "status": "error",
                "message": "Falha ao conectar com Firebird",
                "host": firebird_client.host,
                "database": firebird_client.database,
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "host": firebird_client.host,
            "database": firebird_client.database,
        }


@router.get("/tables", response_model=List[TableInfo])
async def list_tables(
    current_user: User = Depends(get_current_user),
):
    """
    Lista todas as tabelas do banco Firebird.
    """
    if not firebird_client.is_available:
        raise HTTPException(
            status_code=503,
            detail="Firebird não está disponível"
        )

    try:
        tables = firebird_client.get_all_tables()
        return tables
    except FirebirdError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/search")
async def search_tables(
    pattern: str = Query(..., description="Padrão de busca (ex: ITEM%, %PESSOA%)"),
    current_user: User = Depends(get_current_user),
):
    """
    Busca tabelas pelo nome.
    Use % como wildcard.
    """
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    try:
        tables = firebird_client.search_tables(pattern)
        return {"pattern": pattern, "count": len(tables), "tables": tables}
    except FirebirdError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}", response_model=TableDetailResponse)
async def describe_table(
    table_name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Retorna detalhes de uma tabela específica (colunas, PKs, FKs).
    """
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    try:
        info = firebird_client.describe_table(table_name)
        if not info.get("columns"):
            raise HTTPException(
                status_code=404,
                detail=f"Tabela {table_name} não encontrada"
            )
        return info
    except FirebirdError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/data")
async def preview_table_data(
    table_name: str,
    limit: int = Query(10, ge=1, le=100, description="Limite de linhas"),
    current_user: User = Depends(get_current_user),
):
    """
    Preview dos dados de uma tabela (primeiras N linhas).

    Segurança: Apenas tabelas na allowlist são acessíveis.
    """
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    try:
        # Validar nome da tabela via allowlist (prevenir SQL injection)
        safe_table_name = validate_table_name(table_name)

        # Query segura com nome validado
        # FIRST é específico do Firebird para LIMIT
        query = f"SELECT FIRST {limit} * FROM {safe_table_name}"
        data = firebird_client.execute_query(query)

        return {
            "table": safe_table_name,
            "rows_returned": len(data),
            "limit": limit,
            "data": data,
        }
    except SQLSecurityError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FirebirdError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/allowed")
async def list_allowed_tables(
    current_user: User = Depends(get_current_user),
):
    """
    Lista tabelas permitidas para consulta via API.

    Apenas tabelas nesta lista podem ser acessadas via /tables/{name}/data.
    """
    allowed = sorted(get_allowed_tables())
    return {
        "count": len(allowed),
        "tables": allowed,
        "note": "Apenas estas tabelas podem ser acessadas via preview de dados"
    }


@router.get("/schema/full")
async def get_full_schema(
    current_user: User = Depends(get_current_user),
):
    """
    Retorna schema completo do banco (todas as tabelas com colunas).

    ATENÇÃO: Pode ser lento em bancos grandes!
    """
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    try:
        schema = firebird_client.get_full_schema()
        return schema
    except FirebirdError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def execute_query(
    query: str = Query(..., description="Query SELECT a executar"),
    current_user: User = Depends(get_current_user),
):
    """
    Executa query SQL (apenas SELECT com validação de segurança).

    Segurança:
    - Apenas SELECT permitido
    - Bloqueia UNION, INTO, comentários SQL
    - Bloqueia múltiplas queries (;)
    """
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    try:
        # Validar query com regras de segurança rigorosas
        safe_query = validate_raw_query(query)

        results = firebird_client.execute_query(safe_query)
        return {
            "query": query,
            "rows_returned": len(results),
            "data": results,
        }
    except SQLSecurityError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FirebirdError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Dados do Sistema ====================

@router.get("/data/products")
async def list_firebird_products(
    current_user: User = Depends(get_current_user),
):
    """Lista produtos do Firebird."""
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    products = firebird_client.get_products()
    return {"count": len(products), "products": products}


@router.get("/data/stock")
async def list_firebird_stock(
    current_user: User = Depends(get_current_user),
):
    """Lista estoque do Firebird."""
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    stock = firebird_client.get_stock_levels()
    return {"count": len(stock), "stock": stock}


@router.get("/data/routes")
async def list_firebird_routes(
    current_user: User = Depends(get_current_user),
):
    """Lista rotas do Firebird."""
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    routes = firebird_client.get_routes()
    return {"count": len(routes), "routes": routes}


@router.get("/data/vehicles")
async def list_firebird_vehicles(
    current_user: User = Depends(get_current_user),
):
    """Lista veículos do Firebird."""
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    vehicles = firebird_client.get_vehicles()
    return {"count": len(vehicles), "vehicles": vehicles}


@router.get("/data/customer/{phone}")
async def get_firebird_customer(
    phone: str,
    current_user: User = Depends(get_current_user),
):
    """Busca cliente por telefone no Firebird."""
    if not firebird_client.is_available:
        raise HTTPException(status_code=503, detail="Firebird não disponível")

    customer = firebird_client.get_customer_by_phone(phone)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return customer
