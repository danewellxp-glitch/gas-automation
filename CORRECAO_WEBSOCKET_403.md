# ✅ Correção - WebSocket 403 (Unauthorized)

## 🐛 Problema Identificado

**Erro no Console:**
```
WebSocket connection to 'ws://192.168.10.156:8000/ws/dashboard?token=...' failed
WebSocket fechado: 1006
```

**Logs do Backend:**
```
INFO: WebSocket /dashboard?token=... 403
```

## 🔍 Causa

O WebSocket está retornando **403 Unauthorized** porque:

1. **Token pode estar expirado** - Tokens JWT têm expiração (15 minutos por padrão)
2. **Token inválido** - Token pode estar corrompido ou não ser válido
3. **Usuário inativo** - Usuário pode estar marcado como `is_active = False`

## ✅ Correções Aplicadas

1. ✅ **Validação de token antes de conectar**
   - Se não houver token, não tenta conectar
   - Evita tentativas desnecessárias

2. ✅ **URL corrigida**
   - Endpoint correto: `/ws/dashboard`
   - Token passado como query parameter

3. ✅ **Logs melhorados**
   - Token oculto nos logs para segurança

## 🔧 Solução para Token Expirado

O problema de 403 geralmente é causado por token expirado. O sistema deve:

1. **Renovar token automaticamente** quando expirar
2. **Fazer logout** se token não puder ser renovado
3. **Tentar reconectar** após novo login

### Próximos Passos (Opcional):

1. Implementar renovação automática de token
2. Adicionar handler para erro 403 que força novo login
3. Melhorar feedback visual quando WebSocket não conecta

## 📋 Status

- ✅ URL do WebSocket corrigida
- ✅ Validação de token adicionada
- ⚠️ Token expirado precisa ser tratado (renovação automática)

**Nota:** O erro 403 é esperado se o token estiver expirado. O usuário precisa fazer login novamente para obter um novo token.
