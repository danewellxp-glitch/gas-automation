# 🔧 PLANEJAMENTO ROBUSTO - SISTEMA DE NOTIFICAÇÕES V2

**Projeto:** Gas Automation - Sistema de Notificações  
**Versão:** 2.0 (Aprendizado com Erros)  
**Data:** 14/02/2026  
**Objetivo:** Implementação sem erros, incremental e testável

---

## 🎯 LIÇÕES APRENDIDAS DOS ERROS ANTERIORES

### ❌ Erros que Ocorreram na V1:

1. **ERRO JSX em .js**
   - Arquivo criado como `.js` mas continha JSX
   - Build quebrou, precisou renomear

2. **ERRO ESLint não configurado**
   - Tentamos rodar testes mas ESLint não estava configurado
   - Tivemos que usar workarounds

3. **ERRO Script npm incorreto**
   - Tentamos `npm start` mas era `npm run dev` (Vite)

4. **FALTA DE TESTES**
   - Implementamos tudo sem testar no browser
   - Não validamos cada fase antes de prosseguir

5. **SEM GIT COMMITS**
   - Sem commits separados por fase
   - Difícil de reverter mudanças específicas

6. **SEM BRANCHES**
   - Tudo no main/master
   - Reversões manuais trabalhosas

---

## ✅ ESTRATÉGIA NOVA - ZERO ERROS

### Princípios:
1. **Validar antes de implementar**
2. **Testar antes de prosseguir**
3. **Git commit após cada fase**
4. **Branches para features**
5. **Rollback automático se falhar**
6. **Nomenclatura correta desde o início**
7. **Verificação de dependências**
8. **Testes incrementais obrigatórios**

---

## 📋 PRÉ-REQUISITOS (ANTES DE COMEÇAR)

### FASE 0 - PREPARAÇÃO DO AMBIENTE

#### 0.1. Verificar Node/NPM
```bash
# Verificar versões
node --version  # >= 18.x
npm --version   # >= 9.x
```

#### 0.2. Verificar Frontend Rodando
```bash
cd frontend
npm run dev     # Deve iniciar sem erros
# Anotar porta (provavelmente 3004)
```

#### 0.3. Verificar Dependências Existentes
```bash
# Verificar se react-hot-toast está instalado
grep "react-hot-toast" package.json

# Se NÃO estiver, instalar:
npm install react-hot-toast

# Verificar lucide-react (ícones)
grep "lucide-react" package.json

# Se NÃO estiver, instalar:
npm install lucide-react

# Verificar date-fns
grep "date-fns" package.json

# Se NÃO estiver, instalar:
npm install date-fns
```

#### 0.4. Criar Branch de Feature
```bash
cd /home/daniel/gas-automation
git checkout -b feature/notifications-system
```

#### 0.5. Criar Estrutura de Pastas
```bash
# Criar pastas necessárias (se não existirem)
mkdir -p frontend/src/services
mkdir -p frontend/src/hooks
mkdir -p frontend/src/components/notifications
mkdir -p frontend/src/utils
mkdir -p frontend/public/sounds
```

#### 0.6. Verificar Estrutura
```bash
# Listar estrutura
ls -la frontend/src/services
ls -la frontend/src/hooks
ls -la frontend/src/components/notifications
ls -la frontend/public/sounds
```

✅ **CHECKLIST FASE 0:**
- [ ] Node/NPM versões corretas
- [ ] Frontend inicia sem erros
- [ ] react-hot-toast instalado
- [ ] lucide-react instalado
- [ ] date-fns instalado
- [ ] Branch criada
- [ ] Pastas criadas
- [ ] Estrutura verificada

---

## 🏗️ FASE 1 - CORE SERVICE (ROBUSTO)

### Objetivo:
Criar NotificationService com **nomenclatura correta** e **validação imediata**

### 1.1. Criar Arquivo com Extensão Correta
```bash
# ⚠️ CRÍTICO: Usar .jsx desde o início (não .js)
touch frontend/src/services/NotificationService.jsx
```

### 1.2. Implementar NotificationService

**Arquivo:** `frontend/src/services/NotificationService.jsx`

**Conteúdo:** (Versão simplificada primeiro, depois expandir)

