# 🔐 Guia de Autenticação - Gas Automation

## Usuários de Teste

### Usuário Admin (pré-criado)
```
Email: admin@gasautomation.local
Senha: Admin@123456
Role:  admin
```

---

## 📝 Como Criar Novos Usuários

### Opção 1: Via Script SQL

Execute o script abaixo no PostgreSQL:

```sql
-- 1. Gerar hash da senha usando Python primeiro:
-- docker exec gas_backend python -c "
-- from passlib.context import CryptContext
-- pwd = CryptContext(schemes=['argon2'], deprecated='auto')
-- print(pwd.hash('SuaSenha123'))
-- "

-- 2. Copie o hash gerado e execute:
INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
VALUES (
  'novo_usuario',
  'novo@gasautomation.local',
  'Novo Usuário',
  'COLE_O_HASH_AQUI',
  'operator',  -- ou 'admin', 'supervisor'
  true
);
```

### Opção 2: Via Script Python (Recomendado)

```bash
# 1. Criar o script (create_user_script.py):
cat > /tmp/create_new_user.py << 'SCRIPT'
import asyncio
from sqlmodel import Session
from app.database import engine
from app.models.auth_models import User
from app.auth import get_password_hash

username = "novo_usuario"
email = "novo@gasautomation.local"
full_name = "Novo Usuário"
password = "SuaSenha123"
role = "operator"  # ou 'admin', 'supervisor'

user = User(
    username=username,
    email=email,
    full_name=full_name,
    hashed_password=get_password_hash(password),
    role=role,
    is_active=True
)

with Session(engine) as session:
    session.add(user)
    session.commit()
    print(f"✅ Usuário {email} criado com sucesso!")
SCRIPT

# 2. Copie para o container e execute:
docker cp /tmp/create_new_user.py gas_backend:/app/
docker exec -w /app gas_backend python create_new_user.py
```

### Opção 3: Script Direto com psql

```bash
# 1. Gere o hash:
HASH=$(docker exec gas_backend python -c "
from passlib.context import CryptContext
pwd = CryptContext(schemes=['argon2'], deprecated='auto')
print(pwd.hash('SuaSenha123'))
")

# 2. Insira o usuário:
docker exec gas_postgres psql -U gasadmin -d gas_automation << EOF
INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
VALUES ('novo_usuario', 'novo@gasautomation.local', 'Novo Usuário', '$HASH', 'operator', true);
EOF
```

---

## 🔑 Roles Disponíveis

| Role | Permissões |
|------|-----------|
| `admin` | Acesso total ao sistema, gerenciamento de usuários |
| `supervisor` | Gerenciamento de operadores e pedidos |
| `operator` | Visualizar e processar pedidos |
| `user` | Acesso limitado (padrão) |

---

## 🧪 Teste de Login

### Via cURL

```bash
curl -X POST http://192.168.10.156:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@gasautomation.local",
    "password": "Admin@123456"
  }'
```

Resposta esperada:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "admin",
  "email": "admin@gasautomation.local"
}
```

---

## 🔗 Endpoints de Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/login` | Login com email e senha |
| POST | `/api/auth/register` | Registrar novo usuário |
| GET | `/api/auth/me` | Obter dados do usuário atual |

---

## ⚠️ Segurança

### Requisitos de Senha
- Mínimo 8 caracteres
- Deve conter: maiúscula, minúscula, número e caractere especial

### Hash de Senha
- Algoritmo: Argon2
- Nunca armazene senhas em texto plano
- Use sempre `get_password_hash()` antes de armazenar

---

## 📚 Referência

- **Tabela**: `users`
- **Campos principais**: `username`, `email`, `hashed_password`, `role`, `is_active`
- **Chaves únicas**: `username`, `email`
- **Índices**: username, email

---

**Última atualização:** 20 de janeiro de 2026
