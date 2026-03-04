import React, { useState, useEffect, useRef } from 'react';
import { getConversations, getConversationMessages, replyVeloceConversation, endVeloceConversation } from '../../services/api';
import { Send, Check, CheckCheck, Clock, CheckCircle, Info } from 'lucide-react';
import logger from '../../utils/logger';

// Import shared WebSocket manager singleton
import sharedWebSocketService from '../../services/sharedWebSocket';

const ChatInterface = () => {
    const [conversations, setConversations] = useState([]);
    const [activeChat, setActiveChat] = useState(null);
    const [messages, setMessages] = useState([]);
    const [newMessage, setNewMessage] = useState('');
    const [loading, setLoading] = useState(true);

    const messagesEndRef = useRef(null);

    useEffect(() => {
        fetchConversations();

        // Subscribe to WebSockets
        const handleWsMessage = (data) => {
            logger.info('WebSocket received msg:', data);
            if (data.type === 'message-received' || data.type === 'new_message') {
                const payload = data.data || data.message;

                // If the new message belongs to the active chat, update messages list
                setActiveChat((currentChat) => {
                    if (currentChat && payload.conversation_id === currentChat.id) {
                        setMessages((prev) => [...prev, payload]);
                    }
                    return currentChat;
                });

                // Update unread count in the sidebar
                setConversations((prevList) =>
                    prevList.map(c =>
                        c.id === payload.conversation_id
                            ? { ...c, unread_count: (c.unread_count || 0) + 1, last_message_at: new Date().toISOString() }
                            : c
                    ).sort((a, b) => new Date(b.last_message_at) - new Date(a.last_message_at))
                );
            }
        };

        const unsubscribeMsg = sharedWebSocketService.on('message-received', handleWsMessage);
        const unsubscribeNew = sharedWebSocketService.on('new_message', handleWsMessage);
        return () => {
            if (unsubscribeMsg) unsubscribeMsg();
            if (unsubscribeNew) unsubscribeNew();
        };
    }, []);

    const fetchConversations = async () => {
        try {
            setLoading(true);
            const data = await getConversations(1, 100);
            setConversations(data.items || data);
        } catch (err) {
            logger.error('Error fetching conversations:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadChat = async (conversation) => {
        setActiveChat(conversation);
        try {
            const msgs = await getConversationMessages(conversation.id);
            setMessages(msgs.messages || msgs);

            // Clear unread count locally
            setConversations(prev => prev.map(c => c.id === conversation.id ? { ...c, unread_count: 0 } : c));
            setTimeout(scrollToBottom, 100);
        } catch (err) {
            logger.error('Error loading messages:', err);
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!newMessage.trim() || !activeChat) return;

        const content = newMessage;
        setNewMessage('');

        // Optimistic update
        const tempMsg = {
            id: Date.now(),
            content: content,
            direction: 'OUTBOUND',
            status: 'PENDING',
            timestamp: new Date().toISOString()
        };
        setMessages([...messages, tempMsg]);
        scrollToBottom();

        try {
            const response = await replyVeloceConversation(activeChat.id, content);
            // Replace temp message with server response
            setMessages(prev => prev.map(m => m.id === tempMsg.id ? response : m));
        } catch (err) {
            logger.error('Error sending message:', err);
            // Mark as failed
            setMessages(prev => prev.map(m => m.id === tempMsg.id ? { ...m, status: 'FAILED' } : m));
        }
    };

    const handleEndChat = async () => {
        if (!activeChat) return;
        try {
            await endVeloceConversation(activeChat.id);
            setActiveChat(null);
            fetchConversations();
        } catch (err) {
            logger.error('Error ending conversation:', err);
        }
    };

    const renderMessageStatus = (status) => {
        switch (status) {
            case 'PENDING': return <Clock className="w-3 h-3 text-gray-400" />;
            case 'SENT': return <Check className="w-3 h-3 text-gray-400" />;
            case 'DELIVERED': return <CheckCheck className="w-3 h-3 text-gray-400" />;
            case 'READ': return <CheckCheck className="w-3 h-3 text-blue-500" />;
            case 'FAILED': return <span className="text-red-500 text-xs">Erro</span>;
            default: return null;
        }
    };

    return (
        <div className="flex h-[calc(100vh-100px)] bg-gray-100 border rounded-lg shadow-sm overflow-hidden">
            {/* Sidebar: Conv List */}
            <div className="w-1/3 bg-white border-r flex flex-col">
                <div className="p-4 bg-gray-50 border-b">
                    <h2 className="text-lg font-semibold text-gray-800">Conversas</h2>
                </div>
                <div className="overflow-y-auto flex-1">
                    {loading ? (
                        <div className="p-4 text-center text-gray-500">Carregando...</div>
                    ) : conversations.filter(c => c.status !== 'RESOLVED').length === 0 ? (
                        <div className="p-4 text-center text-gray-500">Nenhuma conversa ativa.</div>
                    ) : (
                        conversations.filter(c => c.status !== 'RESOLVED').map((chat) => (
                            <div
                                key={chat.id}
                                onClick={() => loadChat(chat)}
                                className={`p-4 border-b cursor-pointer hover:bg-gray-50 transition-colors ${activeChat?.id === chat.id ? 'bg-indigo-50 border-l-4 border-indigo-600' : ''}`}
                            >
                                <div className="flex justify-between items-center mb-1">
                                    <span className="font-semibold text-gray-800">{chat.name || chat.customer_phone}</span>
                                    <span className="text-xs text-gray-500">
                                        {new Date(chat.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-gray-600 truncate">{chat.customer_phone}</span>
                                    {chat.unread_count > 0 && (
                                        <span className="bg-green-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-medium">
                                            {chat.unread_count}
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col">
                {activeChat ? (
                    <>
                        {/* Header */}
                        <div className="p-4 bg-white border-b flex justify-between items-center shadow-sm">
                            <div>
                                <h3 className="text-lg font-semibold text-gray-800">{activeChat.name || activeChat.customer_phone}</h3>
                                <p className="text-sm text-gray-500">{activeChat.customer_phone}</p>
                            </div>
                            <button
                                onClick={handleEndChat}
                                className="flex items-center px-3 py-1.5 bg-red-50 text-red-600 hover:bg-red-100 rounded-md transition-colors text-sm font-medium"
                            >
                                <CheckCircle className="w-4 h-4 mr-1.5" />
                                Finalizar Atendimento
                            </button>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 p-4 overflow-y-auto bg-[#e5ddd5]" style={{ backgroundImage: "url('https://i.pinimg.com/originals/8f/ba/cb/8fbacbd464e996966eb9d4a6b7a9c21e.jpg')", backgroundSize: 'cover' }}>
                            {messages.map((msg, index) => {
                                const isOutbound = msg.direction === 'OUTBOUND';
                                return (
                                    <div key={msg.id || index} className={`flex mb-4 ${isOutbound ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[75%] rounded-lg p-3 shadow-sm relative ${isOutbound ? 'bg-[#dcf8c6] rounded-tr-none' : 'bg-white rounded-tl-none'}`}>
                                            <p className="text-gray-800 text-sm whitespace-pre-wrap">{msg.content}</p>
                                            <div className="flex items-center justify-end mt-1 space-x-1">
                                                <span className="text-[10px] text-gray-500">
                                                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </span>
                                                {isOutbound && renderMessageStatus(msg.status)}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input Area */}
                        <div className="p-3 bg-gray-100 border-t">
                            <form onSubmit={handleSendMessage} className="flex gap-2">
                                <input
                                    type="text"
                                    value={newMessage}
                                    onChange={(e) => setNewMessage(e.target.value)}
                                    placeholder="Digite uma mensagem..."
                                    className="flex-1 p-3 rounded-full border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
                                />
                                <button
                                    type="submit"
                                    disabled={!newMessage.trim()}
                                    className="bg-indigo-600 text-white p-3 rounded-full hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-colors"
                                >
                                    <Send className="w-5 h-5" />
                                </button>
                            </form>
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center bg-gray-50 text-gray-400">
                        <Info className="w-16 h-16 mb-4 text-gray-300" />
                        <h2 className="text-xl font-medium text-gray-600">WPPConnector Chat</h2>
                        <p className="mt-2">Selecione uma conversa para começar o atendimento.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ChatInterface;
