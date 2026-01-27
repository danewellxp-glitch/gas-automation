"""
Serviço de exportação de pedidos para o Firebird (ERP legado).

Implementa exportação do PostgreSQL (orders/order_items) → Firebird (TRADE/TRADEITEM),
com idempotência básica (salva firebird_trade_id no pedido) e log de erro no próprio pedido.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import anyio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.integrations.firebird import firebird_client
from app.models.customer import Customer
from app.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)


try:
    import fdb  # type: ignore
    _FDB_AVAILABLE = True
except ImportError:
    _FDB_AVAILABLE = False


class FirebirdExportError(Exception):
    pass


@dataclass(frozen=True)
class _OrderSnapshotItem:
    product_code: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


@dataclass(frozen=True)
class _OrderSnapshot:
    order_id: UUID
    order_number: int
    created_at: datetime
    total_amount: Decimal
    payment_method: Optional[str]
    tipo_operacao: str
    notes: str
    customer_id: UUID
    customer_phone: str
    customer_firebird_id: Optional[int]
    items: list[_OrderSnapshotItem]


class FirebirdOrderExporter:
    """
    Exporta pedidos para o Firebird usando fdb.

    Observação: depende de schema Firebird com tabelas TRADE e TRADEITEM (configuráveis).
    """

    @property
    def is_available(self) -> bool:
        return _FDB_AVAILABLE and settings.firebird_enabled

    def _dsn(self) -> str:
        return f"{settings.firebird_host}/3050:{settings.firebird_database}"

    @contextmanager
    def _connect(self):
        if not self.is_available:
            raise FirebirdExportError("Firebird não está configurado ou biblioteca fdb indisponível")
        conn = None
        try:
            conn = fdb.connect(
                dsn=self._dsn(),
                user=settings.firebird_user,
                password=settings.firebird_password,
                charset=settings.firebird_charset,
            )
            yield conn
        finally:
            if conn:
                conn.close()

    def _get_table_columns(self, conn, table_name: str) -> set[str]:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT TRIM(rf.RDB$FIELD_NAME) AS field_name
                FROM RDB$RELATION_FIELDS rf
                WHERE rf.RDB$RELATION_NAME = ?
                """,
                (table_name.upper(),),
            )
            return {str(row[0]).upper() for row in cur.fetchall() if row and row[0]}
        finally:
            cur.close()

    def _coerce_flag(self, value: Any, columns: set[str], column_name: str) -> Any:
        """
        Tenta normalizar flags comuns (S/N, 1/0, True/False).
        Não há como inferir o tipo sem ler metadados de domínio; aqui só normalizamos strings.
        """
        if column_name.upper() not in columns:
            return None
        if value is None:
            return None
        if isinstance(value, str):
            v = value.strip()
            if v in {"S", "N"}:
                return v
            if v in {"1", "0"}:
                return int(v)
        return value

    def _map_product_code(self, code: str) -> list[str]:
        """
        Gera variações do código para tentar localizar no Firebird.
        Ex: P13 -> [P13, P-13]
        """
        code = (code or "").strip().upper()
        if not code:
            return []
        variants = [code]
        if len(code) >= 3 and code[0] == "P" and code[1:].isdigit():
            variants.append(f"P-{code[1:]}")
        return list(dict.fromkeys(variants))

    def _resolve_customer_firebird_id(self, phone: str, existing_id: Optional[int]) -> Optional[int]:
        if existing_id:
            return existing_id
        customer = firebird_client.get_customer_by_phone(phone)
        if not customer:
            return None
        return customer.get("firebird_id")

    def _resolve_product_firebird_id(self, product_code: str) -> Optional[int]:
        for variant in self._map_product_code(product_code):
            prod = firebird_client.get_product_by_code(variant)
            if prod and prod.get("firebird_id"):
                return int(prod["firebird_id"])
        return None

    def export_snapshot(self, snap: _OrderSnapshot) -> tuple[int, Optional[int]]:
        """
        Executa exportação no Firebird (sincrono).

        Returns:
            (trade_id, resolved_customer_firebird_id)
        """
        if not self.is_available:
            raise FirebirdExportError("Firebird não disponível para exportação")

        trade_table = settings.firebird_trade_table.upper()
        trade_item_table = settings.firebird_trade_item_table.upper()

        resolved_customer_id = self._resolve_customer_firebird_id(snap.customer_phone, snap.customer_firebird_id)
        if not resolved_customer_id:
            raise FirebirdExportError("Cliente não possui firebird_id e não foi encontrado no Firebird pelo telefone")

        with self._connect() as conn:
            trade_cols = self._get_table_columns(conn, trade_table)
            item_cols = self._get_table_columns(conn, trade_item_table)

            # Montar insert TRADE com colunas existentes
            trade_values: dict[str, Any] = {}
            if "PESSOA_ID" in trade_cols:
                trade_values["PESSOA_ID"] = resolved_customer_id
            if "DTEMISSAO" in trade_cols:
                trade_values["DTEMISSAO"] = snap.created_at
            if "DTMOVTO" in trade_cols:
                trade_values["DTMOVTO"] = snap.created_at
            if "TOTAL" in trade_cols:
                trade_values["TOTAL"] = snap.total_amount
            if "CANCELADA" in trade_cols:
                trade_values["CANCELADA"] = self._coerce_flag("N", trade_cols, "CANCELADA") or "N"
            if "BXESTOQUE" in trade_cols:
                trade_values["BXESTOQUE"] = (
                    self._coerce_flag(settings.firebird_trade_bxestoque, trade_cols, "BXESTOQUE")
                    or self._coerce_flag("N", trade_cols, "BXESTOQUE")
                    or "N"
                )
            if "BXFINANC" in trade_cols:
                trade_values["BXFINANC"] = (
                    self._coerce_flag(settings.firebird_trade_bxfinanc, trade_cols, "BXFINANC")
                    or self._coerce_flag("N", trade_cols, "BXFINANC")
                    or "N"
                )
            if settings.firebird_trade_estab_id is not None and "ESTAB_ID" in trade_cols:
                trade_values["ESTAB_ID"] = int(settings.firebird_trade_estab_id)
            if settings.firebird_trade_tipomovest_id is not None and "TIPOMOVEST_ID" in trade_cols:
                trade_values["TIPOMOVEST_ID"] = int(settings.firebird_trade_tipomovest_id)
            if "ENTSAI" in trade_cols:
                # Saída (venda). Alguns schemas usam 'S' para saída.
                trade_values["ENTSAI"] = "S"
            if "OBS" in trade_cols:
                trade_values["OBS"] = (snap.notes or "")[:500]

            if not trade_values:
                raise FirebirdExportError(f"Não foi possível montar insert em {trade_table} (sem colunas compatíveis)")

            trade_cols_sql = ", ".join(trade_values.keys())
            trade_placeholders = ", ".join(["?"] * len(trade_values))
            returning = " RETURNING ID" if "ID" in trade_cols else ""

            cur = conn.cursor()
            try:
                cur.execute(
                    f"INSERT INTO {trade_table} ({trade_cols_sql}) VALUES ({trade_placeholders}){returning}",
                    tuple(trade_values.values()),
                )
                if "ID" in trade_cols:
                    row = cur.fetchone()
                    if not row or row[0] is None:
                        raise FirebirdExportError("Firebird não retornou ID do TRADE")
                    trade_id = int(row[0])
                else:
                    # Sem RETURNING, tentar buscar por último valor (não garantido). Falhar explicitamente.
                    raise FirebirdExportError("Tabela TRADE não possui coluna ID (ou RETURNING não suportado)")

                # Inserir itens
                seq = 1
                for it in snap.items:
                    item_id = self._resolve_product_firebird_id(it.product_code)
                    if not item_id:
                        raise FirebirdExportError(f"Produto não encontrado no Firebird: {it.product_code}")

                    item_values: dict[str, Any] = {}
                    if "TRADE_ID" in item_cols:
                        item_values["TRADE_ID"] = trade_id
                    if "ITEM_ID" in item_cols:
                        item_values["ITEM_ID"] = item_id
                    if "QUANTIDADE" in item_cols:
                        item_values["QUANTIDADE"] = it.quantity
                    if "PRECOTABELA" in item_cols:
                        item_values["PRECOTABELA"] = it.unit_price
                    if "TOTAL" in item_cols:
                        item_values["TOTAL"] = it.subtotal
                    if settings.firebird_trade_estlocal_id is not None and "ESTLOCAL_ID" in item_cols:
                        item_values["ESTLOCAL_ID"] = int(settings.firebird_trade_estlocal_id)
                    if "SEQUENCIA" in item_cols:
                        item_values["SEQUENCIA"] = seq

                    if not item_values:
                        raise FirebirdExportError(
                            f"Não foi possível montar insert em {trade_item_table} (sem colunas compatíveis)"
                        )

                    cols_sql = ", ".join(item_values.keys())
                    placeholders = ", ".join(["?"] * len(item_values))
                    cur.execute(
                        f"INSERT INTO {trade_item_table} ({cols_sql}) VALUES ({placeholders})",
                        tuple(item_values.values()),
                    )
                    seq += 1

                conn.commit()
                return trade_id, resolved_customer_id

            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()


