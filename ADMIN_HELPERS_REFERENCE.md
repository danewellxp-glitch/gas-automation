# Referência de Admin Helpers

## 📚 Visão Geral

O arquivo `frontend/src/utils/adminHelpers.js` contém funções utilitárias exportadas do `painel_admin.html` para reutilização em componentes React.

## 🔧 Como Usar

### Importar Helpers

```javascript
import {
  formatRole,
  formatDateTime,
  filterUsers,
  sortUsers,
  showToast,
  debounce,
  // ... outras funções
} from '../../utils/adminHelpers'
```

---

## 📋 Funções Disponíveis

### 1️⃣ Formatação de Dados

#### `formatRole(role)` 
Converte role para exibição amigável em português.

```javascript
import { formatRole } from '../../utils/adminHelpers'

formatRole('admin')     // → 'Admin'
formatRole('operator')  // → 'Operador'
formatRole('owner')     // → 'Proprietário'
formatRole('user')      // → 'Usuário'
```

---

#### `getRoleBadge(role)`
Retorna classe CSS para estilizar badge de role.

```javascript
import { getRoleBadge } from '../../utils/adminHelpers'

getRoleBadge('admin')    // → 'danger'
getRoleBadge('operator') // → 'blue'
getRoleBadge('owner')    // → 'purple'
getRoleBadge('user')     // → 'gray'

// Uso em JSX:
<span className={`badge badge-${getRoleBadge(user.role)}`}>
  {user.role}
</span>
```

---

#### `formatDateTime(timestamp)`
Formata data/hora completa para formato legível pt-BR.

```javascript
import { formatDateTime } from '../../utils/adminHelpers'

formatDateTime('2025-01-20T10:30:00')
// → '20/01/2025, 10:30:00'
```

---

#### `formatTime(timestamp)`
Formata apenas a hora em formato pt-BR (HH:mm).

```javascript
import { formatTime } from '../../utils/adminHelpers'

formatTime('2025-01-20T10:30:00')
// → '10:30'
```

---

#### `formatAction(action)`
Converte código de ação para descrição em português.

```javascript
import { formatAction } from '../../utils/adminHelpers'

formatAction('user_created')    // → 'Usuário criado'
formatAction('role_changed')    // → 'Role alterada'
formatAction('user_deactivated') // → 'Usuário desativado'
```

---

#### `getStatusBadge(status)`
Retorna classe CSS para badge de status.

```javascript
import { getStatusBadge } from '../../utils/adminHelpers'

getStatusBadge('active')  // → 'success'
getStatusBadge('pending') // → 'warning'
getStatusBadge('closed')  // → 'secondary'
```

---

### 2️⃣ Validação

#### `isValidEmail(email)`
Valida formato de email.

```javascript
import { isValidEmail } from '../../utils/adminHelpers'

isValidEmail('user@example.com')  // → true
isValidEmail('invalid-email')     // → false
```

---

#### `isValidPassword(password)`
Valida senha (mínimo 6 caracteres).

```javascript
import { isValidPassword } from '../../utils/adminHelpers'

isValidPassword('abc123')    // → true
isValidPassword('12345')     // → false (< 6 caracteres)
```

---

#### `isValidName(name)`
Valida nome (mínimo 3 caracteres).

```javascript
import { isValidName } from '../../utils/adminHelpers'

isValidName('João Silva')  // → true
isValidName('Jo')          // → false
```

---

### 3️⃣ Notificações

#### `showToast(message, type, duration)`
Exibe notificação temporária (Toast).

```javascript
import { showToast } from '../../utils/adminHelpers'

// Sucesso
showToast('Usuário criado com sucesso!', 'success')

// Erro
showToast('Erro ao carregar dados', 'error')

// Aviso
showToast('Ação não pode ser desfeita', 'warning')

// Info
showToast('Operação em andamento...', 'info')

// Com duração customizada
showToast('Mensagem', 'success', 5000) // 5 segundos
```

**Tipos disponíveis:** `success`, `error`, `warning`, `info`

---

### 4️⃣ Operações com Usuários

#### `filterUsers(users, searchTerm)`
Filtra array de usuários por termo de busca (email, nome, username).

```javascript
import { filterUsers } from '../../utils/adminHelpers'

const allUsers = [
  { id: 1, name: 'João', email: 'joao@example.com' },
  { id: 2, name: 'Maria', email: 'maria@example.com' },
  { id: 3, name: 'Pedro', email: 'pedro@example.com' }
]

const filtered = filterUsers(allUsers, 'joao')
// → [{ id: 1, name: 'João', email: 'joao@example.com' }]
```

