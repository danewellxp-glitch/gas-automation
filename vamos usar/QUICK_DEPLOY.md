# 🚀 GUIA RÁPIDO DE DEPLOY - 192.168.10.156

## ⚡ Deploy Rápido (5 minutos)

### 1️⃣ No Servidor

```bash
# SSH no servidor
ssh user@192.168.10.156

# Clone o repositório
cd /opt
git clone <seu-repo> gas-automation
cd gas-automation

# Copie o arquivo .env.example
cp vamos\ usar/.env.example.server .env

# EDITE o arquivo .env com suas configurações
nano .env
```

### 2️⃣ Configure as Variáveis Críticas

Edite `.env` e altere:
- `DB_PASSWORD` → senha segura
- `JWT_SECRET` → string aleatória de 32+ caracteres
- `TWILIO_*` → suas credenciais (se usar WhatsApp)
- `MINIO_*` → suas credenciais (se usar S3)

### 3️⃣ Execute o Deploy

```bash
# Dar permissão ao script
chmod +x vamos\ usar/deploy.sh

# Executar
./vamos\ usar/deploy.sh
```

O script vai:
- ✅ Verificar Docker/Docker Compose
- ✅ Clonar/atualizar repositório
- ✅ Fazer build das imagens
- ✅ Iniciar todos os serviços
- ✅ Executar migrations
- ✅ Criar backup do banco
- ✅ Exibir URLs de acesso

---

## 📍 Acessar Serviços

| Serviço | URL | Credenciais |
|---------|-----|------------|
| Frontend | http://192.168.10.156:3000 | - |
| API | http://192.168.10.156:8000 | Token JWT |
| Grafana | http://192.168.10.156:3001 | admin/admin |
| Prometheus | http://192.168.10.156:9090 | - |
| MinIO | http://192.168.10.156:9001 | minioadmin/minioadmin123 |
| PostgreSQL | localhost:5432 | Seu DB_USER/DB_PASSWORD |

---

## 📊 Verificar Status

```bash
# Status geral
docker-compose -f vamos\ usar/docker-compose.production.yml ps

# Logs da API
docker-compose -f vamos\ usar/docker-compose.production.yml logs -f backend

# Logs específicos de um serviço
docker-compose -f vamos\ usar/docker-compose.production.yml logs -f postgres
docker-compose -f vamos\ usar/docker-compose.production.yml logs -f redis
```

---

## 🛠️ Comandos Úteis

```bash
# Parar todos os serviços
docker-compose -f vamos\ usar/docker-compose.production.yml down

# Reiniciar um serviço
docker-compose -f vamos\ usar/docker-compose.production.yml restart backend

# Executar migration manual
docker-compose -f vamos\ usar/docker-compose.production.yml exec backend \
    python -m alembic upgrade head

# Entrar no container da API
docker-compose -f vamos\ usar/docker-compose.production.yml exec backend bash

# Ver variáveis de ambiente do container
docker-compose -f vamos\ usar/docker-compose.production.yml exec backend env
```

---

## 🔄 Atualizar Código

```bash
cd /opt/gas-automation

# Pull do repositório
git pull origin main

# Rebuild e restart
docker-compose -f vamos\ usar/docker-compose.production.yml up -d --build backend
```

---

## 💾 Backup e Restore

```bash
# Fazer backup manual
docker-compose -f vamos\ usar/docker-compose.production.yml exec postgres \
    pg_dump -U gas_user gas_automation > backup.sql

# Restaurar de backup
docker-compose -f vamos\ usar/docker-compose.production.yml exec -T postgres \
    psql -U gas_user gas_automation < backup.sql
```

---

## ⚠️ Troubleshooting

### Erro: "Connection refused"
```bash
# Verificar se PostgreSQL está pronto
docker-compose -f vamos\ usar/docker-compose.production.yml exec postgres \
    pg_isready -U gas_user
```

### Erro: "Port already in use"
```bash
# Encontrar processo usando porta
lsof -i :8000
kill -9 <PID>
```

### API não inicia
```bash
# Ver logs detalhados
docker-compose -f vamos\ usar/docker-compose.production.yml logs backend

# Verificar variáveis de ambiente
docker-compose -f vamos\ usar/docker-compose.production.yml config
```

### Migrations falhando
```bash
# Criar nova migration
docker-compose -f vamos\ usar/docker-compose.production.yml exec backend \
    python -m alembic revision --autogenerate -m "descricao"

# Ver histórico
docker-compose -f vamos\ usar/docker-compose.production.yml exec backend \
    python -m alembic history
```

---

## 🔐 Segurança

- [ ] Alterar senha padrão do Grafana (admin/admin)
- [ ] Alterar credenciais padrão do MinIO
- [ ] Usar HTTPS em produção (configurar Nginx/Traefik)
- [ ] Configurar firewalls
- [ ] Fazer backups regularmente
- [ ] Monitorar logs

---

## 📞 Suporte

Detalhes completos: Ver arquivo `DOCKERFILE_README.md`

Documentação backend: `backend/README.md`

Documentação frontend: `frontend/README.md`
