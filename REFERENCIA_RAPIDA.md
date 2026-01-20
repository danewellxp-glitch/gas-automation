╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                      🚀 REFERÊNCIA RÁPIDA                                 ║
║                                                                            ║
║                    Tudo que Você Precisa Saber                           ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝


## 🎯 ACESSO RÁPIDO

**Abrir Sistema:**
```
http://localhost:3001
```

**Credenciais:**
```
Email:    admin@gasautomation.local
Senha:    Admin@123456
```

**Dashboards:**
```
Admin:    http://localhost:3001/admin
Operator: http://localhost:3001/operador
Owner:    http://localhost:3001/owner
```


## 📊 ROLES E PERMISSÕES

```
┌──────────┬────────────┬─────────────────────────────────────┐
│ Role     │ Dashboard  │ Permissões                          │
├──────────┼────────────┼─────────────────────────────────────┤
│ admin    │ /admin     │ • Gerenciar usuários               │
│          │            │ • Editar roles                     │
│          │            │ • Ver configurações                │
├──────────┼────────────┼─────────────────────────────────────┤
│ operator │ /operador  │ • Atender conversas                │
│          │            │ • Gerenciar pedidos                │
│          │            │ • Ver histórico                    │
├──────────┼────────────┼─────────────────────────────────────┤
│ owner    │ /owner     │ • Ver relatórios                   │
│          │            │ • KPIs e métricas                 │
│          │            │ • Visão executiva                 │
├──────────┼────────────┼─────────────────────────────────────┤
│ user     │ /operador  │ • Acesso básico                    │
│          │            │ • Igual ao operator               │
└──────────┴────────────┴─────────────────────────────────────┘
```


## 🔄 FLUXO DE LOGIN

```
1. Acessa http://localhost:3001
   ↓
2. Vê tela de login (se não autenticado)
   ↓
3. Entra email + senha
   ↓
4. Clica "Entrar"
   ↓
5. Backend valida credenciais
   ↓
6. Retorna token + role + email
   ↓
7. Frontend salva em localStorage
   ↓
8. Redireciona para dashboard da role
   ↓
   ├─ admin    → /admin
   ├─ operator → /operador
   ├─ owner    → /owner
   └─ user     → /operador
```


## 📱 TELAS PRINCIPAIS

### Login
```
┌────────────────────────────────┐
│  Gas Automation                │
│  Sistema de Gerenciamento      │
│                                │
│  Email: [pré-preenchido]       │
│  Senha: [pré-preenchido]       │
│                                │
│  [     Entrar     ]            │
└────────────────────────────────┘
```

### Admin Dashboard
```
┌─────────────┬──────────────────────┐
│ Menu Lateral│ Gerenciar Usuários   │
│             │                      │
│ • Dashboard │ Email | Nome | Role  │
│ • Usuários  │────────────────────  │
│ • Relatórios│ admin | Admin| admin │
│ • Config    │ op@.. │João | op    │
│             │ user@.| Pedro| user  │
│ [Sair]      │                      │
│             │ [Editar] [Editar]   │
└─────────────┴──────────────────────┘
```

### Operator Dashboard
```
┌─────────────┬──────────────────────┐
│ Menu Lateral│ Conversas Ativas      │
│             │                      │
│ • Dashboard │ João Silva           │
│ • Conversas │ Maria Santos         │
│ • Pedidos   │ Pedro Oliveira       │
│ • Config    │                      │
│             │ Conversas: 3         │
│ [Sair]      │ Pedidos: 0           │
└─────────────┴──────────────────────┘
```


## 🛠️ ADMIN - GERENCIAR ROLES

**Passo a Passo:**

1. Logado como admin? → Automático /admin
2. Encontre na tabela: Email, Nome, Role Atual
3. Clique: [Editar]
4. Modal abre com dropdown:
   ```
   [ ] admin
   [x] operator ← selecionado
   [ ] owner
   [ ] user
   ```
5. Selecione nova role
6. Clique: [Salvar]
7. Usuário atualizado!

**Próximo Login:**
O usuário vai para seu novo dashboard ✅


## 💾 localStorage

**Após login bem-sucedido:**

```javascript
localStorage.token
// eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

localStorage.user
// {
//   email: "admin@gasautomation.local",
//   role: "admin"
// }
```

