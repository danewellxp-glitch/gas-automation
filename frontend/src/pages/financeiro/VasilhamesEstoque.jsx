import { useState, useEffect, useCallback } from 'react';
import api from '../../api/client';
import { FINANCEIRO } from '../../api/endpoints';

const fmt = (n) =>
  Number(n || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const TIPOS = ['P13', 'P20', 'P45', 'G20L'];

const MOVIMENTO_LABEL = {
  entrada_compra: 'Entrada Compra',
  saida_venda: 'Saída Venda',
  retorno_vazio: 'Retorno Vazio',
  perda: 'Perda',
  ajuste_inventario: 'Ajuste Inventário',
  reabastecimento: 'Reabastecimento',
};

const MOVIMENTO_BADGE = {
  entrada_compra: 'bg-green-100 text-green-700',
  saida_venda: 'bg-blue-100 text-blue-700',
  retorno_vazio: 'bg-indigo-100 text-indigo-700',
  perda: 'bg-red-100 text-red-700',
  ajuste_inventario: 'bg-yellow-100 text-yellow-700',
  reabastecimento: 'bg-emerald-100 text-emerald-700',
};

// Modal genérico
function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function SelectTipo({ value, onChange, required }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      required={required}
      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="">Selecione o tipo</option>
      {TIPOS.map((t) => <option key={t} value={t}>{t}</option>)}
    </select>
  );
}

function CardEstoque({ estoque }) {
  const valor = estoque.qtd_cheios * Number(estoque.custo_unitario);
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-base font-bold text-gray-900">{estoque.tipo}</span>
        <span className="text-sm font-medium text-gray-500">{fmt(valor)}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-green-50 p-2">
          <p className="text-xs text-green-600 font-medium">Cheios</p>
          <p className="text-xl font-bold text-green-700">{estoque.qtd_cheios}</p>
        </div>
        <div className="rounded-lg bg-yellow-50 p-2">
          <p className="text-xs text-yellow-600 font-medium">Em Campo</p>
          <p className="text-xl font-bold text-yellow-700">{estoque.qtd_em_campo}</p>
        </div>
        <div className="rounded-lg bg-blue-50 p-2">
          <p className="text-xs text-blue-600 font-medium">Vazios</p>
          <p className="text-xl font-bold text-blue-700">{estoque.qtd_vazios}</p>
        </div>
      </div>
      <p className="text-xs text-gray-400 text-right">
        Custo unit.: {fmt(estoque.custo_unitario)}
      </p>
    </div>
  );
}

