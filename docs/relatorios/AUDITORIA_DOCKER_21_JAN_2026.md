# 🔍 AUDITORIA DOCKER - 21 JAN 2026

## 📋 RESUMO EXECUTIVO

**Data:** 21 de Janeiro de 2026, 17:26  
**Motivo:** Alterações não documentadas feitas por terceiros hoje de manhã  
**Status:** ⚠️ **PROBLEMAS CRÍTICOS ENCONTRADOS**

---

## 🔴 PROBLEMAS CRÍTICOS

### 1. **CORS Wildcards no Traefik** ⚠️ **ALTA SEVERIDADE**
```yaml
# docker-compose.yml:210
traefik.http.middlewares.backend-cors.headers.accesscontrolalloworiginlist: '*'
```

**Problema:** Permite acesso de QUALQUER origem, violando segurança CORS  
**Impacto:** Vulnerabilidade de segurança - qualquer site pode fazer requisições  
**Recomendação:**
```yaml
traefik.http.middlewares.backend-cors.headers.accesscontrolalloworiginlist: 'http://192.168.10.167:3001'
```

---

### 2. **Variáveis de Ambiente Faltando** ⚠️ **MÉDIA SEVERIDADE**

**Warnings encontrados:**
```
WAHA_DASHBOARD_USERNAME - não definida (vazia)
WAHA_DASHBOARD_PASSWORD - não definida (vazia)
WHATSAPP_SWAGGER_USERNAME - não definida (vazia)
WHATSAPP_SWAGGER_PASSWORD - não definida (vazia)
ASAAS_API_KEY - não definida (vazia)
```

**Impacto:**
- WAHA sem autenticação (dashboard público)
- Swagger sem proteção
- Integração Asaas não funcional

**Solução:** Adicionar ao `.env`:
```bash
WAHA_DASHBOARD_USERNAME=admin
WAHA_DASHBOARD_PASSWORD=senha_forte_aqui
WHATSAPP_SWAGGER_USERNAME=admin
WHATSAPP_SWAGGER_PASSWORD=senha_forte_aqui
ASAAS_API_KEY=sua_chave_asaas_aqui
```

---

### 3. **Traefik API Insegura** ⚠️ **ALTA SEVERIDADE**
```yaml
# docker-compose.yml:11
- "--api.insecure=true"
```

**Problema:** Dashboard do Traefik exposto sem autenticação na porta 8080  
**Impacto:** Qualquer pessoa pode acessar `http://192.168.10.167:8080` e ver configurações  
**Recomendação:** Mudar para `false` e configurar autenticação

---

## ⚠️ PROBLEMAS MÉDIOS

### 4. **Frontend sem Health Check**
```yaml
frontend:
  # ... sem healthcheck definido
```

**Impacto:** Docker não sabe se frontend está realmente funcionando  
**Recomendação:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3001/"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

### 5. **Backend sem Health Check**
```yaml
backend:
  # ... sem healthcheck definido
```

**Impacto:** Outros serviços dependem do backend mas não sabem se está healthy  
**Recomendação:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 5s
  retries: 5
```

---

### 6. **Volumes Bind Mount em Produção**
```yaml
backend:
  volumes:
    - ./backend:/app  # ⚠️ Bind mount

frontend:
  volumes:
    - ./frontend:/app  # ⚠️ Bind mount
```

**Problema:** Modo desenvolvimento em produção  
**Impacto:** Performance ruim, arquivos do host podem afetar container  
**Recomendação:** Remover volumes bind em produção, usar apenas imagens

---

## ✅ COISAS CORRETAS

1. ✅ Health checks no PostgreSQL
2. ✅ Health checks no Redis
3. ✅ Health checks no MinIO
4. ✅ Restart policies configurados (`unless-stopped`)
5. ✅ Depends_on com conditions corretos
6. ✅ Network isolada (`gas_network`)
7. ✅ Secrets keys no `.env` (não hardcoded)

---

## 🔧 AÇÕES RECOMENDADAS

### **URGENTE (Fazer agora):**
1. ⚠️ Remover CORS wildcard do Traefik
2. ⚠️ Desabilitar API insegura do Traefik
3. ⚠️ Adicionar credenciais WAHA ao `.env`

### **IMPORTANTE (Fazer hoje):**
4. 🔧 Adicionar health checks no backend
5. 🔧 Adicionar health checks no frontend
6. 🔧 Configurar ASAAS_API_KEY se for usar

### **MELHORIAS (Próxima semana):**
7. 📝 Documentar alterações no git
8. 📝 Remover bind mounts em produção
9. 📝 Implementar secrets do Docker Compose

---

## 📊 ESTATÍSTICAS

```
Total de Serviços: 15
Containers Ativos: 15
Com Health Check: 5/15 (33%)
Problemas Críticos: 3
Problemas Médios: 3
Status Geral: ⚠️ NECESSITA ATENÇÃO
```

---

## 🔍 ALTERAÇÕES DETECTADAS HOJE

**Arquivo:** `docker-compose.yml`  
**Alteração:** VITE_WS_URL corrigida  
```diff
- VITE_WS_URL: ws://192.168.10.167:8000/ws
+ VITE_WS_URL: ws://192.168.10.167:8000
```
**Status:** ✅ Correção válida (corrige duplicação /ws/ws/)

---

## 📝 RECOMENDAÇÕES FINAIS

1. **Pedir ao primo para documentar alterações futuras**
2. **Criar checklist de segurança antes de alterações**
3. **Usar git para rastrear mudanças**
4. **Implementar CI/CD com validação automática**

---

**Auditoria realizada por:** Claude (Cursor AI)  
**Data:** 21/01/2026 17:26 BRT