```javascript
/**
 * NotificationService - Core do sistema de notificações
 * Versão: 2.0 - Robusta
 */

import toast from 'react-hot-toast'

class NotificationService {
  constructor() {
    this.audio = null
    this.pendingCount = 0
    this.history = []
    this.permissionGranted = false
    this.listeners = []
    this.settings = {
      sound: true,
      volume: 0.7,
      vibration: true,
      nativeNotifications: true,
      autoCloseTime: 10000, // 10 segundos
    }
    
    console.log('🔔 NotificationService inicializando...')
    this.init()
  }
  
  /**
   * Inicialização
   */
  async init() {
    try {
      await this.loadSettings()
      await this.loadHistory()
      this.loadNotificationSound()
      await this.requestNotificationPermission()
      console.log('✅ NotificationService inicializado')
    } catch (error) {
      console.error('❌ Erro ao inicializar NotificationService:', error)
    }
  }
  
  /**
   * Carregar configurações do LocalStorage
   */
  loadSettings() {
    try {
      const saved = localStorage.getItem('notification_settings')
      if (saved) {
        this.settings = { ...this.settings, ...JSON.parse(saved) }
        console.log('⚙️ Configurações carregadas:', this.settings)
      }
    } catch (error) {
      console.warn('⚠️ Erro ao carregar configurações:', error)
    }
  }
  
  /**
   * Carregar histórico do LocalStorage
   */
  loadHistory() {
    try {
      const saved = localStorage.getItem('notifications_history')
      if (saved) {
        const data = JSON.parse(saved)
        this.history = data.history || []
        this.pendingCount = data.pendingCount || 0
        console.log(`📋 Histórico carregado: ${this.history.length} notificações`)
      }
    } catch (error) {
      console.warn('⚠️ Erro ao carregar histórico:', error)
    }
  }
  
  /**
   * Carregar som de notificação
   */
  loadNotificationSound() {
    try {
      this.audio = new Audio('/sounds/notification.mp3')
      this.audio.volume = this.settings.volume
      this.audio.preload = 'auto'
      console.log('🔊 Som de notificação carregado')
    } catch (error) {
      console.warn('⚠️ Erro ao carregar som:', error)
    }
  }
  
  /**
   * Solicitar permissão para notificações nativas
   */
  async requestNotificationPermission() {
    if (!('Notification' in window)) {
      console.warn('⚠️ Browser não suporta notificações nativas')
      return false
    }
    
    if (Notification.permission === 'granted') {
      this.permissionGranted = true
      console.log('✅ Permissão de notificações concedida')
      return true
    }
    
    if (Notification.permission !== 'denied') {
      try {
        const permission = await Notification.requestPermission()
        this.permissionGranted = permission === 'granted'
        console.log(`🔐 Permissão de notificações: ${permission}`)
        return this.permissionGranted
      } catch (error) {
        console.warn('⚠️ Erro ao solicitar permissão:', error)
        return false
      }
    }
    
    return false
  }
  
  /**
   * Notificar novo pedido (método principal)
   */
  notifyNewOrder(orderData) {
    console.log('📦 Notificando novo pedido:', orderData)
    
    const notification = {
      id: `order-${orderData.order_id || Date.now()}`,
      type: 'new_order',
      title: '🔔 Novo Pedido!',
      message: this.formatOrderMessage(orderData),
      orderData,
      timestamp: new Date().toISOString(),
      read: false,
    }
    
    // Adicionar ao histórico
    this.addToHistory(notification)
    
    // Incrementar contador
    this.incrementPendingCount()
    
    // Executar ações
    if (this.settings.sound) {
      this.playSound()
    }
    
    if (this.settings.vibration) {
      this.vibrate([200, 100, 200])
    }
    
    this.showToastNotification(notification)
    
    if (this.settings.nativeNotifications && this.permissionGranted) {
      this.showNativeNotification(notification)
    }
    
    // Notificar listeners
    this.notifyListeners({ type: 'new_order', notification })
    
    return notification
  }
  
  /**
   * Formatar mensagem do pedido
   */
  formatOrderMessage(orderData) {
    const number = orderData.order_number || '#???'
    const customer = orderData.customer_name || 'Cliente'
    const amount = orderData.total_amount 
      ? `R$ ${orderData.total_amount.toFixed(2)}` 
      : ''
    const bairro = orderData.bairro || ''
    
    return `Pedido ${number} - ${customer} ${bairro ? `(${bairro})` : ''} ${amount}`.trim()
  }
  
  /**
   * Tocar som
   */
  playSound() {
    if (this.audio) {
      try {
        this.audio.currentTime = 0
        this.audio.play().catch(err => {
          console.warn('⚠️ Não foi possível tocar som:', err)
        })
      } catch (error) {
        console.warn('⚠️ Erro ao tocar som:', error)
      }
    }
  }
  
  /**
   * Vibrar dispositivo
   */
  vibrate(pattern = 200) {
    if ('vibrate' in navigator) {
      try {
        navigator.vibrate(pattern)
      } catch (error) {
        console.warn('⚠️ Erro ao vibrar:', error)
      }
    }
  }
  
  /**
   * Mostrar toast notification
   */
  showToastNotification(notification) {
    toast.success(notification.message, {
      duration: this.settings.autoCloseTime,
      icon: '🔔',
      style: {
        background: '#10B981',
        color: '#fff',
        fontSize: '14px',
      },
    })
  }
  
  /**
   * Mostrar notificação nativa
   */
  showNativeNotification(notification) {
    try {
      const nativeNotif = new Notification(notification.title, {
        body: notification.message,
        icon: '/logo192.png',
        tag: notification.id,
        requireInteraction: false,
        silent: true,
      })
      
      nativeNotif.onclick = () => {
        window.focus()
        nativeNotif.close()
      }
      
      setTimeout(() => nativeNotif.close(), 8000)
    } catch (error) {
      console.warn('⚠️ Erro ao mostrar notificação nativa:', error)
    }
  }
  
  /**
   * Adicionar ao histórico
   */
  addToHistory(notification) {
    this.history.unshift(notification)
    
    // Limitar a 50
    if (this.history.length > 50) {
      this.history = this.history.slice(0, 50)
    }
    
    this.saveHistory()
  }
  
  /**
   * Salvar histórico
   */
  saveHistory() {
    try {
      localStorage.setItem('notifications_history', JSON.stringify({
        history: this.history.slice(0, 20), // Salvar apenas 20
        pendingCount: this.pendingCount,
      }))
    } catch (error) {
      console.warn('⚠️ Erro ao salvar histórico:', error)
    }
  }
  
  /**
   * Obter histórico
   */
  getHistory() {
    return this.history
  }
  
  /**
   * Obter contador
   */
  getPendingCount() {
    return this.pendingCount
  }
  
  /**
   * Incrementar contador
   */
  incrementPendingCount() {
    this.pendingCount++
    this.updateBadge()
  }
  
  /**
   * Decrementar contador
   */
  decrementPendingCount() {
    if (this.pendingCount > 0) {
      this.pendingCount--
      this.updateBadge()
    }
  }
  
  /**
   * Atualizar badge
   */
  updateBadge() {
    this.notifyListeners({ type: 'badge_update', count: this.pendingCount })
  }
  
  /**
   * Marcar como lida
   */
  markAsRead(notificationId) {
    const notif = this.history.find(n => n.id === notificationId)
    if (notif && !notif.read) {
      notif.read = true
      this.decrementPendingCount()
      this.saveHistory()
      this.notifyListeners({ type: 'mark_read', notificationId })
    }
  }
  
  /**
   * Limpar histórico
   */
  clearHistory() {
    this.history = []
    this.pendingCount = 0
    this.saveHistory()
    this.notifyListeners({ type: 'clear_history' })
  }
  
  /**
   * Atualizar configuração
   */
  updateSetting(key, value) {
    this.settings[key] = value
    
    // Aplicar mudança imediatamente
    if (key === 'volume' && this.audio) {
      this.audio.volume = value
    }
    
    // Salvar
    try {
      localStorage.setItem('notification_settings', JSON.stringify(this.settings))
      this.notifyListeners({ type: 'setting_changed', key, value })
    } catch (error) {
      console.warn('⚠️ Erro ao salvar configuração:', error)
    }
  }
  
  /**
   * Obter configurações
   */
  getSettings() {
    return this.settings
  }
  
  /**
   * Adicionar listener
   */
  addListener(callback) {
    this.listeners.push(callback)
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback)
    }
  }
  
  /**
   * Notificar listeners
   */
  notifyListeners(data) {
    this.listeners.forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error('❌ Erro em listener:', error)
      }
    })
  }
  
  /**
   * Testar notificação
   */
  test() {
    console.log('🧪 Testando notificação...')
    this.notifyNewOrder({
      order_id: Date.now(),
      order_number: '#TESTE',
      customer_name: 'Cliente Teste',
      total_amount: 123.45,
      bairro: 'Centro',
      status: 'pending'
    })
  }
}

// Exportar instância singleton
const notificationService = new NotificationService()

export default notificationService
export { notificationService }
```

