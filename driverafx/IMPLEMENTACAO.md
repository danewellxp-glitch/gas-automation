# 🚗 Dashboard do Motorista - Estilo Uber Driver App

## 📋 Visão Geral

Dashboard moderno e intuitivo para motoristas, inspirado no app da Uber Driver, com design profissional, animações suaves e experiência mobile-first.

## ✨ Principais Características

### Design & UX
- **Interface Dark Mode**: Gradientes sutis de slate com acentos em verde esmeralda
- **Mobile-First**: Totalmente responsivo, otimizado para uso em smartphones
- **Animações Fluidas**: Transições suaves e feedback visual imediato
- **Glassmorphism**: Efeitos de vidro fosco e blur para profundidade
- **Gradientes Modernos**: Cards com gradientes sutis para melhor hierarquia visual

### Funcionalidades

#### 1. **Status do Motorista**
- Toggle rápido entre estados: Offline, Disponível, Ocupado, Pausa
- Indicador visual de status com cor e pulso animado
- Atualização em tempo real do status

#### 2. **Dashboard de Estatísticas**
- 4 cards principais com métricas do dia:
  - 📦 Entregas realizadas
  - ⭐ Avaliação média
  - ⏱️ Tempo médio de entrega
  - 💰 Ganhos do dia
- Ícones coloridos e gradientes por categoria
- Animações ao hover

#### 3. **Tempo Trabalhado**
- Exibição de horas trabalhadas (hoje e na semana)
- Integração com sistema de time tracking
- Visual limpo e legível

#### 4. **Entregas Ativas**
- Lista de entregas em andamento
- Cards expandíveis com detalhes completos
- Status visual claro (Coletada, A Caminho, Chegou, etc)
- Ações rápidas:
  - 📍 Abrir no Google Maps
  - 📞 Ligar para o cliente
  - 🔄 Atualizar status da entrega
  - ⚠️ Reportar problema

#### 5. **Entregas Disponíveis**
- Lista de entregas aguardando aceitação
- Botão destacado para aceitar entrega
- Informações essenciais visíveis (endereço, bairro, tempo estimado)

#### 6. **Modal de Detalhes**
- Visualização completa da entrega
- Informações do cliente e pedido
- Botões de ação contextuais
- Fluxo de status passo a passo
- Design em slide-up para mobile

#### 7. **Menu Lateral**
- Acesso rápido a:
  - Perfil do motorista
  - Histórico de entregas
  - Configurações
  - Logout
- Animação suave de abertura/fechamento

## 🎨 Paleta de Cores

```javascript
// Cores principais
Primary: Emerald/Teal (Verde da Uber)
- bg-emerald-500 (#10B981)
- bg-teal-600 (#0D9488)

// Background
- bg-slate-900 (#0F172A)
- bg-slate-800 (#1E293B)
- bg-slate-700 (#334155)

// Status Colors
- Disponível: Green (#10B981)
- Ocupado: Red (#EF4444)
- Pausa: Yellow (#F59E0B)
- Offline: Gray (#6B7280)

// Accents
- Blue (#3B82F6) - Links e navegação
- Purple (#A855F7) - Ganhos
- Amber (#F59E0B) - Avaliação
```

## 🚀 Instalação e Configuração

### 1. Copiar Arquivos

```bash
# Copiar componente React
cp DriverDashboard.jsx frontend/src/pages/driver/

# Copiar estilos
cp driver-dashboard.css frontend/src/styles/
```

### 2. Importar no seu projeto

```javascript
// Em App.js ou routes
import DriverDashboard from './pages/driver/DriverDashboard';
import './styles/driver-dashboard.css';

// Adicionar rota
<Route path="/driver/dashboard" element={<DriverDashboard />} />
```

### 3. Configurar API URL

No arquivo `DriverDashboard.jsx`, alterar a URL da API se necessário:

```javascript
const API_URL = 'http://SEU_IP:8000'; // Linha 30
```

### 4. Dependências Necessárias

```bash
npm install lucide-react react-hot-toast
```

## 📱 Uso

### Fluxo do Motorista

1. **Login** → Motorista faz login com suas credenciais
2. **Dashboard** → Vê estatísticas e entregas disponíveis
3. **Mudar Status** → Alterna entre Disponível/Ocupado/Pausa
4. **Aceitar Entrega** → Clica em "Aceitar Entrega" nas disponíveis
5. **Atualizar Status** → Progride pelos status (Coletada → A Caminho → Chegou → Entregue)
6. **Navegar** → Usa integração com Maps para chegar ao destino
7. **Finalizar** → Marca como entregue e recebe próxima entrega

### Atalhos e Ações Rápidas

- **Ligar para cliente**: Um toque no número de telefone
- **Abrir Maps**: Botão direto para navegação
- **Reportar problema**: Modal para registrar problemas
- **Atualizar status**: Um clique para próximo status

## 🔧 Personalização

### Alterar Cores

Edite as classes Tailwind no arquivo JSX:

```javascript
// Mudar cor primária de verde para azul
className="bg-emerald-500" → className="bg-blue-500"
```

### Adicionar Mais Estatísticas

No array de stats, adicione novos cards:

```javascript
<div className="bg-gradient-to-br from-red-500/20 to-red-600/20 ...">
  <Icon className="w-8 h-8 text-red-400" />
  <p className="text-3xl font-bold text-white">{stats.newMetric}</p>
  <p className="text-red-300 text-sm">Nova Métrica</p>
</div>
```

### Customizar Status de Entregas

Edite o objeto `DELIVERY_STATUS`:

