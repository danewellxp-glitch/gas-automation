"""
Serviço de Despesas Operacionais.
Lógica de parcelamento, recorrência e alertas.
"""
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense, ExpenseTipo, ExpenseTipoGrupo, Periodicidade, EXPENSE_GRUPO
from app.schemas.expense import ExpenseCreate

logger = logging.getLogger(__name__)


async def create_expense(
    db: AsyncSession,
    body: ExpenseCreate,
    user_id: Optional[int] = None,
) -> List[Expense]:
    """
    Cria uma ou mais despesas dependendo da periodicidade.
    - unico/mensal/anual com parcelas_total=1: 1 registro
    - parcelado com parcelas_total>1: N registros com grupo_parcela_id compartilhado
    """
    grupo = EXPENSE_GRUPO.get(body.tipo, ExpenseTipoGrupo.administrativo)
    hoje = date.today()

    if body.periodicidade == Periodicidade.parcelado and body.parcelas_total > 1:
        return await _create_parcelado(db, body, grupo, hoje, user_id)

    # Despesa única, mensal ou anual
    valor_parcela = body.valor / body.parcelas_total
    expense = Expense(
        tipo=body.tipo.value,
        grupo=grupo.value,
        descricao=body.descricao,
        valor=body.valor,
        valor_parcela=valor_parcela,
        data_lancamento=hoje,
        data_vencimento=body.data_vencimento,
        periodicidade=body.periodicidade.value,
        parcelas_total=1,
        parcela_atual=1,
        veiculo_placa=body.veiculo_placa,
        funcionario_id=body.funcionario_id,
        fornecedor=body.fornecedor,
        numero_nota=body.numero_nota,
        observacao=body.observacao,
        conta_id=body.conta_id,
        created_by=user_id,
    )
    db.add(expense)
    await db.flush()
    return [expense]


async def _create_parcelado(
    db: AsyncSession,
    body: ExpenseCreate,
    grupo: ExpenseTipoGrupo,
    hoje: date,
    user_id: Optional[int],
) -> List[Expense]:
    """Cria N parcelas com grupo_parcela_id compartilhado."""
    grupo_id = uuid.uuid4()
    valor_parcela = body.valor / body.parcelas_total
    parcelas = []

    for i in range(body.parcelas_total):
        vencimento = body.data_vencimento + relativedelta(months=i)
        expense = Expense(
            tipo=body.tipo.value,
            grupo=grupo.value,
            descricao=body.descricao,
            valor=body.valor,
            valor_parcela=valor_parcela,
            data_lancamento=hoje,
            data_vencimento=vencimento,
            periodicidade=Periodicidade.parcelado.value,
            parcelas_total=body.parcelas_total,
            parcela_atual=i + 1,
            grupo_parcela_id=grupo_id,
            veiculo_placa=body.veiculo_placa,
            funcionario_id=body.funcionario_id,
            fornecedor=body.fornecedor,
            numero_nota=body.numero_nota,
            observacao=body.observacao,
            conta_id=body.conta_id,
            created_by=user_id,
        )
        parcelas.append(expense)

    db.add_all(parcelas)
    await db.flush()
    return parcelas