### 1.3. Criar Som de Notificação

**Opção A: Usar gerador de som**

```bash
# Criar arquivo generator.html
cat > frontend/public/sounds/generator.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>Gerador de Som de Notificação</title>
</head>
<body>
  <h1>Gerador de Som</h1>
  <button onclick="generateSound()">Gerar Som</button>
  <audio id="audio" controls></audio>
  
  <script>
    function generateSound() {
      const audioContext = new AudioContext();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = 800;
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.5);
      
      alert('Som gerado! (Use um gravador para salvar como notification.mp3)');
    }
  </script>
</body>
</html>
EOF
```

**Opção B: Usar som gratuito**

```bash
# Baixar som gratuito (exemplo)
# Ou simplesmente criar arquivo vazio por enquanto
touch frontend/public/sounds/notification.mp3
```

### 1.4. Criar README do Som

```bash
cat > frontend/public/sounds/README.md << 'EOF'
# Sons de Notificação

## notification.mp3
Som principal de notificação de novos pedidos.

### Como adicionar um som:
1. Baixe de: https://notificationsounds.com/
2. Ou use o generator.html nesta pasta
3. Salve como notification.mp3

### Requisitos:
- Formato: MP3
- Duração: 0.5-1.5 segundos
- Volume: Moderado
- Tom: Agradável (campainha suave)
EOF
```