---

#### `sortUsers(users, field, direction)`
Ordena array de usuários por campo específico.

```javascript
import { sortUsers } from '../../utils/adminHelpers'

const users = [...]

// Ordenar por email (crescente)
sortUsers(users, 'email', 'asc')

// Ordenar por data de criação (decrescente)
sortUsers(users, 'created_at', 'desc')

// Ordenar por role (com ordem customizada: admin < owner < operator < user)
sortUsers(users, 'role', 'asc')

// Campos suportados: name, email, role, created_at, updated_at
```

---

### 5️⃣ Modal e UI

#### `openModal(modalId)`
Abre modal com animação.

```javascript
import { openModal } from '../../utils/adminHelpers'

openModal('user-modal')
```

---

#### `closeModal(modalId)`
Fecha modal com animação.

```javascript
import { closeModal } from '../../utils/adminHelpers'

closeModal('user-modal')
```

---

#### `showConfirmDialog(title, message, onConfirm, onCancel)`
Exibe diálogo de confirmação.

```javascript
import { showConfirmDialog } from '../../utils/adminHelpers'

showConfirmDialog(
  'Confirmar Ação',
  'Tem certeza que deseja desativar este usuário?',
  () => {
    // Usuário clicou "Sim"
    console.log('Ação confirmada')
  },
  () => {
    // Usuário clicou "Não"
    console.log('Ação cancelada')
  }
)

// Retorna Promise
const confirmed = await showConfirmDialog(...)
if (confirmed) {
  // Fazer algo
}
```

---

### 6️⃣ LocalStorage

#### `saveToStorage(key, value)`
Salva dados no localStorage (converte para JSON automaticamente).

```javascript
import { saveToStorage } from '../../utils/adminHelpers'

saveToStorage('user', { id: 1, name: 'João' })
saveToStorage('theme', 'dark')
saveToStorage('preferences', { language: 'pt-BR', timezone: 'America/Sao_Paulo' })
```

---

#### `getFromStorage(key, defaultValue)`
Recupera dados do localStorage (converte de JSON automaticamente).

```javascript
import { getFromStorage } from '../../utils/adminHelpers'

const user = getFromStorage('user')          // → { id: 1, name: 'João' }
const theme = getFromStorage('theme')        // → 'dark'
const prefs = getFromStorage('preferences')  // → { language: 'pt-BR', timezone: '...' }

// Com valor padrão
const color = getFromStorage('color', '#000000')
```

---

### 7️⃣ Debounce

#### `debounce(func, delay)`
Cria versão "debounced" de uma função (delay antes de executar).

```javascript
import { debounce } from '../../utils/adminHelpers'

// Sem debounce: busca executa 100x enquanto digita
const handleSearch = (term) => {
  const filtered = filterUsers(users, term)
}

// Com debounce: busca executa somente 300ms após parar de digitar
const debouncedSearch = debounce((term) => {
  const filtered = filterUsers(users, term)
}, 300)

// No input:
<input onChange={(e) => debouncedSearch(e.target.value)} />
```

---

## 📖 Exemplo Completo: AdminDashboard.jsx

