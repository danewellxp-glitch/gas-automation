"""Serviço de Estoque de Vasilhames."""
import logging
from datetime import date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financeiro.vasilhame_estoque import VasilhameEstoque, VasilhameMovimento

logger = logging.getLogger(__name__)

TIPOS_VALIDOS = {"P13", "P20", "P45", "G20L"}


class VasilhameService:

    async def _get_estoque_lock(self, db: AsyncSession, tipo_str: str) -> VasilhameEstoque:
        """SELECT FOR UPDATE do estoque, criando registro se não existir."""
        if tipo_str not in TIPOS_VALIDOS:
            raise ValueError(f"Tipo de vasilhame inválido: {tipo_str}. Válidos: {TIPOS_VALIDOS}")

        result = await db.execute(
            select(VasilhameEstoque)
            .where(VasilhameEstoque.tipo == tipo_str)
            .with_for_update()
        )
        estoque = result.scalar_one_or_none()
        if not estoque:
            estoque = VasilhameEstoque(
                tipo=tipo_str,
                qtd_cheios=0,
                qtd_vazios=0,
                qtd_em_campo=0,
                custo_unitario=Decimal("0.00"),
            )
            db.add(estoque)
            await db.flush()
        return estoque

    def _snapshot(self, estoque: VasilhameEstoque) -> dict:
        return {
            "saldo_cheios_antes": estoque.qtd_cheios,
            "saldo_vazios_antes": estoque.qtd_vazios,
            "saldo_em_campo_antes": estoque.qtd_em_campo,
        }

    async def registrar_entrada_compra(
        self,
        db: AsyncSession,
        tipo: str,
        quantidade: int,
        custo_unitario: Decimal,
        user_id: Optional[UUID],
        purchase_order_id: Optional[UUID] = None,
    ) -> VasilhameMovimento:
        """Entrada por compra: incrementa cheios, recalcula custo médio ponderado."""
        estoque = await self._get_estoque_lock(db, tipo)
        snap = self._snapshot(estoque)

        # Custo médio ponderado
        total_atual = estoque.qtd_cheios * estoque.custo_unitario
        total_novo = quantidade * custo_unitario
        nova_qty = estoque.qtd_cheios + quantidade
        if nova_qty > 0:
            estoque.custo_unitario = (total_atual + total_novo) / nova_qty
        estoque.qtd_cheios = nova_qty

        custo_total = quantidade * custo_unitario

        mov = VasilhameMovimento(
            tipo_vasilhame=tipo,
            tipo_movimento="entrada_compra",
            quantidade=quantidade,
            custo_unitario=custo_unitario,
            custo_total=custo_total,
            pedido_id=purchase_order_id,
            created_by=user_id,
            **snap,
        )
        db.add(mov)
        await db.flush()
        return mov

    async def registrar_saida_venda(
        self,
        db: AsyncSession,
        tipo: str,
        quantidade: int,
        pedido_id: Optional[UUID],
        user_id: Optional[UUID],
    ) -> VasilhameMovimento:
        """Saída para venda: decrementa cheios, incrementa em_campo."""
        estoque = await self._get_estoque_lock(db, tipo)
        if estoque.qtd_cheios < quantidade:
            logger.warning(
                f"Saldo insuficiente de cheios para {tipo}: tem {estoque.qtd_cheios}, solicitado {quantidade}"
            )
        snap = self._snapshot(estoque)

        estoque.qtd_cheios = max(0, estoque.qtd_cheios - quantidade)
        estoque.qtd_em_campo += quantidade

        mov = VasilhameMovimento(
            tipo_vasilhame=tipo,
            tipo_movimento="saida_venda",
            quantidade=quantidade,
            pedido_id=pedido_id,
            created_by=user_id,
            **snap,
        )
        db.add(mov)
        await db.flush()
        return mov

    async def registrar_retorno_vazio(
        self,
        db: AsyncSession,
        tipo: str,
        quantidade: int,
        pedido_id: Optional[UUID],
        entregador_id: Optional[UUID],
        user_id: Optional[UUID],
    ) -> VasilhameMovimento:
        """Retorno de vazio pelo entregador: decrementa em_campo, incrementa vazios."""
        estoque = await self._get_estoque_lock(db, tipo)
        snap = self._snapshot(estoque)

        estoque.qtd_em_campo = max(0, estoque.qtd_em_campo - quantidade)
        estoque.qtd_vazios += quantidade

        mov = VasilhameMovimento(
            tipo_vasilhame=tipo,
            tipo_movimento="retorno_vazio",
            quantidade=quantidade,
            pedido_id=pedido_id,
            entregador_id=entregador_id,
            created_by=user_id,
            **snap,
        )
        db.add(mov)
        await db.flush()
        return mov

    async def registrar_perda(
        self,
        db: AsyncSession,
        tipo: str,
        quantidade: int,
        observacao: str,
        user_id: Optional[UUID],
    ) -> VasilhameMovimento:
        """Registra perda: reduz em_campo primeiro, depois cheios."""
        estoque = await self._get_estoque_lock(db, tipo)
        snap = self._snapshot(estoque)

        if estoque.qtd_em_campo >= quantidade:
            estoque.qtd_em_campo -= quantidade
        else:
            restante = quantidade - estoque.qtd_em_campo
            estoque.qtd_em_campo = 0
            estoque.qtd_cheios = max(0, estoque.qtd_cheios - restante)

        custo_total = quantidade * estoque.custo_unitario

        mov = VasilhameMovimento(
            tipo_vasilhame=tipo,
            tipo_movimento="perda",
            quantidade=quantidade,
            custo_unitario=estoque.custo_unitario,
            custo_total=custo_total,
            observacao=observacao,
            created_by=user_id,
            **snap,
        )
        db.add(mov)
        await db.flush()

        # Registra despesa financeira
        try:
            if custo_total > 0:
                from app.services.financeiro.financial_service import create_transaction
                from app.models.financeiro.transaction import TransactionType
                from sqlalchemy import select as sa_select
                from app.models.financeiro.account import Account

                acc_result = await db.execute(
                    sa_select(Account)
                    .where(Account.is_active == True, Account.deleted_at == None)
                    .limit(1)
                )
                account = acc_result.scalar_one_or_none()
                if account:
                    await create_transaction(
                        db=db,
                        account_id=account.id,
                        type=TransactionType.despesa.value,
                        category="outras_despesas",
                        description=f"Perda de vasilhame {tipo} — {quantidade} unidade(s)",
                        amount=custo_total,
                        direction="saida",
                        reference_date=date.today(),
                        is_paid=True,
                        created_by=1,
                        notes=observacao,
                    )
        except Exception as exc:
            logger.error(f"Erro ao registrar despesa de perda de vasilhame: {exc}", exc_info=True)

        return mov

    async def ajuste_inventario(
        self,
        db: AsyncSession,
        tipo: str,
        qtd_cheios_real: int,
        qtd_vazios_real: int,
        observacao: str,
        user_id: Optional[UUID],
    ) -> VasilhameMovimento:
        """Ajuste de inventário: força saldos para valores reais."""
        estoque = await self._get_estoque_lock(db, tipo)
        snap = self._snapshot(estoque)

        estoque.qtd_cheios = qtd_cheios_real
        estoque.qtd_vazios = qtd_vazios_real

        mov = VasilhameMovimento(
            tipo_vasilhame=tipo,
            tipo_movimento="ajuste_inventario",
            quantidade=qtd_cheios_real,
            observacao=observacao,
            created_by=user_id,
            **snap,
        )
        db.add(mov)
        await db.flush()
        return mov

    async def get_posicao_atual(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Retorna posição atual de todos os tipos de vasilhame."""
        result = await db.execute(
            select(VasilhameEstoque).order_by(VasilhameEstoque.tipo)
        )
        estoques = result.scalars().all()
        return [
            {
                "tipo": e.tipo,
                "qtd_cheios": e.qtd_cheios,
                "qtd_vazios": e.qtd_vazios,
                "qtd_em_campo": e.qtd_em_campo,
                "custo_unitario": e.custo_unitario,
                "valor_estoque": float(e.qtd_cheios * e.custo_unitario),
            }
            for e in estoques
        ]

    async def get_movimentacoes(
        self,
        db: AsyncSession,
        tipo: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Lista paginada de movimentações com filtros."""
        conditions = []
        if tipo:
            conditions.append(VasilhameMovimento.tipo_vasilhame == tipo)
        if start:
            conditions.append(VasilhameMovimento.created_at >= start)
        if end:
            from datetime import datetime, timezone, timedelta
            end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc)
            conditions.append(VasilhameMovimento.created_at <= end_dt)

        base_query = select(VasilhameMovimento)
        if conditions:
            base_query = base_query.where(and_(*conditions))

        count_result = await db.execute(base_query)
        total = len(count_result.scalars().all())

        offset = (page - 1) * limit
        result = await db.execute(
            base_query.order_by(desc(VasilhameMovimento.created_at)).offset(offset).limit(limit)
        )
        movs = result.scalars().all()
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "items": movs,
        }

    async def get_alertas(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Retorna alertas de estoque baixo (cheios < 5)."""
        result = await db.execute(
            select(VasilhameEstoque).where(VasilhameEstoque.qtd_cheios < 5)
        )
        estoques = result.scalars().all()
        alertas = []
        for e in estoques:
            alertas.append({
                "tipo": e.tipo,
                "qtd_cheios": e.qtd_cheios,
                "qtd_em_campo": e.qtd_em_campo,
                "mensagem": f"Estoque baixo de {e.tipo}: apenas {e.qtd_cheios} cheio(s) disponível(eis)",
            })
        return alertas