### 1.5. VALIDAR FASE 1

```bash
# Verificar que arquivo existe com extensão correta
ls -la frontend/src/services/NotificationService.jsx

# Tentar compilar (sem iniciar servidor)
cd frontend
npm run build -- --mode development

# Se der erro, corrija antes de prosseguir
# Se OK, prosseguir
```

### 1.6. TESTAR FASE 1 (Standalone)

Criar arquivo de teste:

```bash
cat > frontend/public/test-phase1.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>Teste Fase 1 - NotificationService</title>
  <script type="module">
    // Simular react-hot-toast
    window.toast = {
      success: (msg, opts) => {
        console.log('TOAST:', msg, opts)
        alert(`Toast: ${msg}`)
      }
    }
    
    // Importar service (se possível) ou copiar código aqui
    console.log('Teste Phase 1 carregado')
  </script>
</head>
<body>
  <h1>Teste Fase 1</h1>
  <button onclick="testNotification()">Testar Notificação</button>
  
  <script>
    function testNotification() {
      // Testar manualmente
      console.log('Testando...')
      alert('Veja console para logs')
    }
  </script>
</body>
</html>
EOF
```

### 1.7. GIT COMMIT FASE 1

```bash
git add frontend/src/services/NotificationService.jsx
git add frontend/public/sounds/
git commit -m "feat(notifications): Fase 1 - NotificationService core

- Implementado NotificationService.jsx (singleton)
- Sistema de som, vibração, toast, notificações nativas
- LocalStorage para persistência
- Sistema de listeners
- Configurações personalizáveis
- Histórico de notificações

Tested: Compilação OK, sem erros
"
```

✅ **CHECKLIST FASE 1:**
- [ ] Arquivo criado como `.jsx` (não `.js`)
- [ ] Código compila sem erros
- [ ] Som notification.mp3 existe (ou placeholder)
- [ ] README criado
- [ ] Teste standalone criado
- [ ] Git commit realizado
- [ ] Frontend ainda inicia sem erros

---

## 🔗 FASE 2 - REACT HOOK (ROBUSTO)

### 2.1. Criar Hook useNotifications

**Arquivo:** `frontend/src/hooks/useNotifications.js`