export default function VasilhamesEstoque() {
  const [posicao, setPosicao] = useState([]);
  const [movs, setMovs] = useState({ total: 0, items: [] });
  const [alertas, setAlertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filtros movimentações
  const [filtroTipo, setFiltroTipo] = useState('');
  const [filtroStart, setFiltroStart] = useState('');
  const [filtroEnd, setFiltroEnd] = useState('');
  const [page, setPage] = useState(1);

  // Modais
  const [modal, setModal] = useState(null); // 'entrada' | 'retorno' | 'perda' | 'ajuste'
  const [submitting, setSubmitting] = useState(false);

  // Formulários
  const [formEntrada, setFormEntrada] = useState({ tipo: '', quantidade: '', custo_unitario: '' });
  const [formRetorno, setFormRetorno] = useState({ tipo: '', quantidade: '', pedido_id: '' });
  const [formPerda, setFormPerda] = useState({ tipo: '', quantidade: '', observacao: '' });
  const [formAjuste, setFormAjuste] = useState({ tipo: '', qtd_cheios_real: '', qtd_vazios_real: '', observacao: '' });
  const [confirmPerda, setConfirmPerda] = useState(false);

  const loadPosicao = useCallback(async () => {
    try {
      const resp = await api.get(FINANCEIRO.VASILHAMES_POSICAO);
      setPosicao(resp.data);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao carregar posição');
    }
  }, []);

  const loadAlertas = useCallback(async () => {
    try {
      const resp = await api.get(FINANCEIRO.VASILHAMES_ALERTAS);
      setAlertas(resp.data);
    } catch { /* silent */ }
  }, []);

  const loadMovs = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page, limit: 50 });
      if (filtroTipo) params.set('tipo', filtroTipo);
      if (filtroStart) params.set('start', filtroStart);
      if (filtroEnd) params.set('end', filtroEnd);
      const resp = await api.get(`${FINANCEIRO.VASILHAMES_MOVIMENTACOES}?${params}`);
      setMovs(resp.data);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao carregar movimentações');
    }
  }, [filtroTipo, filtroStart, filtroEnd, page]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([loadPosicao(), loadAlertas(), loadMovs()]);
    setLoading(false);
  }, [loadPosicao, loadAlertas, loadMovs]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleEntrada = async () => {
    setSubmitting(true);
    try {
      await api.post(FINANCEIRO.VASILHAMES_ENTRADA, {
        tipo: formEntrada.tipo,
        quantidade: Number(formEntrada.quantidade),
        custo_unitario: Number(formEntrada.custo_unitario),
      });
      setModal(null);
      setFormEntrada({ tipo: '', quantidade: '', custo_unitario: '' });
      await loadAll();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao registrar entrada');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetorno = async () => {
    setSubmitting(true);
    try {
      await api.post(FINANCEIRO.VASILHAMES_RETORNO, {
        tipo: formRetorno.tipo,
        quantidade: Number(formRetorno.quantidade),
        pedido_id: formRetorno.pedido_id || null,
      });
      setModal(null);
      setFormRetorno({ tipo: '', quantidade: '', pedido_id: '' });
      await loadAll();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao registrar retorno');
    } finally {
      setSubmitting(false);
    }
  };

  const handlePerda = async () => {
    if (!confirmPerda) { setConfirmPerda(true); return; }
    setSubmitting(true);
    try {
      await api.post(FINANCEIRO.VASILHAMES_PERDA, {
        tipo: formPerda.tipo,
        quantidade: Number(formPerda.quantidade),
        observacao: formPerda.observacao,
      });
      setModal(null);
      setFormPerda({ tipo: '', quantidade: '', observacao: '' });
      setConfirmPerda(false);
      await loadAll();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao registrar perda');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAjuste = async () => {
    setSubmitting(true);
    try {
      await api.post(FINANCEIRO.VASILHAMES_AJUSTE, {
        tipo: formAjuste.tipo,
        qtd_cheios_real: Number(formAjuste.qtd_cheios_real),
        qtd_vazios_real: Number(formAjuste.qtd_vazios_real),
        observacao: formAjuste.observacao,
      });
      setModal(null);
      setFormAjuste({ tipo: '', qtd_cheios_real: '', qtd_vazios_real: '', observacao: '' });
      await loadAll();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao ajustar inventário');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Estoque de Vasilhames</h1>
          <p className="text-sm text-gray-500 mt-1">Controle operacional de botijões e galões</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setModal('entrada')}
            className="rounded-lg bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700"
          >
            + Entrada
          </button>
          <button
            onClick={() => setModal('retorno')}
            className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Retorno Vazio
          </button>
          <button
            onClick={() => { setModal('perda'); setConfirmPerda(false); }}
            className="rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            Registrar Perda
          </button>
          <button
            onClick={() => setModal('ajuste')}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Ajuste Inventário
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline text-xs">fechar</button>
        </div>
      )}

      {/* Alertas */}
      {alertas.length > 0 && (
        <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4 space-y-1">
          <p className="text-sm font-semibold text-yellow-800">Alertas de Estoque Baixo</p>
          {alertas.map((a) => (
            <p key={a.tipo} className="text-sm text-yellow-700">{a.mensagem}</p>
          ))}
        </div>
      )}

      {/* Cards por tipo */}
      {loading ? (
        <div className="flex justify-center py-12">
          <span className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {TIPOS.map((tipo) => {
            const e = posicao.find((p) => p.tipo === tipo) || {
              tipo,
              qtd_cheios: 0,
              qtd_vazios: 0,
              qtd_em_campo: 0,
              custo_unitario: 0,
              valor_estoque: 0,
            };
            return <CardEstoque key={tipo} estoque={e} />;
          })}
        </div>
      )}

      {/* Filtros e tabela de movimentações */}
      <div className="rounded-xl border border-gray-200 bg-white">
        <div className="flex flex-wrap items-center gap-3 p-4 border-b border-gray-100">
          <span className="text-sm font-semibold text-gray-700">Movimentações</span>
          <SelectTipo value={filtroTipo} onChange={(v) => { setFiltroTipo(v); setPage(1); }} />
          <input
            type="date"
            value={filtroStart}
            onChange={(e) => { setFiltroStart(e.target.value); setPage(1); }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none"
            placeholder="De"
          />
          <input
            type="date"
            value={filtroEnd}
            onChange={(e) => { setFiltroEnd(e.target.value); setPage(1); }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none"
            placeholder="Até"
          />
          <button
            onClick={() => { setFiltroTipo(''); setFiltroStart(''); setFiltroEnd(''); setPage(1); }}
            className="text-xs text-gray-500 underline"
          >
            Limpar
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left">Data</th>
                <th className="px-4 py-3 text-left">Tipo</th>
                <th className="px-4 py-3 text-left">Movimento</th>
                <th className="px-4 py-3 text-right">Qtd</th>
                <th className="px-4 py-3 text-right">Custo Unit.</th>
                <th className="px-4 py-3 text-right">Custo Total</th>
                <th className="px-4 py-3 text-left">Observação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {movs.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    Nenhuma movimentação encontrada.
                  </td>
                </tr>
              ) : (
                movs.items.map((m) => (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                      {m.created_at ? new Date(m.created_at).toLocaleDateString('pt-BR') : '—'}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900">{m.tipo_vasilhame}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${MOVIMENTO_BADGE[m.tipo_movimento] || 'bg-gray-100 text-gray-600'}`}
                      >
                        {MOVIMENTO_LABEL[m.tipo_movimento] || m.tipo_movimento}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">{m.quantidade}</td>
                    <td className="px-4 py-3 text-right">{m.custo_unitario != null ? fmt(m.custo_unitario) : '—'}</td>
                    <td className="px-4 py-3 text-right">{m.custo_total != null ? fmt(m.custo_total) : '—'}</td>
                    <td className="px-4 py-3 text-gray-500 max-w-xs truncate">{m.observacao || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Paginação */}
        {movs.total > 50 && (
          <div className="flex items-center justify-between p-4 border-t border-gray-100">
            <span className="text-sm text-gray-500">
              {movs.total} registros · página {page}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-40"
              >
                Anterior
              </button>
              <button
                disabled={page * 50 >= movs.total}
                onClick={() => setPage((p) => p + 1)}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-40"
              >
                Próxima
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ====== Modais ====== */}

      {/* Modal Entrada */}
      {modal === 'entrada' && (
        <Modal title="Registrar Entrada por Compra" onClose={() => setModal(null)}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <SelectTipo value={formEntrada.tipo} onChange={(v) => setFormEntrada({ ...formEntrada, tipo: v })} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quantidade</label>
              <input
                type="number"
                min="1"
                value={formEntrada.quantidade}
                onChange={(e) => setFormEntrada({ ...formEntrada, quantidade: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Custo Unitário (R$)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={formEntrada.custo_unitario}
                onChange={(e) => setFormEntrada({ ...formEntrada, custo_unitario: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0,00"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-3">
            <button onClick={() => setModal(null)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Cancelar
            </button>
            <button
              onClick={handleEntrada}
              disabled={!formEntrada.tipo || !formEntrada.quantidade || submitting}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {submitting ? 'Salvando...' : 'Registrar Entrada'}
            </button>
          </div>
        </Modal>
      )}

      {/* Modal Retorno */}
      {modal === 'retorno' && (
        <Modal title="Registrar Retorno de Vazio" onClose={() => setModal(null)}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <SelectTipo value={formRetorno.tipo} onChange={(v) => setFormRetorno({ ...formRetorno, tipo: v })} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quantidade</label>
              <input
                type="number"
                min="1"
                value={formRetorno.quantidade}
                onChange={(e) => setFormRetorno({ ...formRetorno, quantidade: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">ID do Pedido (opcional)</label>
              <input
                type="text"
                value={formRetorno.pedido_id}
                onChange={(e) => setFormRetorno({ ...formRetorno, pedido_id: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="UUID do pedido"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-3">
            <button onClick={() => setModal(null)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Cancelar
            </button>
            <button
              onClick={handleRetorno}
              disabled={!formRetorno.tipo || !formRetorno.quantidade || submitting}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting ? 'Salvando...' : 'Registrar Retorno'}
            </button>
          </div>
        </Modal>
      )}

      {/* Modal Perda */}
      {modal === 'perda' && (
        <Modal title="Registrar Perda de Vasilhame" onClose={() => { setModal(null); setConfirmPerda(false); }}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <SelectTipo value={formPerda.tipo} onChange={(v) => setFormPerda({ ...formPerda, tipo: v })} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quantidade</label>
              <input
                type="number"
                min="1"
                value={formPerda.quantidade}
                onChange={(e) => setFormPerda({ ...formPerda, quantidade: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Observação <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={3}
                value={formPerda.observacao}
                onChange={(e) => setFormPerda({ ...formPerda, observacao: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                placeholder="Descreva o motivo da perda..."
              />
            </div>
            {confirmPerda && (
              <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                Confirma o registro de perda de <strong>{formPerda.quantidade}</strong> vasilhame(s) do tipo <strong>{formPerda.tipo}</strong>? Esta operação gerará uma despesa financeira.
              </div>
            )}
          </div>
          <div className="mt-4 flex justify-end gap-3">
            <button
              onClick={() => { setModal(null); setConfirmPerda(false); }}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              onClick={handlePerda}
              disabled={!formPerda.tipo || !formPerda.quantidade || !formPerda.observacao.trim() || submitting}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {submitting ? 'Salvando...' : confirmPerda ? 'Confirmar Perda' : 'Registrar Perda'}
            </button>
          </div>
        </Modal>
      )}

      {/* Modal Ajuste */}
      {modal === 'ajuste' && (
        <Modal title="Ajuste de Inventário" onClose={() => setModal(null)}>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <SelectTipo value={formAjuste.tipo} onChange={(v) => setFormAjuste({ ...formAjuste, tipo: v })} required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Qtd Cheios (real)</label>
                <input
                  type="number"
                  min="0"
                  value={formAjuste.qtd_cheios_real}
                  onChange={(e) => setFormAjuste({ ...formAjuste, qtd_cheios_real: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Qtd Vazios (real)</label>
                <input
                  type="number"
                  min="0"
                  value={formAjuste.qtd_vazios_real}
                  onChange={(e) => setFormAjuste({ ...formAjuste, qtd_vazios_real: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Observação <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={2}
                value={formAjuste.observacao}
                onChange={(e) => setFormAjuste({ ...formAjuste, observacao: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                placeholder="Motivo do ajuste..."
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-3">
            <button onClick={() => setModal(null)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              Cancelar
            </button>
            <button
              onClick={handleAjuste}
              disabled={
                !formAjuste.tipo ||
                formAjuste.qtd_cheios_real === '' ||
                formAjuste.qtd_vazios_real === '' ||
                !formAjuste.observacao.trim() ||
                submitting
              }
              className="rounded-lg bg-yellow-600 px-4 py-2 text-sm font-medium text-white hover:bg-yellow-700 disabled:opacity-50"
            >
              {submitting ? 'Salvando...' : 'Aplicar Ajuste'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
