"""Serviço de Conciliação PIX com Asaas."""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.financeiro.pix_conciliation import PixConciliationItem, PixConciliationRun
from app.models.financeiro.transaction import Transaction
from app.models.payment import Payment

logger = logging.getLogger(__name__)

RESULTADO_CONCILIADO = "conciliado"
RESULTADO_DIVERGENCIA = "divergencia_valor"
RESULTADO_APENAS_ASAAS = "apenas_asaas"
RESULTADO_APENAS_LOCAL = "apenas_local"

TOLERANCE = Decimal("0.01")


class PixConciliationService:

    async def fetch_asaas_pix_payments(self, target_date: date) -> list[dict[str, Any]]:
        """Busca pagamentos PIX recebidos no Asaas para a data informada."""
        if not settings.asaas_api_key:
            logger.warning("asaas_api_key não configurada — retornando lista vazia")
            return []

        date_str = target_date.isoformat()
        params = {
            "billingType": "PIX",
            "dateCreated[ge]": date_str,
            "dateCreated[le]": date_str,
            "status": "RECEIVED",
            "limit": 100,
        }
        headers = {"access_token": settings.asaas_api_key}
        url = settings.asaas_api_url.rstrip("/") + "/payments"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                payments = data.get("data", [])
                return [
                    {
                        "id": p.get("id"),
                        "value": p.get("value"),
                        "payerName": p.get("payer", {}).get("name") if isinstance(p.get("payer"), dict) else p.get("payerName"),
                        "paymentDate": p.get("paymentDate"),
                        "status": p.get("status"),
                    }
                    for p in payments
                ]
        except Exception as exc:
            logger.error(f"Erro ao buscar pagamentos Asaas: {exc}", exc_info=True)
            return []

    async def run_daily_conciliation(self, db: AsyncSession, target_date: date) -> dict[str, Any]:
        """Executa conciliação PIX para a data e persiste o resultado."""
        asaas_payments = await self.fetch_asaas_pix_payments(target_date)

        # Busca Transactions locais de venda_gas pagas na data
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.category == "venda_gas",
                    Transaction.is_paid == True,
                    Transaction.reference_date == target_date,
                    Transaction.deleted_at == None,
                )
            )
        )
        local_transactions: list[Transaction] = result.scalars().all()

        # Monta mapa asaas_payment_id → Payment local (via payments table)
        asaas_id_to_payment: dict[str, Payment] = {}
        if local_transactions:
            order_ids = [t.order_id for t in local_transactions if t.order_id]
            if order_ids:
                pay_result = await db.execute(
                    select(Payment).where(
                        and_(
                            Payment.order_id.in_(order_ids),
                            Payment.method == "PIX",
                        )
                    )
                )
                for p in pay_result.scalars().all():
                    if p.asaas_payment_id:
                        asaas_id_to_payment[p.asaas_payment_id] = p

        # Mapa order_id → Transaction
        order_id_to_transaction: dict[UUID, Transaction] = {
            t.order_id: t for t in local_transactions if t.order_id
        }

        # Mapa asaas_id → Transaction (via Payment)
        asaas_id_to_transaction: dict[str, Transaction] = {}
        for asaas_id, payment in asaas_id_to_payment.items():
            if payment.order_id in order_id_to_transaction:
                asaas_id_to_transaction[asaas_id] = order_id_to_transaction[payment.order_id]

        items: list[dict] = []

        # Processa payments do Asaas
        matched_transaction_ids: set[UUID] = set()
        for ap in asaas_payments:
            asaas_id = ap["id"]
            asaas_amount = Decimal(str(ap["value"])) if ap["value"] is not None else None
            payer_name = ap.get("payerName")
            paid_at_str = ap.get("paymentDate")
            paid_at = None
            if paid_at_str:
                try:
                    paid_at = datetime.fromisoformat(paid_at_str).replace(tzinfo=timezone.utc)
                except Exception:
                    paid_at = None

            if asaas_id in asaas_id_to_transaction:
                tx = asaas_id_to_transaction[asaas_id]
                matched_transaction_ids.add(tx.id)
                local_amount = tx.amount
                diferenca = (asaas_amount or Decimal("0")) - local_amount
                if abs(diferenca) <= TOLERANCE:
                    resultado = RESULTADO_CONCILIADO
                    diferenca = Decimal("0.00")
                else:
                    resultado = RESULTADO_DIVERGENCIA
                items.append({
                    "resultado": resultado,
                    "asaas_payment_id": asaas_id,
                    "asaas_amount": asaas_amount,
                    "asaas_payer_name": payer_name,
                    "asaas_paid_at": paid_at,
                    "transaction_id": tx.id,
                    "transaction_amount": local_amount,
                    "order_id": tx.order_id,
                    "diferenca": diferenca,
                })
            else:
                # Só no Asaas
                items.append({
                    "resultado": RESULTADO_APENAS_ASAAS,
                    "asaas_payment_id": asaas_id,
                    "asaas_amount": asaas_amount,
                    "asaas_payer_name": payer_name,
                    "asaas_paid_at": paid_at,
                    "transaction_id": None,
                    "transaction_amount": None,
                    "order_id": None,
                    "diferenca": asaas_amount or Decimal("0.00"),
                })

        # Transactions locais não encontradas no Asaas
        for tx in local_transactions:
            if tx.id not in matched_transaction_ids:
                items.append({
                    "resultado": RESULTADO_APENAS_LOCAL,
                    "asaas_payment_id": None,
                    "asaas_amount": None,
                    "asaas_payer_name": None,
                    "asaas_paid_at": None,
                    "transaction_id": tx.id,
                    "transaction_amount": tx.amount,
                    "order_id": tx.order_id,
                    "diferenca": -(tx.amount),
                })

        # Totais
        total_asaas = len(asaas_payments)
        total_local = len(local_transactions)
        total_conciliado = sum(1 for i in items if i["resultado"] == RESULTADO_CONCILIADO)
        total_divergencia = sum(1 for i in items if i["resultado"] == RESULTADO_DIVERGENCIA)
        total_apenas_asaas = sum(1 for i in items if i["resultado"] == RESULTADO_APENAS_ASAAS)
        total_apenas_local = sum(1 for i in items if i["resultado"] == RESULTADO_APENAS_LOCAL)
        valor_asaas = sum((i["asaas_amount"] or Decimal("0")) for i in items if i["asaas_amount"])
        valor_local = sum((i["transaction_amount"] or Decimal("0")) for i in items if i["transaction_amount"])

        # Persiste run
        run = PixConciliationRun(
            conciliation_date=target_date,
            run_at=datetime.now(timezone.utc),
            total_asaas=total_asaas,
            total_local=total_local,
            total_conciliado=total_conciliado,
            total_divergencia=total_divergencia,
            total_apenas_asaas=total_apenas_asaas,
            total_apenas_local=total_apenas_local,
            valor_asaas=Decimal(str(valor_asaas)),
            valor_local=Decimal(str(valor_local)),
            status="pendente_revisao",
        )
        db.add(run)
        await db.flush()

        # Persiste items
        for item_data in items:
            item = PixConciliationItem(
                run_id=run.id,
                **item_data,
            )
            db.add(item)

        await db.commit()
        await db.refresh(run)
        return {"run": run, "items": items}

    async def get_or_run_conciliation(self, db: AsyncSession, target_date: date) -> PixConciliationRun:
        """Retorna conciliação existente para a data ou executa uma nova."""
        result = await db.execute(
            select(PixConciliationRun).where(
                PixConciliationRun.conciliation_date == target_date
            ).order_by(PixConciliationRun.run_at.desc()).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        data = await self.run_daily_conciliation(db, target_date)
        return data["run"]

    async def aprovar_run(self, db: AsyncSession, run_id: UUID, user_id: UUID) -> PixConciliationRun:
        """Aprova o fechamento de uma conciliação."""
        result = await db.execute(
            select(PixConciliationRun).where(PixConciliationRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError(f"Conciliação {run_id} não encontrada")
        run.aprovado_por = user_id
        run.aprovado_at = datetime.now(timezone.utc)
        run.status = "aprovado"
        await db.commit()
        await db.refresh(run)
        return run

    async def resolver_item(
        self, db: AsyncSession, item_id: UUID, user_id: UUID, observacao: str
    ) -> PixConciliationItem:
        """Marca um item divergente como resolvido."""
        result = await db.execute(
            select(PixConciliationItem).where(PixConciliationItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError(f"Item {item_id} não encontrado")
        item.resolvido = True
        item.resolvido_por = user_id
        item.observacao = observacao
        await db.commit()
        await db.refresh(item)
        return item
