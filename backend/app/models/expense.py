"""
Módulo de Despesas Operacionais.
Controla todas as saídas de caixa da distribuidora por categoria.
"""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ExpenseTipoGrupo(str, enum.Enum):
    pessoal = "pessoal"
    frota = "frota"
    produto_estoque = "produto_estoque"
    estrutura = "estrutura"
    regulatorio = "regulatorio"
    administrativo = "administrativo"
    comercial = "comercial"


class ExpenseTipo(str, enum.Enum):
    # Pessoal
    salario = "salario"
    decimo_terceiro = "decimo_terceiro"
    ferias = "ferias"
    fgts = "fgts"
    inss_patronal = "inss_patronal"
    vale_transporte = "vale_transporte"
    vale_refeicao = "vale_refeicao"
    uniforme_epi = "uniforme_epi"
    exame_medico = "exame_medico"
    rescisao = "rescisao"
    # Frota
    combustivel = "combustivel"
    manutencao_preventiva = "manutencao_preventiva"
    manutencao_corretiva = "manutencao_corretiva"
    ipva = "ipva"
    seguro_frota = "seguro_frota"
    seguro_antt = "seguro_antt"
    dpvat = "dpvat"
    licenciamento = "licenciamento"
    pedagio = "pedagio"
    lavagem_frota = "lavagem_frota"
    # Produto/Estoque
    compra_glp = "compra_glp"
    compra_vasilhame = "compra_vasilhame"
    requalificacao_botijao = "requalificacao_botijao"
    insumos = "insumos"
    # Estrutura
    aluguel = "aluguel"
    condominio = "condominio"
    manutencao_estrutura = "manutencao_estrutura"
    energia = "energia"
    agua = "agua"
    internet = "internet"
    telefone = "telefone"
    # Regulatório
    licenca_anp = "licenca_anp"
    alvara_funcionamento = "alvara_funcionamento"
    vistoria_bombeiros = "vistoria_bombeiros"
    calibracao_balanca = "calibracao_balanca"
    certificado_digital = "certificado_digital"
    # Administrativo
    contador = "contador"
    tarifa_bancaria = "tarifa_bancaria"
    juros_capital_giro = "juros_capital_giro"
    sistema_legado = "sistema_legado"
    terceirizado = "terceirizado"
    # Comercial
    marketing = "marketing"
    outro = "outro"


class Periodicidade(str, enum.Enum):
    unico = "unico"
    mensal = "mensal"
    anual = "anual"
    parcelado = "parcelado"


# Mapeamento tipo → grupo
EXPENSE_GRUPO: dict = {
    # Pessoal
    ExpenseTipo.salario: ExpenseTipoGrupo.pessoal,
    ExpenseTipo.decimo_terceiro: ExpenseTipoGrupo.pessoal,
    ExpenseTipo.ferias: ExpenseTipoGrupo.pessoal,
    ExpenseTipo.fgts: ExpenseTipoGrupo.pessoal,
    ExpenseTipo.inss_patronal: ExpenseTipoGrupo.pessoal,
    ExpenseTipo.vale_transporte: ExpenseTipoGrupo.pessoal,
    ExpenseTipo.vale_refeicao: ExpenseTipoGrupo.pessoal,
    ExpenseTipo.uniforme_epi: ExpenseTipoGrupo.pessoal,
    ExpenseTipo.exame_medico: ExpenseTipoGrupo.pessoal,
    ExpenseTipo.rescisao: ExpenseTipoGrupo.pessoal,
    # Frota
    ExpenseTipo.combustivel: ExpenseTipoGrupo.frota,
    ExpenseTipo.manutencao_preventiva: ExpenseTipoGrupo.frota,
    ExpenseTipo.manutencao_corretiva: ExpenseTipoGrupo.frota,
    ExpenseTipo.ipva: ExpenseTipoGrupo.frota,
    ExpenseTipo.seguro_frota: ExpenseTipoGrupo.frota,
    ExpenseTipo.seguro_antt: ExpenseTipoGrupo.frota,
    ExpenseTipo.dpvat: ExpenseTipoGrupo.frota,
    ExpenseTipo.licenciamento: ExpenseTipoGrupo.frota,
    ExpenseTipo.pedagio: ExpenseTipoGrupo.frota,
    ExpenseTipo.lavagem_frota: ExpenseTipoGrupo.frota,
    # Produto/Estoque
    ExpenseTipo.compra_glp: ExpenseTipoGrupo.produto_estoque,
    ExpenseTipo.compra_vasilhame: ExpenseTipoGrupo.produto_estoque,
    ExpenseTipo.requalificacao_botijao: ExpenseTipoGrupo.produto_estoque,
    ExpenseTipo.insumos: ExpenseTipoGrupo.produto_estoque,
    # Estrutura
    ExpenseTipo.aluguel: ExpenseTipoGrupo.estrutura,
    ExpenseTipo.condominio: ExpenseTipoGrupo.estrutura,
    ExpenseTipo.manutencao_estrutura: ExpenseTipoGrupo.estrutura,
    ExpenseTipo.energia: ExpenseTipoGrupo.estrutura,
    ExpenseTipo.agua: ExpenseTipoGrupo.estrutura,
    ExpenseTipo.internet: ExpenseTipoGrupo.estrutura,
    ExpenseTipo.telefone: ExpenseTipoGrupo.estrutura,
    # Regulatório
    ExpenseTipo.licenca_anp: ExpenseTipoGrupo.regulatorio,
    ExpenseTipo.alvara_funcionamento: ExpenseTipoGrupo.regulatorio,
    ExpenseTipo.vistoria_bombeiros: ExpenseTipoGrupo.regulatorio,
    ExpenseTipo.calibracao_balanca: ExpenseTipoGrupo.regulatorio,
    ExpenseTipo.certificado_digital: ExpenseTipoGrupo.regulatorio,
    # Administrativo
    ExpenseTipo.contador: ExpenseTipoGrupo.administrativo,
    ExpenseTipo.tarifa_bancaria: ExpenseTipoGrupo.administrativo,
    ExpenseTipo.juros_capital_giro: ExpenseTipoGrupo.administrativo,
    ExpenseTipo.sistema_legado: ExpenseTipoGrupo.administrativo,
    ExpenseTipo.terceirizado: ExpenseTipoGrupo.administrativo,
    # Comercial
    ExpenseTipo.marketing: ExpenseTipoGrupo.comercial,
    ExpenseTipo.outro: ExpenseTipoGrupo.administrativo,
}


class Expense(BaseModel):
    __tablename__ = "expenses"

    tipo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    grupo: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)

    # Valores
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, comment="Valor total do lançamento")
    valor_parcela: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, comment="Valor de cada parcela")

    # Datas
    data_lancamento: Mapped[date] = mapped_column(Date, nullable=False)
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Parcelamento / Recorrência
    periodicidade: Mapped[str] = mapped_column(String(20), nullable=False, default=Periodicidade.unico.value)
    parcelas_total: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parcela_atual: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    grupo_parcela_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="Agrupa parcelas do mesmo lançamento"
    )

    # Status de pagamento
    pago: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    data_pagamento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Vínculos opcionais
    veiculo_placa: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    funcionario_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    fornecedor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    numero_nota: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Controle
    conta_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_expenses_tipo_vencimento", "tipo", "data_vencimento"),
        Index("ix_expenses_pago_vencimento", "pago", "data_vencimento"),
        Index("ix_expenses_grupo_vencimento", "grupo", "data_vencimento"),
    )