```javascript
import { useState, useEffect } from 'react'
import { apiRequest } from '../../utils/api'
import {
  formatRole,
  getRoleBadge,
  formatDateTime,
  filterUsers,
  sortUsers,
  showToast,
  debounce
} from '../../utils/adminHelpers'

export default function AdminDashboard() {
  const [users, setUsers] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [sortField, setSortField] = useState('created_at')
  const [sortDirection, setSortDirection] = useState('desc')

  // Busca com debounce
  const handleSearch = debounce((term) => {
    setSearchTerm(term)
  }, 300)

  // Aplicar filtros e ordenação
  const displayedUsers = sortUsers(
    filterUsers(users, searchTerm),
    sortField,
    sortDirection
  )

  const handleUpdateUser = async (userId, newData) => {
    try {
      await apiRequest(`users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(newData)
      })
      showToast('Usuário atualizado com sucesso!', 'success')
      // Recarregar usuários
    } catch (error) {
      showToast(`Erro: ${error.message}`, 'error')
    }
  }

  return (
    <div>
      {/* Barra de busca */}
      <input
        onChange={(e) => handleSearch(e.target.value)}
        placeholder="Buscar usuários..."
      />

      {/* Tabela com usuários filtrados e ordenados */}
      <table>
        <tbody>
          {displayedUsers.map(user => (
            <tr key={user.id}>
              <td>{user.email}</td>
              <td>{user.name}</td>
              <td>
                <span className={`badge-${getRoleBadge(user.role)}`}>
                  {formatRole(user.role)}
                </span>
              </td>
              <td>{formatDateTime(user.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

---

## 🎯 Casos de Uso Comuns

### Caso 1: Adicionar Nova Coluna Ordenável à Tabela

```javascript
const [sortField, setSortField] = useState('created_at')
const [sortDirection, setSortDirection] = useState('desc')

const handleSort = (field) => {
  if (sortField === field) {
    setSortDirection(d => d === 'asc' ? 'desc' : 'asc')
  } else {
    setSortField(field)
    setSortDirection('asc')
  }
}

const sortedUsers = sortUsers(filteredUsers, sortField, sortDirection)

// Na tabela:
<th onClick={() => handleSort('email')}>
  Email {sortField === 'email' && (sortDirection === 'asc' ? '↑' : '↓')}
</th>
```

---

### Caso 2: Validar Formulário Antes de Submeter

```javascript
import { isValidEmail, isValidPassword, isValidName } from '../../utils/adminHelpers'

const handleSubmit = (e) => {
  e.preventDefault()
  
  if (!isValidName(formData.name)) {
    showToast('Nome deve ter pelo menos 3 caracteres', 'warning')
    return
  }
  
  if (!isValidEmail(formData.email)) {
    showToast('Email inválido', 'warning')
    return
  }
  
  if (!isValidPassword(formData.password)) {
    showToast('Senha deve ter pelo menos 6 caracteres', 'warning')
    return
  }
  
  // Submeter formulário
}
```

---

### Caso 3: Implementar Busca em Tempo Real com Debounce

```javascript
const [searchTerm, setSearchTerm] = useState('')

const debouncedSearch = debounce((term) => {
  // Aqui a busca realmente é executada
  const results = filterUsers(users, term)
  updateResults(results)
}, 500)

const handleInputChange = (e) => {
  const value = e.target.value
  // Update imediato no input para responsividade
  setSearchTerm(value)
  // Busca atrasada
  debouncedSearch(value)
}
```

---

### Caso 4: Persisting User Preferences

```javascript
import { saveToStorage, getFromStorage } from '../../utils/adminHelpers'

// Ao carregar componente
useEffect(() => {
  const savedPrefs = getFromStorage('admin_preferences', {
    sortField: 'created_at',
    theme: 'light'
  })
  setSortField(savedPrefs.sortField)
  setTheme(savedPrefs.theme)
}, [])

// Ao mudar preferência
const updatePreference = (key, value) => {
  const prefs = getFromStorage('admin_preferences', {})
  saveToStorage('admin_preferences', { ...prefs, [key]: value })
}
```

---

## 🔗 Funções Relacionadas

| Função | Descrição | Retorno |
|--------|-----------|---------|
| `formatRole()` | Converte role para pt-BR | String |
| `getRoleBadge()` | Classe CSS para role | String |
| `formatDateTime()` | Data/hora legível | String |
| `formatTime()` | Apenas hora | String |
| `formatAction()` | Descrição da ação | String |
| `isValidEmail()` | Valida email | Boolean |
| `isValidPassword()` | Valida senha | Boolean |
| `isValidName()` | Valida nome | Boolean |
| `filterUsers()` | Filtra usuários | Array |
| `sortUsers()` | Ordena usuários | Array |
| `debounce()` | Cria função debounced | Function |
| `showToast()` | Exibe notificação | Void |
| `openModal()` | Abre modal | Void |
| `closeModal()` | Fecha modal | Void |
| `showConfirmDialog()` | Diálogo confirmação | Promise |
| `saveToStorage()` | Salva no localStorage | Void |
| `getFromStorage()` | Lê do localStorage | Any |

---

## 📝 Notas Importantes

1. **Toast Automático:** `showToast()` cria um elemento DOM que desaparece automaticamente após 3 segundos
2. **Debounce:** Útil para buscas em tempo real e validações, evita chamadas excessivas à API
3. **Storage:** Sempre use `try-catch` internamente para evitar erros de quota ou permission
4. **Formatação:** Todas as funções de formatação usam `pt-BR` como locale padrão
5. **Sort de Roles:** Segue ordem: admin < owner < operator < user

---

## 🚀 Próximas Funcionalidades

- [ ] Exportar dados para CSV
- [ ] Importar usuários em lote
- [ ] Gráficos de estatísticas
- [ ] Logs de auditoria completos
- [ ] Gestão de permissões granulares