```javascript
const DELIVERY_STATUS = {
  novo_status: { 
    label: 'Novo Status', 
    color: 'bg-pink-100 text-pink-700', 
    icon: IconComponent 
  }
};
```

## 🔌 Integrações

### WebSocket (Tempo Real)

O componente está preparado para integração WebSocket:

```javascript
// Adicionar hook de WebSocket
import { useWebSocketDriver } from '../hooks/useWebSocketDriver';

const DriverDashboard = () => {
  const { connected, lastMessage } = useWebSocketDriver();
  
  useEffect(() => {
    if (lastMessage?.type === 'new_delivery') {
      loadDriverData(); // Recarregar dados
    }
  }, [lastMessage]);
};
```

### Notificações Push

Adicionar suporte a notificações:

```javascript
// Solicitar permissão
if ('Notification' in window && Notification.permission === 'default') {
  Notification.requestPermission();
}

// Enviar notificação
new Notification('Nova Entrega!', {
  body: 'Você tem uma nova entrega disponível',
  icon: '/icon.png',
  badge: '/badge.png'
});
```

### Geolocalização

Adicionar rastreamento GPS:

```javascript
const [location, setLocation] = useState(null);

useEffect(() => {
  if ('geolocation' in navigator) {
    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        });
      },
      (error) => console.error('Erro GPS:', error),
      { enableHighAccuracy: true }
    );
    
    return () => navigator.geolocation.clearWatch(watchId);
  }
}, []);
```

## 📊 APIs Utilizadas

### Endpoints Principais

```javascript
// Autenticação
POST /api/auth/login
GET  /api/drivers/me

// Entregas
GET  /api/drivers/me/deliveries/active
GET  /api/drivers/deliveries/available
POST /api/drivers/deliveries/{id}/accept
PUT  /api/drivers/deliveries/{id}/status

// Status e Estatísticas
PUT  /api/drivers/me/status
GET  /api/drivers/me/stats/today
GET  /api/drivers/me/time-worked
```

### Formato de Resposta

```javascript
// Driver
{
  "id": "uuid",
  "name": "João Silva",
  "phone": "+55...",
  "status": "available",
  "rating": 4.8,
  "total_deliveries": 150
}

// Delivery
{
  "id": "uuid",
  "status": "in_transit",
  "bairro": "Centro",
  "estimated_minutes": 30,
  "order": {
    "numero_pedido": "12345",
    "cliente_nome": "Maria",
    "telefone": "+55...",
    "endereco": "Rua X, 123"
  }
}
```

## 🐛 Troubleshooting

### Problema: Dashboard não carrega

**Solução**: Verificar se o token está válido no localStorage

```javascript
const token = localStorage.getItem('token');
if (!token) {
  window.location.href = '/driver/login';
}
```

### Problema: Entregas não aparecem

**Solução**: Verificar se o status do motorista está correto

```javascript
// Motorista precisa estar "available" para ver entregas disponíveis
updateDriverStatus('available');
```

### Problema: Erro 401 nas requisições

**Solução**: Token expirado, fazer logout e login novamente

```javascript
// Adicionar interceptor para erros 401
if (response.status === 401) {
  localStorage.removeItem('token');
  window.location.href = '/driver/login';
}
```

## 📈 Performance

### Otimizações Implementadas

1. **Auto-refresh inteligente**: 30 segundos (configurável)
2. **Loading states**: Feedback visual em todas as ações
3. **Lazy loading**: Modal só renderiza quando aberto
4. **Memoização**: useCallback para funções que não mudam

### Melhorias Futuras

- [ ] Cache de dados com React Query
- [ ] Virtual scrolling para listas longas
- [ ] Service Worker para modo offline
- [ ] Code splitting por rota
- [ ] Imagens otimizadas (WebP)

## 🎯 Checklist de Implementação

### Fase 1: Core (Essencial)
- [x] Layout responsivo
- [x] Toggle de status
- [x] Lista de entregas ativas
- [x] Lista de entregas disponíveis
- [x] Aceitar entrega
- [x] Atualizar status
- [x] Modal de detalhes

### Fase 2: Integrações
- [ ] WebSocket em tempo real
- [ ] Geolocalização GPS
- [ ] Notificações push
- [ ] Google Maps integração

### Fase 3: Melhorias
- [ ] Histórico de entregas
- [ ] Perfil do motorista
- [ ] Filtros e busca
- [ ] Modo offline
- [ ] Testes E2E

## 📝 Notas Importantes

1. **Mobile First**: O design foi pensado primeiro para mobile
2. **Acessibilidade**: Todos os botões têm áreas de toque adequadas (min 44x44px)
3. **Performance**: Auto-refresh limitado a 30s para não sobrecarregar
4. **UX**: Feedback visual imediato em todas as ações
5. **Segurança**: Token JWT obrigatório em todas as requisições

## 🎨 Screenshots Conceituais

### Dashboard Principal
- Header com foto e status do motorista
- 4 cards de estatísticas com gradientes
- Tempo trabalhado destacado
- Listas de entregas com cards limpos

### Modal de Detalhes
- Slide-up animation (mobile)
- Informações completas da entrega
- Botões de ação destacados
- Status visual claro

### Menu Lateral
- Animação suave
- Opções de navegação
- Botão de logout destacado

## 🤝 Suporte

Para dúvidas ou problemas:
1. Verificar logs do navegador (F12 → Console)
2. Verificar resposta da API (Network tab)
3. Confirmar que backend está rodando
4. Validar token JWT

## 📄 Licença

Este componente faz parte do sistema Gas Automation.
Desenvolvido em Janeiro de 2026.