```javascript
/**
 * Hook useNotifications
 * Integra NotificationService com React
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import notificationService from '../services/NotificationService'

export const useNotifications = ({ 
  enabled = true,
  autoRequestPermission = false,
  onNotification = null,
} = {}) => {
  const [pendingCount, setPendingCount] = useState(0)
  const [history, setHistory] = useState([])
  const [permissionGranted, setPermissionGranted] = useState(false)
  const [settings, setSettings] = useState({})
  const [isInitialized, setIsInitialized] = useState(false)
  
  const initRef = useRef(false)
  const listenerRef = useRef(null)
  
  // Inicializar
  useEffect(() => {
    if (!enabled || initRef.current) return
    
    initRef.current = true
    
    const initialize = async () => {
      console.log('🔔 Inicializando useNotifications...')
      
      setPendingCount(notificationService.getPendingCount())
      setHistory(notificationService.getHistory())
      setSettings(notificationService.getSettings())
      setPermissionGranted(notificationService.permissionGranted)
      
      if (autoRequestPermission && !notificationService.permissionGranted) {
        await notificationService.requestNotificationPermission()
        setPermissionGranted(notificationService.permissionGranted)
      }
      
      setIsInitialized(true)
      console.log('✅ useNotifications inicializado')
    }
    
    initialize()
  }, [enabled, autoRequestPermission])
  
  // Listener
  useEffect(() => {
    if (!enabled || !isInitialized) return
    
    listenerRef.current = notificationService.addListener((data) => {
      console.log('📬 Evento:', data.type)
      
      switch (data.type) {
        case 'badge_update':
          setPendingCount(data.count)
          break
        case 'mark_read':
        case 'clear_history':
          setHistory([...notificationService.getHistory()])
          setPendingCount(notificationService.getPendingCount())
          break
        case 'setting_changed':
          setSettings(notificationService.getSettings())
          break
        case 'new_order':
          setHistory([...notificationService.getHistory()])
          setPendingCount(notificationService.getPendingCount())
          if (onNotification) onNotification(data)
          break
        default:
          setHistory([...notificationService.getHistory()])
          setPendingCount(notificationService.getPendingCount())
      }
    })
    
    return () => {
      if (listenerRef.current) {
        listenerRef.current()
      }
    }
  }, [enabled, isInitialized, onNotification])
  
  // Escutar eventos WebSocket
  useEffect(() => {
    if (!enabled || !isInitialized) return
    
    const handleOrderCreated = (event) => {
      const { orderData } = event.detail
      console.log('📦 Novo pedido via evento:', orderData)
      notificationService.notifyNewOrder(orderData)
    }
    
    window.addEventListener('websocket:order_created', handleOrderCreated)
    
    return () => {
      window.removeEventListener('websocket:order_created', handleOrderCreated)
    }
  }, [enabled, isInitialized])
  
  // Funções
  const markAsRead = useCallback((notificationId) => {
    if (!enabled) return
    notificationService.markAsRead(notificationId)
  }, [enabled])
  
  const markAllAsRead = useCallback(() => {
    if (!enabled) return
    history.forEach(notif => {
      if (!notif.read) notificationService.markAsRead(notif.id)
    })
  }, [enabled, history])
  
  const clearHistory = useCallback(() => {
    if (!enabled) return
    notificationService.clearHistory()
  }, [enabled])
  
  const requestPermission = useCallback(async () => {
    const granted = await notificationService.requestNotificationPermission()
    setPermissionGranted(granted)
    return granted
  }, [])
  
  const updateSetting = useCallback((key, value) => {
    if (!enabled) return
    notificationService.updateSetting(key, value)
  }, [enabled])
  
  const test = useCallback(() => {
    notificationService.test()
  }, [])
  
  return {
    pendingCount,
    history,
    permissionGranted,
    settings,
    isInitialized,
    markAsRead,
    markAllAsRead,
    clearHistory,
    requestPermission,
    updateSetting,
    test,
    hasUnread: pendingCount > 0,
    unreadNotifications: history.filter(n => !n.read),
    totalNotifications: history.length,
  }
}

export default useNotifications
```

### 2.2. Criar WebSocket Helper

**Arquivo:** `frontend/src/utils/notificationWebSocketHelper.js`

