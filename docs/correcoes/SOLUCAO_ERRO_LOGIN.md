# 🔧 Solução: Erro "Failed to fetch" no Login

## 🔍 Problema Identificado

O erro "Failed to fetch" ocorre quando o frontend não consegue conectar ao backend na URL `http://192.168.10.167:8000/api/auth/login`.

**DIAGNÓSTICO:** 
- ✅ Container Docker `gas_backend` está rodando
- ⚠️ **Container está com status "unhealthy"** - isso explica o problema!
- ❌ **Erro encontrado:** `ImportError: numpy.core.multiarray failed to import`
- ⚠️ Há também um processo uvicorn manual rodando na porta 8000 (pode estar causando conflito)

**CAUSA RAIZ:** Incompatibilidade entre numpy e opencv-python-headless no container Docker.

**SOLUÇÃO:** Atualizar dependências e reconstruir o container.

## ✅ Soluções Implementadas

### 1. Melhorias no Tratamento de Erros
- ✅ Mensagem de erro mais clara no frontend
- ✅ Diagnóstico automático do problema
- ✅ Sugestões de solução exibidas ao usuário

### 2. Verificações Realizadas
- ✅ Backend está rodando na porta 8000 (processo PID 1183076)
- ✅ Porta 8000 está escutando em 0.0.0.0
- ⚠️ **Problema:** Backend não está acessível externamente via IP 192.168.10.167

## 🛠️ Soluções Possíveis

### ⚠️ SOLUÇÃO IMEDIATA: Corrigir Backend Unhealthy

O container está marcado como "unhealthy". **Execute estes comandos:**

```bash
# 1. Verificar logs para entender o problema
docker logs gas_backend --tail 100

# 2. Parar processo manual que pode estar conflitando
pkill -f "uvicorn app.main:app.*8000"

# 3. Reiniciar o container
docker restart gas_backend

# 4. Aguardar alguns segundos e verificar status
sleep 10
docker ps | grep backend

# 5. Verificar se está respondendo
curl http://localhost:8000/health
curl http://192.168.10.167:8000/health

# 6. Se ainda estiver unhealthy, verificar healthcheck
docker inspect gas_backend | grep -A 10 Healthcheck
```

**SOLUÇÃO DEFINITIVA - Corrigir dependências e reconstruir:**

```bash
cd /home/daniel/gas-automation

# 1. Parar processo manual que pode estar conflitando
pkill -f "uvicorn app.main:app.*8000"

# 2. Reconstruir o container com as dependências atualizadas
docker-compose stop backend
docker-compose build --no-cache backend
docker-compose up -d backend

# 3. Verificar logs
docker logs gas_backend -f

# 4. Aguardar alguns segundos e testar
sleep 10
curl http://localhost:8000/health
curl http://192.168.10.167:8000/health
```

**Nota:** As dependências numpy e opencv-python-headless foram atualizadas no `requirements.txt` para corrigir a incompatibilidade.

### Opção 1: Verificar se o backend está realmente acessível

```bash
# Testar conexão local (deve funcionar após reiniciar)
curl http://localhost:8000/health

# Testar conexão externa
curl http://192.168.10.167:8000/health
```

### Opção 3: Usar Docker Compose (Recomendado)

```bash
cd /home/daniel/gas-automation
docker-compose up -d backend
```

### Opção 4: Verificar Firewall

```bash
# Verificar se o firewall está bloqueando a porta
sudo ufw status
sudo iptables -L -n | grep 8000

# Se necessário, liberar a porta
sudo ufw allow 8000/tcp
```

### Opção 5: Verificar se o backend está rodando no Docker

```bash
# Verificar containers
docker ps | grep backend

# Ver logs do backend
docker logs gas_backend

# Reiniciar o container
docker restart gas_backend
```

## 📝 Arquivos Modificados

1. **frontend/src/hooks/useAuth.jsx**
   - Melhor tratamento de erros de rede
   - Mensagem mais clara para "Failed to fetch"

2. **frontend/src/pages/Login.jsx**
   - Mensagem de erro melhorada
   - Sugestões de solução exibidas ao usuário

## 🔍 Diagnóstico Rápido

Execute estes comandos para diagnosticar:

```bash
# 1. Verificar se o processo está rodando
ps aux | grep uvicorn | grep 8000

# 2. Verificar se a porta está escutando
netstat -tlnp | grep 8000
# ou
ss -tlnp | grep 8000

# 3. Testar conexão local
curl http://localhost:8000/health

# 4. Testar conexão externa
curl http://192.168.10.167:8000/health

# 5. Verificar logs do backend
# Se estiver em Docker:
docker logs gas_backend --tail 50

# Se estiver rodando manualmente:
# Verificar onde os logs estão sendo escritos
```

## 🎯 SOLUÇÃO IMEDIATA

**O backend não está rodando!** Siga estes passos:

### 1. Iniciar o Backend

**Se estiver usando Docker:**
```bash
cd /home/daniel/gas-automation
docker-compose up -d backend
# Verificar logs
docker logs gas_backend --tail 50 -f
```

**Se estiver rodando manualmente:**
```bash
cd /home/daniel/gas-automation/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Verificar se o backend está respondendo

```bash
# Aguardar alguns segundos e testar
sleep 5
curl http://localhost:8000/health
curl http://192.168.10.167:8000/health
```

### 3. Testar login novamente

Após o backend estar rodando, tente fazer login novamente. A mensagem de erro agora deve ser mais clara se houver outros problemas.

### 4. Verificar logs se ainda houver problemas

```bash
# Docker
docker logs gas_backend --tail 100

# Manual - verificar onde os logs estão sendo escritos
# Geralmente no terminal onde o uvicorn foi iniciado
```

## 📞 Informações de Debug

- **URL do Backend:** http://192.168.10.167:8000
- **URL da API:** http://192.168.10.167:8000/api
- **Endpoint de Login:** POST /api/auth/login
- **Frontend Port:** 3001
- **Backend Port:** 8000

## ⚠️ Nota Importante

O erro "Failed to fetch" geralmente indica:
1. Backend não está rodando
2. Backend não está acessível na URL configurada
3. Problema de CORS (mas isso daria erro diferente)
4. Problema de firewall/rede

A solução mais comum é garantir que o backend esteja rodando e acessível na URL configurada no frontend.