exporter = FirebirdOrderExporter()


async def export_order_to_firebird(order_id: UUID) -> int:
    """
    Exporta pedido para Firebird e atualiza flags no PostgreSQL.

    Returns:
        trade_id do Firebird.
    """
    async with AsyncSessionLocal() as session:
        # Buscar pedido completo
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items),
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise FirebirdExportError("Pedido não encontrado")

        # Idempotência básica
        if order.firebird_trade_id:
            return int(order.firebird_trade_id)

        # Validar status (exportar normalmente quando entregue)
        if order.status != OrderStatus.DELIVERED.value:
            raise FirebirdExportError(f"Pedido precisa estar 'delivered' para exportar (status atual: {order.status})")

        customer: Customer = order.customer
        if not customer:
            raise FirebirdExportError("Pedido sem cliente carregado")

        snap = _OrderSnapshot(
            order_id=order.id,
            order_number=order.order_number,
            created_at=order.created_at,
            total_amount=order.total_amount,
            payment_method=order.payment_method,
            tipo_operacao=order.tipo_operacao,
            notes=order.notes or "",
            customer_id=customer.id,
            customer_phone=customer.phone,
            customer_firebird_id=customer.firebird_id,
            items=[
                _OrderSnapshotItem(
                    product_code=i.product_code,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    subtotal=i.subtotal,
                )
                for i in order.items
            ],
        )

        # Marcar tentativa
        order.firebird_export_attempts = int(order.firebird_export_attempts or 0) + 1
        await session.flush()

        try:
            trade_id, resolved_customer_id = await anyio.to_thread.run_sync(exporter.export_snapshot, snap)

            # Persistir IDs e status
            if resolved_customer_id and not customer.firebird_id:
                customer.firebird_id = int(resolved_customer_id)

            order.firebird_trade_id = int(trade_id)
            order.firebird_export_status = "exported"
            order.firebird_exported_at = datetime.now(timezone.utc)
            order.firebird_export_error = None

            await session.commit()
            return int(trade_id)

        except Exception as e:
            logger.error(f"Falha ao exportar pedido {order_id} para Firebird: {e}")
            order.firebird_export_status = "failed"
            order.firebird_export_error = str(e)
            await session.commit()
            raise

