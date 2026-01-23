# 📋 MIGRAÇÃO DE CONSOLE.LOG PARA LOGGER

**Status:** ⚠️ PENDENTE  
**Prioridade:** MÉDIA  
**Tempo Estimado:** 2-3 horas  

---

## 📊 SITUAÇÃO ATUAL

```
Total de console.* encontrados: 196 ocorrências
- console.log: ~150
- console.error: ~35
- console.warn: ~8
- console.debug: ~3
```

---

## ✅ O QUE FOI FEITO

1. **Logger Centralizado Criado**
   - Arquivo: `frontend/src/utils/logger.js`
   - Funcionalidades:
     * Logs apenas em desenvolvimento
     * Errors sempre logados
     * Warnings sempre logados
     * Métodos: log, info, debug, warn, error
     * Timestamp automático
     * Preparado para Sentry/LogRocket

2. **Documentação**
   - Exemplos de uso
   - Avisos sobre dados sensíveis
   - Boas práticas

---

## ⏳ O QUE FALTA FAZER

### **Passo 1: Substituir em Arquivos Críticos** (PRIORIDADE ALTA)

Arquivos que lidam com autenticação e dados sensíveis:

```bash
# Arquivos prioritários
frontend/src/hooks/useAuth.jsx
frontend/src/services/api.js
frontend/src/components/operator/CreateOrderPanel.jsx
frontend/src/components/admin/*
frontend/src/pages/driver/DriverLogin.jsx
```

**Substituição:**
```javascript
// Antes:
console.log('User data:', user)
console.error('Login error:', error)

// Depois:
import logger from '@/utils/logger'
logger.debug('User authenticated:', user.id)  // Não loga dados completos!
logger.error('Login error:', error)
```

---

### **Passo 2: Buscar e Substituir em Massa** (PRIORIDADE MÉDIA)

Script para automatizar parcialmente:

```bash
cd frontend/src

# Adicionar import no topo dos arquivos
find . -name "*.jsx" -o -name "*.js" | xargs sed -i '1i import logger from "@/utils/logger"'

# Substituir console.log por logger.log
find . -name "*.jsx" -o -name "*.js" | xargs sed -i 's/console\.log/logger.log/g'

# Substituir console.error por logger.error
find . -name "*.jsx" -o -name "*.js" | xargs sed -i 's/console\.error/logger.error/g'

# Substituir console.warn por logger.warn
find . -name "*.jsx" -o -name "*.js" | xargs sed -i 's/console\.warn/logger.warn/g'

# Substituir console.debug por logger.debug
find . -name "*.jsx" -o -name "*.js" | xargs sed -i 's/console\.debug/logger.debug/g'
```

⚠️ **ATENÇÃO:** Revisar manualmente após substituição automática!

---

### **Passo 3: Revisar Dados Sensíveis** (PRIORIDADE ALTA)

Buscar por logs que podem expor dados sensíveis:

```bash
# Buscar por possíveis vazamentos
grep -r "logger.log.*token" src/
grep -r "logger.log.*password" src/
grep -r "logger.log.*secret" src/
grep -r "logger.log.*key" src/
grep -r "logger.log.*customer" src/
grep -r "logger.log.*user" src/
```

**Corrigir:** Logar apenas IDs, não dados completos.

---

### **Passo 4: Remover Console.logs Desnecessários**

Alguns console.logs podem ser simplesmente removidos:

```javascript
// ❌ Remover:
console.log('Component mounted')
console.log('Data:', data)  // Se não usado em dev

// ✅ Manter (como logger.debug):
logger.debug('WebSocket connected')
logger.debug('Order created:', orderId)  // Apenas ID
```

---

## 🎯 PRIORIDADE DE ARQUIVOS

### **🔴 URGENTE (Dados Sensíveis)**
```
1. frontend/src/hooks/useAuth.jsx
2. frontend/src/services/api.js
3. frontend/src/pages/driver/DriverLogin.jsx
4. frontend/src/components/operator/CreateOrderPanel.jsx
```

### **🟡 ALTA (Lógica de Negócio)**
```
5. frontend/src/pages/admin/AdminDashboard.jsx
6. frontend/src/pages/owner/OwnerDashboard.jsx
7. frontend/src/pages/operator/OperatorDashboard.jsx
8. frontend/src/components/driver/*
9. frontend/src/services/sharedWebSocket.js
```

### **🟢 MÉDIA (Demais Arquivos)**
```
10. Todos os outros componentes
11. Pages auxiliares
12. Utilities
```

---

## ✅ CHECKLIST DE EXECUÇÃO

```
[ ] Criar logger.js (✅ FEITO)
[ ] Testar logger em dev e prod
[ ] Substituir em arquivos críticos (useAuth, api.js)
[ ] Executar script de substituição em massa
[ ] Revisar imports duplicados
[ ] Buscar e corrigir dados sensíveis
[ ] Testar aplicação completa
[ ] Verificar console no modo produção
[ ] Commit das mudanças
[ ] Documentar no CHANGELOG
```

---

## 📝 TEMPLATE DE COMMIT

```bash
git commit -m "refactor: replace console.log with centralized logger

Substitui console.* por logger centralizado em [X] arquivos:
- Logs apenas em desenvolvimento
- Errors sempre registrados
- Dados sensíveis protegidos

Arquivos alterados:
- [lista de arquivos]

Faltam [N] arquivos para migração completa.

Ref: Item #11 do Sprint 1"
```

---

## 🧪 TESTE APÓS MIGRAÇÃO

```bash
# 1. Build de produção
npm run build

# 2. Verificar que não há console.log na build
grep -r "console.log" dist/

# 3. Testar aplicação
npm run preview

# 4. Abrir DevTools e verificar:
#    - Nenhum log desnecessário em produção
#    - Errors ainda aparecem corretamente
#    - Performance não afetada
```

---

## 📚 REFERÊNCIAS

- Logger: `frontend/src/utils/logger.js`
- Exemplos: Ver comentários no próprio arquivo
- Documentação: Este arquivo

---

**Próximo Passo:** Executar substituição nos arquivos prioritários e fazer commit parcial.
