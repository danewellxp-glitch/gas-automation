# 🧪 Guia Completo de Testes - Sistema de Roles

**Data:** 20 de janeiro de 2026  
**Versão:** 1.0.0

---

## 📊 Usuários de Teste Criados

| Email | Senha | Role | Dashboard | Descrição |
|-------|-------|------|-----------|-----------|
| admin@gasautomation.local | Teste@123456 | admin | `/admin` | Acesso total, gerencia usuários e roles |
| operador@gasautomation.local | Teste@123456 | operator | `/operador` | Gerencia conversas e pedidos |
| dono@gasautomation.local | Teste@123456 | owner | `/owner` | Visão executiva com estatísticas |
| usuario@gasautomation.local | Teste@123456 | user | `/operador` | Acesso básico (redireciona para operador) |

---

## ✅ Cenários de Teste

### 1. Teste de Autenticação Básica

#### 1.1 Login como Admin
- URL: http://192.168.10.156:3001
- Email: `admin@gasautomation.local`
- Senha: `Teste@123456`

**Esperado:**
- ✅ Login bem-sucedido
- ✅ Token salvo no localStorage
- ✅ Redirecionamento para `/admin`
- ✅ AdminDashboard carregado
- ✅ Usuário pode gerenciar roles

#### 1.2 Login como Operator
- Email: `operador@gasautomation.local`
- Senha: `Teste@123456`

**Esperado:**
- ✅ Login bem-sucedido
- ✅ Redirecionamento para `/operador`
- ✅ OperatorDashboard carregado
- ✅ Menu de operador disponível

#### 1.3 Login como Owner
- Email: `dono@gasautomation.local`
- Senha: `Teste@123456`

**Esperado:**
- ✅ Login bem-sucedido
- ✅ Redirecionamento para `/owner`
- ✅ OwnerDashboard carregado
- ✅ Estatísticas do negócio visíveis

#### 1.4 Login como User (role padrão)
- Email: `usuario@gasautomation.local`
- Senha: `Teste@123456`

**Esperado:**
- ✅ Login bem-sucedido
- ✅ Redirecionamento para `/operador` (fallback)
- ✅ OperatorDashboard carregado

---

### 2. Teste de Proteção de Rotas

#### 2.1 Tentar Acessar /admin sem ser admin
1. Login como operator
2. Tentar acessar http://192.168.10.156:3001/admin manualmente

**Esperado:**
- ✅ Redirecionado automaticamente para `/operador`

#### 2.2 Tentar Acessar Rota Protegida sem Token
1. Limpar localStorage: `localStorage.clear()`
2. Tentar acessar http://192.168.10.156:3001/dashboard

**Esperado:**
- ✅ Redirecionado para `/login`

---

### 3. Teste de Gerenciamento de Roles (AdminDashboard)

#### 3.1 Listar Usuários
1. Login como admin
2. Ir para `/admin`

**Esperado:**
- ✅ Tabela com todos os usuários carregada
- ✅ Roles exibidas com cores diferentes
- ✅ Status (Ativo/Inativo) visível

#### 3.2 Editar Role de um Usuário
1. Em `/admin`, clicar em "Editar" para operador@gasautomation.local
2. Selecionar nova role: "Owner"
3. Confirmar mudança

**Esperado:**
- ✅ Modal de confirmação aparece
- ✅ Mudança é aplicada no banco
- ✅ Tabela é atualizada automaticamente
- ✅ Mensagem de sucesso exibida

#### 3.3 Validação: Admin Não Pode Editar Sua Própria Role
1. Em `/admin`, procurar admin@gasautomation.local
2. Tentar clicar em "Editar"

**Esperado:**
- ✅ Botão está desabilitado (cinza)
- ✅ Tooltip: "Você não pode editar sua própria role"

#### 3.4 Validação: Role Inválida
1. Tentar enviar request diretamente para a API com role inválida
```bash
curl -X PUT http://192.168.10.156:8000/api/users/2/role \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "invalid_role"}'
```

**Esperado:**
- ✅ Erro 400: "Invalid role"

---

### 4. Teste de Endpoints da API

#### 4.1 GET /api/users (Listar Usuários)
```bash
curl -X GET http://192.168.10.156:8000/api/users \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Esperado:**
- ✅ Status 200
- ✅ Array de usuários retornado
- ✅ Cada usuário com campos: id, email, username, full_name, role, is_active

#### 4.2 GET /api/users/me (Dados do Usuário Atual)
```bash
curl -X GET http://192.168.10.156:8000/api/users/me \
  -H "Authorization: Bearer TOKEN"
