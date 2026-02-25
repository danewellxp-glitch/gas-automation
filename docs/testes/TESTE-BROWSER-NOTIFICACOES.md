# 🧪 COMO TESTAR NO BROWSER - Fase 2

**Instruções passo a passo para testar o sistema de notificações**

---

## ⚡ Teste Rápido (5 minutos)

### 1️⃣ Adicionar NotificationTester

Edite qualquer arquivo de página/componente React (ex: `DashboardOverview.jsx`):

```javascript
// No topo do arquivo, adicionar import:
import NotificationTester from '../components/notifications/NotificationTester'

// No JSX, antes do </div> de fechamento:
{process.env.NODE_ENV === 'development' && <NotificationTester />}
```

**Exemplo completo:**

```javascript
import React from 'react'
import NotificationTester from '../components/notifications/NotificationTester'

export default function MinhaPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header>
        <h1>Minha Página</h1>
      </header>
      
      <main>
        {/* Seu conteúdo aqui */}
      </main>
      
      {/* Componente de teste (canto inferior direito) */}
      {process.env.NODE_ENV === 'development' && <NotificationTester />}
    </div>
  )
}
```

---

### 2️⃣ Iniciar o Frontend

```bash
cd /home/daniel/gas-automation/frontend
npm start
```

Aguarde o servidor iniciar (geralmente em `http://localhost:3000`)

---

### 3️⃣ Abrir no Browser

1. Abrir: `http://localhost:3000`
2. Navegar até a página onde adicionou o `NotificationTester`
3. Verificar se o componente aparece no **canto inferior direito**

---

### 4️⃣ Executar Testes

#### Teste 1: Status do Sistema ✅
Verificar no componente:
- **Status:** ✅ Ativo (verde)
- **Permissão:** ❌ Não (vermelho) - normal no primeiro acesso
- **Pendentes:** 0
- **Total:** 0

#### Teste 2: Notificação Simples 🔔
1. Clicar em **"🔔 Notificação de Teste"**
2. **Verificar:**
   - ✅ Toast popup aparece (canto superior direito)
   - ✅ Contador "Pendentes" aumenta para 1
   - ✅ Som toca (se ativo)
   - ✅ Histórico mostra 1 notificação

#### Teste 3: Múltiplas Notificações 🔔🔔🔔
1. Clicar em **"🔔🔔🔔 3 Notificações"**
2. **Verificar:**
   - ✅ 3 notificações aparecem (1 por segundo)
   - ✅ Contador aumenta para 4
   - ✅ Histórico mostra 4 notificações

#### Teste 4: Solicitar Permissão 🔐
1. Clicar em **"🔐 Solicitar Permissão"**
2. **Verificar:**
   - ✅ Browser mostra popup de permissão
3. Clicar em **"Permitir"**
4. **Verificar:**
   - ✅ Status muda para "✅ Sim" (verde)

#### Teste 5: Notificação Nativa 💻
Com permissão concedida:
1. Clicar em **"🔔 Notificação de Teste"**
2. **Verificar:**
   - ✅ Toast popup aparece
   - ✅ Notificação nativa do browser aparece (mesmo com aba em segundo plano)
   - ✅ Som toca

#### Teste 6: Configurações ⚙️
1. **Desmarcar "🔊 Som"**
   - Testar notificação
   - ✅ Som não toca, mas popup aparece
   
2. **Ajustar Volume** (slider)
   - Mover para 0%
   - Testar notificação
   - ✅ Som não toca
   
3. **Marcar "🔊 Som" novamente**
   - Ajustar volume para 50%
   - Testar notificação
   - ✅ Som toca com volume médio

4. **Desmarcar "📳 Vibração"**
   - Testar em mobile
   - ✅ Dispositivo não vibra

5. **Desmarcar "💻 Nativas"**
   - Testar notificação
   - ✅ Notificação nativa não aparece, mas toast sim

#### Teste 7: Componentes de Badge 🎨
No topo do NotificationTester, verificar:
- ✅ Sino clássico com badge animado
- ✅ Badge numérico compacto
- ✅ Botão com texto + badge

Todos devem mostrar o mesmo contador.

#### Teste 8: Marcar como Lida ✓
1. Clicar em **"✓ Marcar Todas como Lidas"**
2. **Verificar:**
   - ✅ Contador "Pendentes" volta para 0
   - ✅ Histórico continua mostrando notificações (mas marcadas como lidas)

#### Teste 9: Limpar Histórico 🗑️
1. Clicar em **"🗑️ Limpar Histórico"**
2. **Verificar:**
   - ✅ Contador "Pendentes" = 0
   - ✅ Contador "Total" = 0
   - ✅ Histórico vazio