async def list_expenses(
    db: AsyncSession,
    tipo: Optional[str] = None,
    grupo: Optional[str] = None,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    veiculo: Optional[str] = None,
    funcionario_id: Optional[int] = None,
    pago: Optional[bool] = None,
    periodicidade: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Expense]:
    filters = [Expense.deleted_at == None]

    if tipo:
        filters.append(Expense.tipo == tipo)
    if grupo:
        filters.append(Expense.grupo == grupo)
    if mes:
        filters.append(func.extract("month", Expense.data_vencimento) == mes)
    if ano:
        filters.append(func.extract("year", Expense.data_vencimento) == ano)
    if veiculo:
        filters.append(Expense.veiculo_placa == veiculo)
    if funcionario_id is not None:
        filters.append(Expense.funcionario_id == funcionario_id)
    if pago is not None:
        filters.append(Expense.pago == pago)
    if periodicidade:
        filters.append(Expense.periodicidade == periodicidade)

    result = await db.execute(
        select(Expense)
        .where(and_(*filters))
        .order_by(Expense.data_vencimento)
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_proximos_vencimentos(db: AsyncSession, dias: int = 30) -> List[Expense]:
    """Despesas não pagas com vencimento nos próximos N dias."""
    hoje = date.today()
    limite = hoje + relativedelta(days=dias)
    result = await db.execute(
        select(Expense)
        .where(
            and_(
                Expense.deleted_at == None,
                Expense.pago == False,
                Expense.data_vencimento >= hoje,
                Expense.data_vencimento <= limite,
            )
        )
        .order_by(Expense.data_vencimento)
    )
    return result.scalars().all()


async def get_despesas_por_grupo(
    db: AsyncSession,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
) -> List[dict]:
    """Totais agrupados por grupo (para DRE)."""
    filters = [Expense.deleted_at == None]
    if mes:
        filters.append(func.extract("month", Expense.data_vencimento) == mes)
    if ano:
        filters.append(func.extract("year", Expense.data_vencimento) == ano)

    result = await db.execute(
        select(
            Expense.grupo,
            func.sum(Expense.valor_parcela).label("total"),
            func.sum(
                func.case((Expense.pago == True, Expense.valor_parcela), else_=0)
            ).label("pago"),
            func.sum(
                func.case((Expense.pago == False, Expense.valor_parcela), else_=0)
            ).label("pendente"),
        )
        .where(and_(*filters))
        .group_by(Expense.grupo)
        .order_by(Expense.grupo)
    )
    return [
        {
            "grupo": row.grupo,
            "total": row.total or Decimal("0"),
            "pago": row.pago or Decimal("0"),
            "pendente": row.pendente or Decimal("0"),
        }
        for row in result.all()
    ]


async def pagar_expense(
    db: AsyncSession,
    expense_id: uuid.UUID,
    data_pagamento: Optional[date] = None,
) -> Optional[Expense]:
    result = await db.execute(
        select(Expense).where(
            and_(Expense.id == expense_id, Expense.deleted_at == None)
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        return None

    expense.pago = True
    expense.data_pagamento = data_pagamento or date.today()
    await db.flush()
    return expense


async def pagar_grupo_parcela(
    db: AsyncSession,
    grupo_parcela_id: uuid.UUID,
    data_pagamento: Optional[date] = None,
) -> int:
    """Marca todas as parcelas do grupo como pagas. Retorna quantidade paga."""
    result = await db.execute(
        select(Expense).where(
            and_(
                Expense.grupo_parcela_id == grupo_parcela_id,
                Expense.deleted_at == None,
                Expense.pago == False,
            )
        )
    )
    parcelas = result.scalars().all()
    hoje = data_pagamento or date.today()
    for p in parcelas:
        p.pago = True
        p.data_pagamento = hoje
    await db.flush()
    return len(parcelas)


async def delete_expense(db: AsyncSession, expense_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Expense).where(
            and_(Expense.id == expense_id, Expense.deleted_at == None)
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        return False
    expense.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return True


async def get_alertas_vencimento(db: AsyncSession) -> dict:
    """
    Retorna alertas para o dashboard:
    - vencendo_7_dias: despesas não pagas vencendo em até 7 dias
    - vencidas: despesas não pagas com vencimento passado
    """
    hoje = date.today()
    em_7_dias = hoje + relativedelta(days=7)

    result_urgente = await db.execute(
        select(Expense).where(
            and_(
                Expense.deleted_at == None,
                Expense.pago == False,
                Expense.data_vencimento >= hoje,
                Expense.data_vencimento <= em_7_dias,
            )
        ).order_by(Expense.data_vencimento)
    )

    result_vencidas = await db.execute(
        select(Expense).where(
            and_(
                Expense.deleted_at == None,
                Expense.pago == False,
                Expense.data_vencimento < hoje,
            )
        ).order_by(Expense.data_vencimento)
    )

    return {
        "vencendo_7_dias": result_urgente.scalars().all(),
        "vencidas": result_vencidas.scalars().all(),
    }
