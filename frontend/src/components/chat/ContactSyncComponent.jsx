import React, { useState, useEffect } from 'react';
import { syncContacts, getContacts } from '../../services/api';
import { RefreshCw, Users, CheckCircle, AlertTriangle } from 'lucide-react';

const ContactSyncComponent = () => {
    const [contacts, setContacts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [result, setResult] = useState(null);

    useEffect(() => {
        fetchContacts();
    }, []);

    const fetchContacts = async () => {
        setLoading(true);
        try {
            const data = await getContacts();
            setContacts(data);
        } catch (err) {
            console.error('Failed to fetch contacts:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSync = async () => {
        setSyncing(true);
        setResult(null);
        try {
            const data = await syncContacts();
            setResult({ success: true, message: data.message });
            await fetchContacts();
        } catch (err) {
            console.error('Failed to sync contacts:', err);
            setResult({ success: false, message: 'Falha ao sincronizar contatos.' });
        } finally {
            setSyncing(false);
        }
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow-md max-w-4xl mx-auto my-6">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-gray-800 flex items-center">
                        <Users className="mr-2" /> Contatos Sincronizados
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                        Exibindo apenas números válidos do WhatsApp (Filtro automático ativado).
                    </p>
                </div>
                <button
                    onClick={handleSync}
                    disabled={syncing}
                    className={`flex items-center px-4 py-2 text-white font-medium rounded-md transition-colors ${syncing ? 'bg-indigo-400 cursor-wait' : 'bg-indigo-600 hover:bg-indigo-700'
                        }`}
                >
                    <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                    {syncing ? 'Sincronizando...' : 'Sincronizar Contatos'}
                </button>
            </div>

            {result && (
                <div className={`p-4 mb-4 rounded-md ${result.success ? 'bg-green-50 text-green-800 border-l-4 border-green-500' : 'bg-red-50 text-red-800 border-l-4 border-red-500'}`}>
                    <div className="flex items-center">
                        {result.success ? <CheckCircle className="mr-2 h-5 w-5" /> : <AlertTriangle className="mr-2 h-5 w-5" />}
                        <span className="font-medium">{result.message}</span>
                    </div>
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center p-8">
                    <RefreshCw className="h-8 w-8 animate-spin text-indigo-500" />
                </div>
            ) : contacts.length > 0 ? (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nome</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Telefone</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Última Sincronização</th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {contacts.map((contact) => (
                                <tr key={contact.id}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{contact.name || '-'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{contact.phone_number}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {new Date(contact.last_synced_at).toLocaleString('pt-BR')}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                            Válido
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
                    <Users className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">Nenhum contato encontrado</h3>
                    <p className="mt-1 text-sm text-gray-500">
                        Tente sincronizar com o aparelho conectado para carregar os contatos válidos.
                    </p>
                </div>
            )}
        </div>
    );
};

export default ContactSyncComponent;
