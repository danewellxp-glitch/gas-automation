import { useState, useEffect, useCallback } from 'react';
import api from '../../api/client';
import { FINANCEIRO } from '../../api/endpoints';
import BaseModal from '../../components/ui/BaseModal';

const fmt = (n) =>
  Number(n || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const BADGE = {
  conciliado: 'bg-green-100 text-green-800',
  divergencia_valor: 'bg-yellow-100 text-yellow-800',
  apenas_asaas: 'bg-red-100 text-red-800',
  apenas_local: 'bg-gray-100 text-gray-700',
};

const BADGE_LABEL = {
  conciliado: '✓ Conciliado',
  divergencia_valor: '! Divergência',
  apenas_asaas: 'Só Asaas',
  apenas_local: 'Só Local',
};

export default function PixConciliacao() {
  const today = new Date().toISOString().slice(0, 10);
  const [selectedDate, setSelectedDate] = useState(today);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState(null);

  // Modal de resolução
  const [resolveModal, setResolveModal] = useState(null); // { item }
  const [resolveObs, setResolveObs] = useState('');
  const [resolving, setResolving] = useState(false);

  const load = useCallback(async (date) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get(`${FINANCEIRO.CONCILIACAO_PIX}?date=${date}`);
      setData(resp.data);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao carregar conciliação');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(selectedDate);
  }, [selectedDate, load]);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      await api.post(FINANCEIRO.CONCILIACAO_PIX_RUN, { date: selectedDate });
      await load(selectedDate);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao executar conciliação');
    } finally {
      setRunning(false);
    }
  };

  const handleAprovar = async () => {
    if (!data?.run?.id) return;
    setApproving(true);
    setError(null);
    try {
      await api.post(FINANCEIRO.CONCILIACAO_PIX_APROVAR(data.run.id));
      await load(selectedDate);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao aprovar conciliação');
    } finally {
      setApproving(false);
    }
  };

  const handleResolver = async () => {
    if (!resolveModal) return;
    setResolving(true);
    try {
      await api.post(FINANCEIRO.CONCILIACAO_PIX_RESOLVER(resolveModal.item.id), {
        observacao: resolveObs,
      });
      setResolveModal(null);
      setResolveObs('');
      await load(selectedDate);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao resolver item');
    } finally {
      setResolving(false);
    }
  };

  const run = data?.run;
  const items = data?.items || [];

  const pendentesNaoResolvidos =
    items.filter(
      (i) => i.resultado !== 'conciliado' && !i.resolvido
    ).length;

  const canAprovar = run && run.status !== 'aprovado' && pendentesNaoResolvidos === 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Conciliação PIX</h1>
          <p className="text-sm text-gray-500 mt-1">Cruza pagamentos do Asaas com transações locais</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleRun}
            disabled={running || loading}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {running ? (
              <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
            Executar Conciliação
          </button>
          <button
            onClick={handleAprovar}
            disabled={!canAprovar || approving}
            title={pendentesNaoResolvidos > 0 ? 'Resolva todas as divergências antes de aprovar' : ''}
            className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-40"
          >
            {approving ? 'Aprovando...' : 'Aprovar Fechamento'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {run && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>Status:</span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              run.status === 'aprovado'
                ? 'bg-green-100 text-green-700'
                : 'bg-yellow-100 text-yellow-700'
            }`}
          >
            {run.status === 'aprovado' ? 'Aprovado' : 'Pendente revisão'}
          </span>
          <span className="text-gray-400">•</span>
          <span>Executado em {new Date(run.run_at).toLocaleString('pt-BR')}</span>
        </div>
      )}

      {/* Cards de sumário */}
      {run && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Total Asaas</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{run.total_asaas}</p>
            <p className="text-sm text-gray-500">{fmt(run.valor_asaas)}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Total Local</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{run.total_local}</p>
            <p className="text-sm text-gray-500">{fmt(run.valor_local)}</p>
          </div>
          <div className="rounded-xl border border-green-200 bg-green-50 p-4">
            <p className="text-xs text-green-700 uppercase tracking-wide">Conciliados</p>
            <p className="mt-1 text-2xl font-bold text-green-700">{run.total_conciliado}</p>
          </div>
          <div className="rounded-xl border border-red-200 bg-red-50 p-4">
            <p className="text-xs text-red-700 uppercase tracking-wide">Divergências</p>
            <p className="mt-1 text-2xl font-bold text-red-700">{run.total_divergencia}</p>
          </div>
          <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4">
            <p className="text-xs text-yellow-700 uppercase tracking-wide">Pendências</p>
            <p className="mt-1 text-2xl font-bold text-yellow-700">
              {run.total_apenas_asaas + run.total_apenas_local}
            </p>
            <p className="text-xs text-yellow-600">
              {run.total_apenas_asaas} só Asaas · {run.total_apenas_local} só local
            </p>
          </div>
        </div>
      )}

      {/* Tabela de itens */}
      {loading ? (
        <div className="flex justify-center py-12">
          <span className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
        </div>
      ) : items.length > 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">Resultado</th>
                  <th className="px-4 py-3 text-left">ID Asaas</th>
                  <th className="px-4 py-3 text-left">Pagador</th>
                  <th className="px-4 py-3 text-right">Valor Asaas</th>
                  <th className="px-4 py-3 text-right">Valor Local</th>
                  <th className="px-4 py-3 text-right">Diferença</th>
                  <th className="px-4 py-3 text-left">Observação</th>
                  <th className="px-4 py-3 text-center">Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {items.map((item) => (
                  <tr key={item.id} className={item.resolvido ? 'opacity-60' : ''}>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${BADGE[item.resultado] || 'bg-gray-100 text-gray-700'}`}
                      >
                        {BADGE_LABEL[item.resultado] || item.resultado}
                      </span>
                      {item.resolvido && (
                        <span className="ml-1 text-xs text-gray-400">(resolvido)</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">
                      {item.asaas_payment_id || '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-700">{item.asaas_payer_name || '—'}</td>
                    <td className="px-4 py-3 text-right">{item.asaas_amount != null ? fmt(item.asaas_amount) : '—'}</td>
                    <td className="px-4 py-3 text-right">{item.transaction_amount != null ? fmt(item.transaction_amount) : '—'}</td>
                    <td className={`px-4 py-3 text-right font-medium ${Number(item.diferenca) !== 0 ? 'text-red-600' : 'text-gray-500'}`}>
                      {Number(item.diferenca) !== 0 ? fmt(item.diferenca) : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 max-w-xs truncate">{item.observacao || '—'}</td>
                    <td className="px-4 py-3 text-center">
                      {item.resultado !== 'conciliado' && !item.resolvido && (
                        <button
                          onClick={() => { setResolveModal({ item }); setResolveObs(''); }}
                          className="rounded-lg bg-yellow-100 px-2 py-1 text-xs font-medium text-yellow-800 hover:bg-yellow-200"
                        >
                          Resolver
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        !loading && run && (
          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
            Nenhum item encontrado para esta data.
          </div>
        )
      )}

      {/* Modal de resolução */}
      {resolveModal && (
        <BaseModal onClose={() => setResolveModal(null)} maxWidth="max-w-md">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">Marcar como Resolvido</h3>
            <p className="text-sm text-gray-500 mb-4">
              Item: <span className="font-medium">{BADGE_LABEL[resolveModal.item.resultado]}</span>
              {resolveModal.item.asaas_payment_id && ` · ${resolveModal.item.asaas_payment_id}`}
            </p>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Observação <span className="text-red-500">*</span>
            </label>
            <textarea
              rows={3}
              value={resolveObs}
              onChange={(e) => setResolveObs(e.target.value)}
              placeholder="Descreva como foi resolvida a divergência..."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => setResolveModal(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleResolver}
                disabled={!resolveObs.trim() || resolving}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {resolving ? 'Salvando...' : 'Marcar Resolvido'}
              </button>
            </div>
          </div>
        </BaseModal>
      )}
    </div>
  );
}
