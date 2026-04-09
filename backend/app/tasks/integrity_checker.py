"""
IntegrityChecker — Verificação diária de inconsistências no banco de dados.

Detecta e registra:
- Pedidos PAID sem Delivery
- Pedidos DELIVERED sem pagamento registrado
- Clientes com telefone duplicado
- Entregas órfãs (sem pedido associado)
- Pedidos sem itens
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_integrity_check(db: AsyncSession) -> dict:
    """
    Executa todas as verificações de integridade.
    Retorna um dict com os resultados por categoria.
    """
    results = {}

    try:
        results["paid_orders_without_delivery"] = await _check_paid_orders_without_delivery(db)
    except Exception as e:
        logger.error(f"Erro em paid_orders_without_delivery: {e}")
        results["paid_orders_without_delivery"] = {"error": str(e)}

    try:
        results["delivered_orders_without_payment"] = await _check_delivered_without_payment(db)
    except Exception as e:
        logger.error(f"Erro em delivered_orders_without_payment: {e}")
        results["delivered_orders_without_payment"] = {"error": str(e)}

    try:
        results["duplicate_customer_phones"] = await _check_duplicate_phones(db)
    except Exception as e:
        logger.error(f"Erro em duplicate_customer_phones: {e}")
        results["duplicate_customer_phones"] = {"error": str(e)}

    try:
        results["orphan_deliveries"] = await _check_orphan_deliveries(db)
    except Exception as e:
        logger.error(f"Erro em orphan_deliveries: {e}")
        results["orphan_deliveries"] = {"error": str(e)}

    try:
        results["orders_without_items"] = await _check_orders_without_items(db)
    except Exception as e:
        logger.error(f"Erro em orders_without_items: {e}")
        results["orders_without_items"] = {"error": str(e)}

    total_issues = sum(
        v.get("count", 0) for v in results.values() if isinstance(v, dict) and "count" in v
    )
    results["summary"] = {
        "total_issues": total_issues,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if total_issues == 0 else "issues_found",
    }

    if total_issues > 0:
        logger.warning(f"[IntegrityCheck] {total_issues} inconsistências encontradas: {results}")
    else:
        logger.info("[IntegrityCheck] Nenhuma inconsistência encontrada.")

    return results


async def _check_paid_orders_without_delivery(db: AsyncSession) -> dict:
    """Pedidos com status PAID mas sem registro de Delivery."""
    result = await db.execute(text("""
        SELECT o.id, o.order_number, o.status, o.created_at
        FROM orders o
        LEFT JOIN deliveries d ON d.order_id = o.id
        WHERE o.status IN ('paid', 'approved', 'preparing', 'dispatched')
          AND d.id IS NULL
          AND o.deleted_at IS NULL
        ORDER BY o.created_at DESC
        LIMIT 50
    """))
    rows = result.fetchall()
    return {
        "count": len(rows),
        "items": [
            {"order_id": str(r[0]), "order_number": r[1], "status": r[2], "created_at": str(r[3])}
            for r in rows
        ],
    }


async def _check_delivered_without_payment(db: AsyncSession) -> dict:
    """Pedidos DELIVERED com payment_method != fiado e sem Payment confirmado."""
    result = await db.execute(text("""
        SELECT o.id, o.order_number, o.payment_method, o.total_amount
        FROM orders o
        LEFT JOIN payments p ON p.order_id = o.id AND p.status = 'confirmed'
        WHERE o.status = 'delivered'
          AND o.payment_method NOT IN ('fiado', 'boleto')
          AND p.id IS NULL
          AND o.deleted_at IS NULL
        ORDER BY o.created_at DESC
        LIMIT 50
    """))
    rows = result.fetchall()
    return {
        "count": len(rows),
        "items": [
            {
                "order_id": str(r[0]),
                "order_number": r[1],
                "payment_method": r[2],
                "total_amount": float(r[3]) if r[3] else None,
            }
            for r in rows
        ],
    }


async def _check_duplicate_phones(db: AsyncSession) -> dict:
    """Clientes com telefone duplicado (mais de um cadastro com mesmo phone)."""
    result = await db.execute(text("""
        SELECT phone, COUNT(*) as cnt, array_agg(id::text) as ids
        FROM customers
        WHERE phone IS NOT NULL
          AND deleted_at IS NULL
        GROUP BY phone
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 30
    """))
    rows = result.fetchall()
    return {
        "count": len(rows),
        "items": [
            {"phone": r[0], "count": r[1], "customer_ids": r[2]}
            for r in rows
        ],
    }


async def _check_orphan_deliveries(db: AsyncSession) -> dict:
    """Deliveries sem Order associada (order_id inválido)."""
    result = await db.execute(text("""
        SELECT d.id, d.status, d.created_at
        FROM deliveries d
        LEFT JOIN orders o ON o.id = d.order_id
        WHERE o.id IS NULL
        LIMIT 20
    """))
    rows = result.fetchall()
    return {
        "count": len(rows),
        "items": [
            {"delivery_id": str(r[0]), "status": r[1], "created_at": str(r[2])}
            for r in rows
        ],
    }


async def _check_orders_without_items(db: AsyncSession) -> dict:
    """Pedidos sem nenhum OrderItem."""
    result = await db.execute(text("""
        SELECT o.id, o.order_number, o.status, o.created_at
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status NOT IN ('cancelled')
          AND o.deleted_at IS NULL
          AND oi.id IS NULL
        ORDER BY o.created_at DESC
        LIMIT 30
    """))
    rows = result.fetchall()
    return {
        "count": len(rows),
        "items": [
            {"order_id": str(r[0]), "order_number": r[1], "status": r[2], "created_at": str(r[3])}
            for r in rows
        ],
    }


class IntegrityCheckerTask:
    """
    Task de verificação de integridade que roda periodicamente.
    Registra resultados e pode enviar alertas.
    """

    def __init__(self, interval_hours: int = 24):
        self.interval_hours = interval_hours
        self._task: asyncio.Task = None
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"[IntegrityChecker] Iniciado (intervalo: {self.interval_hours}h)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        # Aguarda 5 min após startup para não sobrecarregar a inicialização
        await asyncio.sleep(300)

        while self._running:
            try:
                from app.database import AsyncSessionLocal
                async with AsyncSessionLocal() as db:
                    await run_integrity_check(db)
            except Exception as e:
                logger.error(f"[IntegrityChecker] Erro na verificação: {e}", exc_info=True)

            await asyncio.sleep(self.interval_hours * 3600)


integrity_checker = IntegrityCheckerTask()
