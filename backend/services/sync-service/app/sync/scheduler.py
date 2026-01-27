"""
Módulos de sincronização entre Firebird e PostgreSQL.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.config import settings
from app.sync.firebird_client import firebird_client

logger = logging.getLogger(__name__)


class SyncDirection(str, Enum):
    """Direção da sincronização."""
    FIREBIRD_TO_POSTGRES = "firebird_to_postgres"
    POSTGRES_TO_FIREBIRD = "postgres_to_firebird"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, Enum):
    """Status de uma sincronização."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncResult:
    """Resultado de uma operação de sincronização."""

    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        self.status = SyncStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.records_processed = 0
        self.records_created = 0
        self.records_updated = 0
        self.records_failed = 0
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at and self.started_at
                else None
            ),
            "records_processed": self.records_processed,
            "records_created": self.records_created,
            "records_updated": self.records_updated,
            "records_failed": self.records_failed,
            "errors": self.errors[:10],  # Limitar erros
        }


# PostgreSQL async engine
_engine = None
_session_factory = None


def get_postgres_engine():
    """Retorna engine PostgreSQL."""
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine, _session_factory


async def get_redis() -> redis.Redis:
    """Retorna cliente Redis."""
    return redis.from_url(settings.redis_url)


# ==================== Sincronização de Produtos ====================

async def sync_products() -> SyncResult:
    """
    Sincroniza produtos do Firebird para PostgreSQL.

    - Busca produtos do Firebird
    - Compara com produtos existentes no PostgreSQL
    - Insere novos ou atualiza existentes
    """
    result = SyncResult("products")
    result.status = SyncStatus.RUNNING
    result.started_at = datetime.now(timezone.utc)

    try:
        if not firebird_client.is_available:
            result.status = SyncStatus.FAILED
            result.errors.append("Firebird não disponível")
            return result

        # Buscar produtos do Firebird
        fb_products = firebird_client.get_products()
        result.records_processed = len(fb_products)

        if not fb_products:
            result.status = SyncStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            return result

        # Conectar ao PostgreSQL
        _, session_factory = get_postgres_engine()

        async with session_factory() as session:
            for product in fb_products:
                try:
                    code = product.get("code")
                    if not code:
                        continue

                    # Verificar se existe
                    check_result = await session.execute(
                        text("SELECT id FROM products WHERE code = :code"),
                        {"code": code}
                    )
                    existing = check_result.fetchone()

                    if existing:
                        # Atualizar
                        await session.execute(
                            text("""
                                UPDATE products SET
                                    name = :name,
                                    price = :price,
                                    weight_kg = :weight,
                                    active = :active,
                                    updated_at = :updated_at
                                WHERE code = :code
                            """),
                            {
                                "code": code,
                                "name": product.get("name"),
                                "price": float(product.get("price", 0)),
                                "weight": product.get("weight_kg"),
                                "active": product.get("active", True),
                                "updated_at": datetime.now(timezone.utc),
                            }
                        )
                        result.records_updated += 1
                    else:
                        # Inserir
                        await session.execute(
                            text("""
                                INSERT INTO products (code, name, price, weight_kg, active, created_at)
                                VALUES (:code, :name, :price, :weight, :active, :created_at)
                            """),
                            {
                                "code": code,
                                "name": product.get("name"),
                                "price": float(product.get("price", 0)),
                                "weight": product.get("weight_kg"),
                                "active": product.get("active", True),
                                "created_at": datetime.now(timezone.utc),
                            }
                        )
                        result.records_created += 1

                except Exception as e:
                    result.records_failed += 1
                    result.errors.append(f"Produto {product.get('code')}: {str(e)}")

            await session.commit()

        result.status = SyncStatus.COMPLETED

    except Exception as e:
        result.status = SyncStatus.FAILED
        result.errors.append(str(e))
        logger.error(f"Erro na sincronização de produtos: {e}")

    result.completed_at = datetime.now(timezone.utc)
    return result


# ==================== Sincronização de Clientes ====================

