# 🧪 GUIA RÁPIDO - TESTAR FASE 4

**Data:** 14/02/2026  
**Frontend:** http://localhost:3004  
**Status:** ✅ Pronto para testar

---

## ⚡ TESTE RÁPIDO (5 minutos)

### 1️⃣ Acessar Dashboard do Operador

```
URL: http://localhost:3004/operador
```

**Login:** Use credenciais de operador ou admin

**Verificar:**
- ✅ Sino 🔔 aparece no header (canto superior direito)
- ✅ Contador em 0
- ✅ Banner de permissão aparece (canto inferior direito)

---

### 2️⃣ Simular Notificação de Novo Pedido

Abra o **DevTools** (F12) e execute no **Console**:

```javascript
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: {
    orderData: {
      order_id: 123,
      order_number: '#001',
      customer_name: 'João Silva',
      total_amount: 150.00,
      bairro: 'Centro',
      status: 'pending'
    }
  }
}))
```

**Verificar:**
- ✅ Toast popup aparece (canto superior direito)
- ✅ Som toca 🔊
- ✅ Contador do sino aumenta (0 → 1)
- ✅ Badge pulsa com animação
- ✅ Notificação nativa pode aparecer (se permitido)

---

### 3️⃣ Abrir Painel de Notificações

Clique no **sino 🔔** no header

**Verificar:**
- ✅ Painel desliza da direita
- ✅ Overlay escuro aparece no fundo
- ✅ Notificação aparece na lista
- ✅ Header mostra "Notificações (1)"
- ✅ Botões "Marcar todas" e "Limpar" visíveis

---

### 4️⃣ Testar Filtros

No painel, clique em:
- **"Todas"** → Mostra todas
- **"Não lidas"** → Mostra apenas não lidas (1)
- **"Lidas"** → Mostra "Ainda não há notificações lidas"

**Verificar:**
- ✅ Filtros funcionam
- ✅ Contador correto

---

### 5️⃣ Marcar Como Lida

Clique em **uma notificação** na lista

**Verificar:**
- ✅ Barra azul lateral desaparece
- ✅ Cor muda (azul → cinza)
- ✅ Contador diminui (1 → 0)
- ✅ Notificação move para "Lidas"

---

### 6️⃣ Ver Detalhes do Pedido

Na notificação, clique em **"👁️ Ver Detalhes"** (ou clique na notificação)

**Verificar:**
- ✅ Painel fecha
- ✅ Dashboard muda para aba "Pedidos pendentes"
- ✅ Console mostra: `📦 Ver pedido: 123`

---

### 7️⃣ Aprovar Pedido Direto do Toast

Simule nova notificação (passo 2) e clique em **"✅ Aprovar"** no toast

**Verificar:**
- ✅ Console mostra: `✅ Aprovar pedido: 123`
- ✅ Requisição PATCH é feita (Network tab)
- ✅ Toast de sucesso/erro aparece

---

### 8️⃣ Solicitar Permissão

Se banner de permissão aparece, clique em **"Permitir Agora"**

**Verificar:**
- ✅ Browser pede permissão
- ✅ Após permitir, banner desaparece
- ✅ Próximas notificações incluem notificação nativa

---

### 9️⃣ Limpar Histórico

Abra o painel e clique em **"Limpar"**

**Verificar:**
- ✅ Popup de confirmação aparece
- ✅ Após confirmar, lista fica vazia
- ✅ Contador volta para 0
- ✅ Mostra "Nenhuma notificação"

---

### 🔟 Múltiplas Notificações

Execute o script do passo 2 **várias vezes** (3-5x)

**Verificar:**
- ✅ Cada notificação aparece
- ✅ Contador aumenta (1, 2, 3...)
- ✅ Som toca para cada uma
- ✅ Todas aparecem no histórico
- ✅ "Marcar todas" funciona

---

## ✅ Checklist Completo

- [ ] Sino aparece no header
- [ ] Contador inicia em 0
- [ ] Banner de permissão aparece
- [ ] Simular notificação funciona
- [ ] Toast popup aparece
- [ ] Som toca
- [ ] Contador aumenta
- [ ] Badge pulsa
- [ ] Painel abre/fecha com animação
- [ ] Overlay aparece
- [ ] Notificações aparecem na lista
- [ ] Filtros funcionam (todas, não lidas, lidas)
- [ ] Marcar como lida funciona
- [ ] Marcar todas funciona
- [ ] Ver detalhes navega para pedidos
- [ ] Aprovar pedido faz requisição
- [ ] Limpar histórico funciona
- [ ] Permissão pode ser solicitada
- [ ] Notificações nativas funcionam
- [ ] Múltiplas notificações funcionam

---

## 🐛 Se Algo Não Funcionar

### Erro no Console?
1. Abrir DevTools (F12)
2. Ver mensagens de erro
3. Verificar imports

### Som não toca?
1. Adicionar `notification.mp3` em `/frontend/public/sounds/`
2. Verificar volume do browser
3. Verificar se configurações bloqueiam áudio

### Badge não aparece?
1. Verificar se `NotificationBell` está importado
2. Verificar se `headerActions` está sendo passado
3. Verificar console por erros

### Painel não abre?
1. Verificar se `showNotificationPanel` está funcionando
2. Verificar se `NotificationPanel` está renderizado
3. Verificar CSS/Tailwind

### Permissão não funciona?
1. Verificar se browser suporta (Chrome, Firefox, Edge)
2. Verificar se não está bloqueado nas configurações
3. Limpar permissões antigas (chrome://settings/content/notifications)

---

## 🎯 Resultado Esperado

Se tudo funcionar:

✅ **Notificações aparecem instantaneamente**  
✅ **Som toca para cada notificação**  
✅ **Painel abre/fecha suavemente**  
✅ **Filtros funcionam perfeitamente**  
✅ **Ações rápidas funcionam**  
✅ **Histórico persiste (refresh page)**  

🎉 **FASE 4 100% FUNCIONAL!**

---

## 📝 Comandos Úteis

### Simular Notificação de Teste
```javascript
window.dispatchEvent(new CustomEvent('websocket:order_created', {
  detail: {
    orderData: {
      order_id: Date.now(),
      order_number: `#${Math.floor(Math.random() * 1000)}`,
      customer_name: 'Cliente Teste',
      total_amount: 100 + Math.random() * 200,
      bairro: ['Centro', 'Jardins', 'Vila Nova'][Math.floor(Math.random() * 3)],
      status: 'pending'
    }
  }
}))
```

### Limpar Histórico via Console
```javascript
localStorage.removeItem('notifications_history')
window.location.reload()
```

### Verificar Permissões
```javascript
console.log('Permissão:', Notification.permission)
```

### Testar Som Manualmente
```javascript
const audio = new Audio('/sounds/notification.mp3')
audio.play()
```

---

**🚀 Pronto para testar! Acesse: http://localhost:3004/operador**
