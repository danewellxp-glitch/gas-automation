import React, { useState } from 'react';
import ChatInterface from '../components/chat/ChatInterface';
import ContactSyncComponent from '../components/chat/ContactSyncComponent';
import { MessageSquare, Users } from 'lucide-react';

const VeloceChatDashboard = () => {
    const [activeTab, setActiveTab] = useState('chat'); // 'chat' or 'contacts'

    return (
        <div className="flex flex-col h-full bg-gray-50 p-6">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-800">Atendimento ao Cliente</h1>
                    <p className="text-gray-500">Gerencie conversas e sincronização de contatos do WhatsApp.</p>
                </div>

                <div className="flex bg-white rounded-lg shadow-sm border p-1">
                    <button
                        onClick={() => setActiveTab('chat')}
                        className={`flex items-center px-4 py-2 rounded-md transition-colors ${activeTab === 'chat'
                                ? 'bg-indigo-50 text-indigo-700 font-medium'
                                : 'text-gray-600 hover:bg-gray-50'
                            }`}
                    >
                        <MessageSquare className="w-4 h-4 mr-2" />
                        Conversas
                    </button>
                    <button
                        onClick={() => setActiveTab('contacts')}
                        className={`flex items-center px-4 py-2 rounded-md transition-colors ${activeTab === 'contacts'
                                ? 'bg-indigo-50 text-indigo-700 font-medium'
                                : 'text-gray-600 hover:bg-gray-50'
                            }`}
                    >
                        <Users className="w-4 h-4 mr-2" />
                        Sincronização
                    </button>
                </div>
            </div>

            <div className="flex-1 bg-white rounded-xl shadow-sm border overflow-hidden">
                {activeTab === 'chat' ? (
                    <ChatInterface />
                ) : (
                    <div className="p-6 overflow-y-auto h-full">
                        <ContactSyncComponent />
                    </div>
                )}
            </div>
        </div>
    );
};

export default VeloceChatDashboard;