```javascript
/**
 * Helper para integrar WebSocket com NotificationService
 */

class NotificationWebSocketHelper {
  handleMessage(data) {
    console.log('🔌 WebSocket message:', data)
    
    if (data.type === 'order_created') {
      this.handleOrderCreated(data)
    } else if (data.type === 'order_status_updated') {
      this.handleOrderStatusUpdated(data)
    } else if (data.type === 'map_reset') {
      this.handleMapReset(data)
    }
  }
  
  handleOrderCreated(data) {
    window.dispatchEvent(new CustomEvent('websocket:order_created', {
      detail: { orderData: data.order_data || data }
    }))
  }
  
  handleOrderStatusUpdated(data) {
    window.dispatchEvent(new CustomEvent('websocket:order_status_updated', {
      detail: { orderId: data.order_id, newStatus: data.new_status }
    }))
  }
  
  handleMapReset(data) {
    window.dispatchEvent(new CustomEvent('websocket:map_reset', {
      detail: data
    }))
  }
}

export const setupNotificationWebSocket = new NotificationWebSocketHelper()
export default setupNotificationWebSocket
```

### 2.3. Criar NotificationBell

**Arquivo:** `frontend/src/components/notifications/NotificationBell.jsx`

```javascript
/**
 * NotificationBell - Sino com contador
 */

import { Bell } from 'lucide-react'

export default function NotificationBell({ count = 0, onClick }) {
  return (
    <button
      onClick={onClick}
      className="relative p-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-full transition-colors"
      aria-label={`${count} notificações pendentes`}
      type="button"
    >
      <Bell className="w-6 h-6" />
      
      {count > 0 && (
        <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-xs font-bold text-white animate-pulse">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </button>
  )
}
```

### 2.4. VALIDAR FASE 2

```bash
# Verificar que arquivos existem
ls -la frontend/src/hooks/useNotifications.js
ls -la frontend/src/utils/notificationWebSocketHelper.js
ls -la frontend/src/components/notifications/NotificationBell.jsx

# Compilar
cd frontend
npm run build -- --mode development

# Se der erro, corrija antes de prosseguir
```

### 2.5. TESTAR FASE 2 (Isoladamente)

Criar página de teste:

**Arquivo:** `frontend/src/pages/TestPhase2.jsx`

```javascript
import { useNotifications } from '../hooks/useNotifications'
import NotificationBell from '../components/notifications/NotificationBell'

export default function TestPhase2() {
  const { 
    pendingCount, 
    history, 
    test,
    clearHistory 
  } = useNotifications({ enabled: true })
  
  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Teste Fase 2</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Notificações</h2>
            <NotificationBell count={pendingCount} onClick={() => alert('Clicou!')} />
          </div>
          
          <div className="space-y-2">
            <button
              onClick={test}
              className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              🧪 Testar Notificação
            </button>
            
            <button
              onClick={clearHistory}
              className="w-full bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
            >
              🗑️ Limpar Histórico
            </button>
          </div>
          
          <div className="mt-4">
            <p className="text-sm text-gray-600">
              Pendentes: <strong>{pendingCount}</strong>
            </p>
            <p className="text-sm text-gray-600">
              Total: <strong>{history.length}</strong>
            </p>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold mb-2">Histórico</h3>
          {history.length === 0 ? (
            <p className="text-gray-500 text-sm">Nenhuma notificação</p>
          ) : (
            <div className="space-y-2">
              {history.map(notif => (
                <div key={notif.id} className="text-sm border-b pb-2">
                  <p className="font-medium">{notif.title}</p>
                  <p className="text-gray-600">{notif.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

Adicionar rota temporária em `App.jsx`:

```javascript
// No topo
import TestPhase2 from './pages/TestPhase2'

// Nas rotas (TEMPORÁRIO)
<Route path="/test-phase-2" element={<TestPhase2 />} />
```

### 2.6. TESTAR NO BROWSER

```bash
# Garantir que frontend está rodando
cd frontend
npm run dev

# Abrir browser
# http://localhost:3004/test-phase-2

# Testar:
# 1. Clicar em "🧪 Testar Notificação"
# 2. Verificar que toast aparece
# 3. Verificar que contador aumenta
# 4. Verificar que som toca
# 5. Verificar console (logs)
# 6. Clicar em "🗑️ Limpar Histórico"
# 7. Verificar que limpa
```

### 2.7. GIT COMMIT FASE 2

```bash
git add frontend/src/hooks/useNotifications.js
git add frontend/src/utils/notificationWebSocketHelper.js
git add frontend/src/components/notifications/NotificationBell.jsx
git add frontend/src/pages/TestPhase2.jsx
git add frontend/src/App.jsx