#### Teste 10: Console do Browser 🖥️
Abrir DevTools (F12) → Console:

```javascript
// Teste manual
notificationService.test()

// Notificação customizada
notificationService.notifyNewOrder({
  order_id: '999',
  order_number: 777,
  customer_name: 'Teste Manual',
  total_amount: 250.00,
  bairro: 'Teste'
})

// Simular WebSocket
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: {
    orderData: {
      order_id: '888',
      order_number: 666,
      customer_name: 'WebSocket Teste'
    }
  }
}))
```

**Verificar:**
- ✅ Comandos funcionam
- ✅ Notificações aparecem
- ✅ Logs no console são claros

---

## ✅ Checklist de Testes

- [ ] NotificationTester aparece no canto da tela
- [ ] Status do sistema correto
- [ ] Notificação simples funciona
- [ ] Múltiplas notificações funcionam
- [ ] Solicitar permissão funciona
- [ ] Notificação nativa funciona
- [ ] Som toca e pode ser desligado
- [ ] Volume é ajustável
- [ ] Vibração funciona (mobile)
- [ ] Notificações nativas podem ser desligadas
- [ ] Componentes de badge mostram contador
- [ ] Marcar como lida funciona
- [ ] Limpar histórico funciona
- [ ] Comandos do console funcionam
- [ ] LocalStorage persiste configurações (refresh page)

---

## 🐛 Troubleshooting

### ❌ NotificationTester não aparece
**Possíveis causas:**
1. Import incorreto
2. Caminho relativo errado
3. Arquivo não existe

**Solução:**
```bash
# Verificar se arquivo existe
ls frontend/src/components/notifications/NotificationTester.jsx

# Verificar import (ajustar caminho conforme necessário)
import NotificationTester from '../components/notifications/NotificationTester'
```

### ❌ Erro: "Cannot find module 'useNotifications'"
**Solução:**
Verificar caminho relativo:
```javascript
// Se componente está em: src/components/admin/
import { useNotifications } from '../../hooks/useNotifications'

// Se componente está em: src/pages/
import { useNotifications } from '../hooks/useNotifications'
```

### ❌ Som não toca
**Solução:**
1. Adicionar arquivo `notification.mp3` em `frontend/public/sounds/`
2. Ou usar o gerador: abrir `frontend/public/sounds/generator.html` no browser

### ❌ Notificações nativas não aparecem
**Solução:**
1. Verificar se permissão foi concedida (Status = ✅ Sim)
2. Verificar se "💻 Nativas" está marcado
3. Testar em browser diferente (alguns bloqueiam)

### ❌ Frontend não inicia
**Solução:**
```bash
cd frontend
npm install
npm start
```

---

## 📱 Testar em Mobile

### Chrome Android
1. Abrir `http://[IP-DO-PC]:3000` no mobile
2. Permitir notificações
3. Testar vibração (funciona)
4. Testar notificações nativas (funciona)

### Safari iOS
1. Abrir `http://[IP-DO-PC]:3000` no Safari
2. Permitir notificações
3. Vibração **não funciona** (iOS não suporta)
4. Notificações nativas funcionam

---

## 🎯 Teste de Integração WebSocket (Opcional)

Se você já tem WebSocket no projeto:

### 1. Adicionar Helper
No componente que escuta WebSocket:

```javascript
import { setupNotificationWebSocket } from '../../utils/notificationWebSocketHelper'

// Onde você processa mensagens WebSocket:
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  // Seu código existente
  // ...
  
  // ADICIONAR:
  setupNotificationWebSocket.handleMessage(data)
}
```

### 2. Testar Evento
No console do browser:

```javascript
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: {
    orderData: {
      order_id: '123',
      order_number: 456,
      customer_name: 'João Silva',
      customer_phone: '5541999999999',
      total_amount: 150.00,
      bairro: 'Centro',
      status: 'pending'
    }
  }
}))
```

**Verificar:**
- ✅ Notificação dispara
- ✅ Toast aparece
- ✅ Som toca
- ✅ Contador aumenta

---

## 🎉 Teste Completo!

Se todos os itens do checklist estão marcados:

**✅ SISTEMA DE NOTIFICAÇÕES 100% FUNCIONAL!**

### Próximos Passos:
1. Remover `NotificationTester` (manter apenas em development)
2. Integrar no dashboard real
3. Conectar com WebSocket (se disponível)
4. Deploy em produção

---

**Dúvidas?** Consulte a documentação:
- `REFERENCIA-RAPIDA-NOTIFICACOES.md`
- `docs/guias/GUIA-USO-NOTIFICACOES.md`
- `IMPLEMENTACAO_FASE2_NOTIFICACOES.md`

**Pronto para usar! 🚀🔔**