**Para limpar:**
```
F12 → Application → Local Storage → Delete all
F5 (recarregar)
```


## 🌐 Endpoints da API

```
POST /api/auth/login
  Input:  {email, password}
  Output: {access_token, role, email}

GET /api/users
  Requer: admin
  Output: [{id, email, username, full_name, role, is_active}, ...]

GET /api/users/me
  Output: {id, email, username, full_name, role, is_active}

PUT /api/users/{id}/role
  Requer: admin
  Input:  {role: "operator"}
  Output: {message, user}
```


## 🧪 Testes Rápidos

### Teste 1: Login Funciona?
```
1. Abra http://localhost:3001
2. Veja tela de login → ✅ OK
3. Clique "Entrar"
4. Veja /admin → ✅ Login funciona
```

### Teste 2: Role Persistence?
```
1. Admin edita role de usuário para "operator"
2. Logout
3. Login com novo usuário
4. Vê /operador → ✅ Role salvo
```

### Teste 3: Proteção de Rotas?
```
1. Logado como operator
2. Tenta /admin
3. Redireciona para /operador → ✅ Protegido
```

### Teste 4: Sem Token?
```
1. Limpa localStorage
2. Acessa http://localhost:3001
3. Vai para /login → ✅ Protegido
```


## 🔧 Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| Não vejo login | Limpe localStorage (F12) e recarregue |
| Login não funciona | Verifique backend em localhost:8000 |
| Redirecionado para /login | Sem token ou token inválido |
| Não consigo editar roles | Verifique se é admin |
| Role não muda | Verifique console (F12) para erros |
| Usuário vê dashboard errado | Faça logout/login novamente |


## 📊 Tabela Comparativa

| Antes | Depois |
|-------|--------|
| Dashboard direto | Tela de login obrigatória |
| Sem roles visuais | Roles gerenciáveis via UI |
| Sem redirecionamento | Redireciona por role |
| Sem proteção | Rotas protegidas |
| Sem tabela de usuários | Admin dashboard com tabela |
| Role apenas em BD | Role em localStorage + BD |


## 🎯 Status de Implementação

```
✅ Login page
✅ Autenticação JWT
✅ Armazenamento de role
✅ Redirecionamento por role
✅ ProtectedRoute com role
✅ Admin dashboard
✅ Operator dashboard
✅ Owner dashboard
✅ Gerenciar usuários
✅ Editar roles (admin)
✅ Proteção contra self-edit
✅ Validação no backend
✅ localStorage seguro
✅ Documentação completa
```


## 📚 Próximas Leituras

**Principiante:**
1. [COMECE_AQUI.md](./COMECE_AQUI.md)
2. Este documento (REFERENCIA_RAPIDA.md)

**Operador:**
1. [GUIA_RAPIDO_NOVO_SISTEMA.md](./GUIA_RAPIDO_NOVO_SISTEMA.md)
2. [NOVO_FLUXO_AUTENTICACAO_RBAC.md](./NOVO_FLUXO_AUTENTICACAO_RBAC.md#-gerenciamento-de-roles)

**Desenvolvedor:**
1. [ARQUIVOS_MODIFICADOS.md](./ARQUIVOS_MODIFICADOS.md)
2. [NOVO_FLUXO_AUTENTICACAO_RBAC.md](./NOVO_FLUXO_AUTENTICACAO_RBAC.md)
3. [CHECKLIST_FINAL.md](./CHECKLIST_FINAL.md)

**Procurando por:**
→ [INDICE_DOCUMENTACAO.md](./INDICE_DOCUMENTACAO.md)


## 🎨 Atalhos do Navegador

```
http://localhost:3001       Login / Dashboard
http://localhost:3001/admin Admin Dashboard
http://localhost:3001/operador Operator Dashboard
http://localhost:3001/owner Owner Dashboard
http://localhost:8000/docs  API Documentation (Swagger)
```


## 🚀 Comandos para Iniciar

```bash
# Backend
cd backend && python -m uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev

# Acessar
Abra: http://localhost:3001
```


═══════════════════════════════════════════════════════════════════════════════

Tudo que você precisa em uma página! 🎯

═══════════════════════════════════════════════════════════════════════════════