```

**Esperado:**
- ✅ Status 200
- ✅ Dados do usuário autenticado

#### 4.3 GET /api/users/{id} (Detalhes Específicos)
```bash
curl -X GET http://192.168.10.156:8000/api/users/2 \
  -H "Authorization: Bearer TOKEN"
```

**Esperado:**
- ✅ Status 200
- ✅ Dados do usuário com id 2

#### 4.4 PUT /api/users/{id}/role (Atualizar Role)
```bash
curl -X PUT http://192.168.10.156:8000/api/users/2/role \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "owner"}'
```

**Esperado:**
- ✅ Status 200
- ✅ Mensagem de sucesso
- ✅ Dados do usuário com nova role

---

### 5. Teste de Segurança

#### 5.1 Acesso Não-Autorizado
```bash
# Operador tentando listar usuários
curl -X GET http://192.168.10.156:8000/api/users \
  -H "Authorization: Bearer OPERATOR_TOKEN"
```

**Esperado:**
- ✅ Status 403: "Only admins can list users"

#### 5.2 Token Expirado
1. Aguardar 31 minutos (token expire = 30 min)
2. Tentar fazer requisição

**Esperado:**
- ✅ Status 401: "Não foi possível validar as credenciais"

#### 5.3 Token Inválido
```bash
curl -X GET http://192.168.10.156:8000/api/users \
  -H "Authorization: Bearer INVALID_TOKEN"
```

**Esperado:**
- ✅ Status 401: "Não foi possível validar as credenciais"

---

### 6. Teste de UX/UI

#### 6.1 Feedback Visual de Carregamento
1. Login como admin
2. Ir para `/admin`

**Esperado:**
- ✅ Spinner animado enquanto carrega usuários
- ✅ Conteúdo carrega normalmente após

#### 6.2 Modal de Confirmação
1. Admin → Editar usuário
2. Selecionar nova role
3. Clicar "Próximo"

**Esperado:**
- ✅ Modal muda para tela de confirmação
- ✅ Mostra email e nova role selecionada
- ✅ Botões "Voltar" e "Confirmar"

#### 6.3 Cores de Role Diferentes
1. Em `/admin`, observar a tabela

**Esperado:**
- ✅ Admin: vermelho
- ✅ Operator: azul
- ✅ Owner: roxo
- ✅ User: cinza

#### 6.4 Logout e Limpeza de Estado
1. Login como qualquer usuário
2. Clicar em "Sair"

**Esperado:**
- ✅ Redirecionado para `/login`
- ✅ Token removido do localStorage
- ✅ User removido do localStorage
- ✅ Não consegue voltar ao dashboard anterior

---

## 🔍 Verificação de Endpoints

### Verificar Todos os Endpoints
```bash
# Backend Swagger
http://192.168.10.156:8000/docs
```

**Esperado:**
- ✅ Swagger UI carregando
- ✅ Todos os endpoints listados
- ✅ Possibilidade de testar endpoints

---

## 🐛 Possíveis Problemas e Soluções

### Problema: "Failed to fetch" ao entrar em um dashboard
**Causa:** URL da API pode estar incorreta
**Solução:** Verificar `VITE_API_URL` no docker-compose.yml

### Problema: Redirecionamento não funciona após login
**Causa:** Role não está sendo salva corretamente no localStorage
**Solução:** Verificar console do navegador (F12) para erros

### Problema: Não consegue editar role
**Causa:** Token expirado ou usuário não é admin
**Solução:** Fazer login novamente, verificar role do usuário

### Problema: Usuários novos não aparecem na lista
**Causa:** Cache do navegador
**Solução:** Fazer refresh da página (Ctrl+F5)

---

## 📋 Checklist Final de Testes

- [ ] Login com Admin funciona
- [ ] Login com Operator funciona
- [ ] Login com Owner funciona
- [ ] Login com User funciona
- [ ] Redirecionamento pós-login correto
- [ ] Proteção de rotas funciona
- [ ] AdminDashboard carrega usuários
- [ ] Edição de roles funciona
- [ ] Validação de role própria funciona
- [ ] Modal de confirmação funciona
- [ ] API retorna dados corretos
- [ ] Logout limpa estado
- [ ] Tokens são armazenados corretamente
- [ ] Mensagens de erro aparecem

---

## 🚀 Próximas Melhorias

- [ ] Adicionar paginação na lista de usuários
- [ ] Adicionar busca/filtro de usuários
- [ ] Implementar logs de auditoria para mudanças de role
- [ ] Adicionar histórico de alterações
- [ ] Implementar roles mais granulares (sub-roles)
- [ ] Dashboard de Admin com estatísticas
- [ ] Sincronização de role em tempo real (WebSocket)

---

**Status:** ✅ Sistema de Roles Implementado e Pronto para Testes