git commit -m "feat(notifications): Fase 2 - React Hook e Bell

- Hook useNotifications completo
- WebSocket helper para integração
- NotificationBell component
- Página de teste isolada

Tested: Browser OK, toast funciona, contador funciona
"
```

✅ **CHECKLIST FASE 2:**
- [ ] Hook criado e funcional
- [ ] WebSocket helper criado
- [ ] NotificationBell criado
- [ ] Página de teste criada
- [ ] Rota temporária adicionada
- [ ] Teste no browser OK
- [ ] Toast aparece
- [ ] Som toca
- [ ] Contador funciona
- [ ] Console sem erros
- [ ] Git commit realizado

---

## 🎨 FASE 3 - UI COMPONENTS (OPCIONAL)

**DECISÃO IMPORTANTE:**

Antes de implementar Fase 3, **confirmar com usuário**:
- Fase 2 está funcionando perfeitamente?
- Deseja painel lateral e UI avançada?
- Ou prefere manter simples (só Fase 2)?

Se usuário quiser Fase 3, seguir planejamento similar...

---

## 🏭 FASE 4 - DASHBOARD INTEGRATION (OPCIONAL)

**DECISÃO IMPORTANTE:**

Antes de implementar Fase 4, **confirmar com usuário**:
- Fases 2 e 3 estão funcionando?
- Deseja integrar no OperatorDashboard?
- Ou prefere manter isolado?

Se usuário quiser Fase 4, seguir planejamento similar...

---

## 🛡️ ESTRATÉGIA DE ROLLBACK

Se algo der errado em qualquer fase:

```bash
# Reverter último commit
git reset --soft HEAD~1

# Ou reverter mudanças não commitadas
git checkout -- .

# Ou ir para branch main
git checkout main

# Ou deletar branch
git branch -D feature/notifications-system
```

---

## ✅ RESUMO DO PLANEJAMENTO ROBUSTO

### Diferenças da V1 (Com Erros):

| Aspecto | V1 (Errado) | V2 (Correto) |
|---------|-------------|--------------|
| Extensão arquivo | .js com JSX | .jsx desde início |
| Testes | Após tudo pronto | Cada fase isolada |
| Git | Sem commits | Commit por fase |
| Branches | No main | Feature branch |
| Validação | Manual | Build check |
| Dependências | Assumiu instaladas | Verifica antes |
| Rollback | Manual difícil | Git reset fácil |

### Vantagens V2:

1. ✅ **Zero erros de extensão** (.jsx desde início)
2. ✅ **Teste incremental** (cada fase isolada)
3. ✅ **Rollback fácil** (git commits)
4. ✅ **Validação prévia** (dependências, pastas)
5. ✅ **Build check** (antes de prosseguir)
6. ✅ **Página de teste** (para cada fase)
7. ✅ **Console logs** (debug fácil)
8. ✅ **Confirmação usuário** (antes de avançar)

---

## 🚀 PRÓXIMOS PASSOS

1. **Executar Fase 0** (preparação)
2. **Executar Fase 1** (core service)
3. **Testar Fase 1** standalone
4. **Confirmar com usuário** antes de Fase 2
5. **Executar Fase 2** (hook + bell)
6. **Testar Fase 2** no browser
7. **Confirmar com usuário** antes de Fase 3
8. (Repetir para fases seguintes)

---

## 📋 CHECKLIST GERAL

### Antes de Começar:
- [ ] Node/NPM funcionando
- [ ] Frontend roda sem erros
- [ ] Dependências instaladas
- [ ] Branch criada
- [ ] Pastas criadas

### Durante Implementação:
- [ ] Extensões corretas (.jsx)
- [ ] Build check após cada fase
- [ ] Teste isolado para cada fase
- [ ] Console sem erros
- [ ] Git commit após cada fase

### Antes de Prosseguir:
- [ ] Fase atual 100% funcional
- [ ] Teste no browser OK
- [ ] Usuário confirma prosseguir
- [ ] Backup (git commit) feito

---

**🎯 Este planejamento garante ZERO ERROS!**

**Quer começar pela Fase 0 (Preparação)?**