async def sync_customers() -> SyncResult:
    """
    Sincroniza clientes do Firebird para PostgreSQL.
    """
    result = SyncResult("customers")
    result.status = SyncStatus.RUNNING
    result.started_at = datetime.now(timezone.utc)

    try:
        if not firebird_client.is_available:
            result.status = SyncStatus.FAILED
            result.errors.append("Firebird não disponível")
            return result

        fb_customers = firebird_client.get_customers()
        result.records_processed = len(fb_customers)

        if not fb_customers:
            result.status = SyncStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            return result

        _, session_factory = get_postgres_engine()

        async with session_factory() as session:
            for customer in fb_customers:
                try:
                    phone = customer.get("phone")
                    if not phone:
                        continue

                    # Normalizar telefone
                    phone = "".join(filter(str.isdigit, phone))
                    if len(phone) < 10:
                        continue

                    # Verificar se existe
                    check_result = await session.execute(
                        text("SELECT id FROM customers WHERE phone = :phone"),
                        {"phone": phone}
                    )
                    existing = check_result.fetchone()

                    address = customer.get("address", {})

                    if existing:
                        await session.execute(
                            text("""
                                UPDATE customers SET
                                    name = COALESCE(:name, name),
                                    email = COALESCE(:email, email),
                                    updated_at = :updated_at
                                WHERE phone = :phone
                            """),
                            {
                                "phone": phone,
                                "name": customer.get("name"),
                                "email": customer.get("email"),
                                "updated_at": datetime.now(timezone.utc),
                            }
                        )
                        result.records_updated += 1
                    else:
                        await session.execute(
                            text("""
                                INSERT INTO customers (phone, name, email, created_at)
                                VALUES (:phone, :name, :email, :created_at)
                            """),
                            {
                                "phone": phone,
                                "name": customer.get("name"),
                                "email": customer.get("email"),
                                "created_at": datetime.now(timezone.utc),
                            }
                        )
                        result.records_created += 1

                except Exception as e:
                    result.records_failed += 1
                    result.errors.append(f"Cliente {customer.get('phone')}: {str(e)}")

            await session.commit()

        result.status = SyncStatus.COMPLETED

    except Exception as e:
        result.status = SyncStatus.FAILED
        result.errors.append(str(e))
        logger.error(f"Erro na sincronização de clientes: {e}")

    result.completed_at = datetime.now(timezone.utc)
    return result


# ==================== Sincronização de Estoque ====================

async def sync_stock() -> SyncResult:
    """
    Sincroniza níveis de estoque do Firebird para PostgreSQL.
    """
    result = SyncResult("stock")
    result.status = SyncStatus.RUNNING
    result.started_at = datetime.now(timezone.utc)

    try:
        if not firebird_client.is_available:
            result.status = SyncStatus.FAILED
            result.errors.append("Firebird não disponível")
            return result

        stock_levels = firebird_client.get_stock_levels()
        result.records_processed = len(stock_levels)

        # Publicar eventos de atualização de estoque
        r = await get_redis()

        for item in stock_levels:
            try:
                await r.xadd(
                    "inventory:sync",
                    {
                        "type": "stock.update",
                        "product_code": item.get("product_code", ""),
                        "quantity": str(item.get("quantity", 0)),
                        "min_quantity": str(item.get("min_quantity", 0)),
                        "source": "firebird",
                    }
                )
                result.records_updated += 1

            except Exception as e:
                result.records_failed += 1
                result.errors.append(f"Estoque {item.get('product_code')}: {str(e)}")

        await r.close()
        result.status = SyncStatus.COMPLETED

    except Exception as e:
        result.status = SyncStatus.FAILED
        result.errors.append(str(e))
        logger.error(f"Erro na sincronização de estoque: {e}")

    result.completed_at = datetime.now(timezone.utc)
    return result


# ==================== Sincronização Completa ====================

async def run_full_sync() -> Dict[str, Any]:
    """
    Executa sincronização completa de todas as entidades.

    Chamado pelo scheduler ou manualmente via API.
    """
    logger.info("Iniciando sincronização completa")
    start_time = datetime.now(timezone.utc)

    results = {}

    # Sincronizar produtos
    results["products"] = (await sync_products()).to_dict()

    # Sincronizar clientes
    results["customers"] = (await sync_customers()).to_dict()

    # Sincronizar estoque
    results["stock"] = (await sync_stock()).to_dict()

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Salvar resultado no Redis
    try:
        r = await get_redis()
        await r.set(
            "sync:last_run",
            str({
                "timestamp": end_time.isoformat(),
                "duration_seconds": duration,
                "results": results,
            }),
            ex=86400  # 24h
        )
        await r.close()
    except Exception as e:
        logger.error(f"Erro ao salvar resultado da sincronização: {e}")

    logger.info(f"Sincronização completa finalizada em {duration:.2f}s")

    return {
        "started_at": start_time.isoformat(),
        "completed_at": end_time.isoformat(),
        "duration_seconds": duration,
        "results": results,
    }
