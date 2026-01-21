# 🐳 Guia de Deploy - Dockerfile Atualizado

## Alterações Realizadas

### ✅ Removidas:
- ❌ Referências ao `localhost` (agora usa `0.0.0.0`)
- ❌ Cópias de arquivos Python antigos (main_eric.py, test_*.py, etc)
- ❌ Cópias desnecessárias de static/ e templates/
- ❌ Python 3.9 (atualizado para 3.11)

### ✅ Adicionadas:
- ✔️ Suporte a PostgreSQL (postgresql-client)
- ✔️ Alembic para migrations
- ✔️ Variáveis de ambiente para produção
- ✔️ Diretórios de logs
- ✔️ Arquivo .dockerignore para otimizar imagem

---

## 🚀 Como Usar

### Opção 1: Build Local (Desenvolvimento)

```bash
cd /home/daniel/gas-automation

# Build da imagem
docker build -f vamos\ usar/Dockerfile -t gas-automation-api:latest .

# Executar container
docker run -d \
  --name gas-api \
  -p 8000:8000 \
  --env-file .env \
  -e ENVIRONMENT=development \
  gas-automation-api:latest
```

### Opção 2: Usar docker-compose (Recomendado)

Adicione ao seu `docker-compose.yml`:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: vamos usar/Dockerfile
    container_name: gas_backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:pass@postgres:5432/gas_automation
      - JWT_SECRET=${JWT_SECRET}
      - LOG_LEVEL=info
    depends_on:
      - postgres
      - redis
    networks:
      - gas_network
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://0.0.0.0:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Opção 3: Deploy no Servidor 192.168.10.156

```bash
# 1. SSH no servidor
ssh user@192.168.10.156

# 2. Clone o repositório
git clone <seu-repo> /opt/gas-automation
cd /opt/gas-automation

# 3. Configure .env
cp .env.example .env
nano .env  # Edite com suas configurações

# 4. Build e execute
docker build -f vamos\ usar/Dockerfile -t gas-api:latest .
docker run -d \
  --name gas-api \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  gas-api:latest
```

---

## 📋 Checklist de Configuração

Antes de fazer deploy, certifique-se que:

- [ ] `.env` está configurado com valores corretos
- [ ] `requirements.txt` está na pasta `/backend`
- [ ] Pasta `app/` existe em `/backend`
- [ ] `alembic.ini` está em `/backend`
- [ ] Banco de dados PostgreSQL está acessível
- [ ] Redis está em funcionamento (se necessário)
- [ ] Portas 8000 estão abertas no firewall

---

## 🔍 Verificar Logs

```bash
# Ver logs do container
docker logs -f gas_backend

# Ou se estiver rodando diretamente
tail -f /app/logs/*.log
```

---

## ⚠️ Importante

1. **Não inclua arquivos antigos**: O `.dockerignore` já filtra main_eric.py e similares
2. **Ambiente**: Sempre defina `ENVIRONMENT=production` em produção
3. **JWT_SECRET**: Configure uma chave segura no `.env`
4. **Database**: Use PostgreSQL em produção, nunca SQLite
5. **Health Check**: Certifique-se que seu endpoint `/health` está implementado

---

## 🆘 Troubleshooting

### Erro: "Module 'backend' not found"
**Solução**: Mudou para `app.main:app` - Certifique-se que o arquivo existe em `backend/app/main.py`

### Erro: "Connection refused"
**Solução**: Verifique se PostgreSQL/Redis estão rodando e acessíveis

### Imagem muito grande
**Solução**: O `.dockerignore` ajuda, mas você pode limpar cache: `docker system prune`

---

## 📊 Estrutura Esperada

```
gas-automation/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── __init__.py
│   │   └── ...
│   ├── alembic/
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
├── vamos usar/
│   └── Dockerfile  ← Novo Dockerfile
└── docker-compose.yml
```

---

## 📞 Próximos Passos

1. Teste localmente com `docker build`
2. Verifique se a aplicação sobe com sucesso
3. Configure health check corretamente
4. Deploy em 192.168.10.156
