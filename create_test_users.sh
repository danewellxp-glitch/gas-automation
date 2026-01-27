#!/bin/bash
# Script para criar usuários de teste com diferentes roles

set -e

DB_HOST="localhost"
DB_PORT="5433"
DB_USER="gasadmin"
DB_PASSWORD="gasadmin123"
DB_NAME="gas_automation"

# Hashes de senhas (gerados com Python)
# Todos os hashes são da senha "Teste@123456"
PASSWORD_HASH='$argon2id$v=19$m=65536,t=3,p=4$8p4ghGnVRXPaFVXtYvqR1w$6r4RGzFIUIHdBN5p3DtkKFVNVvQ3H9T1LkWkJB5sI8A'

echo "Criando usuários de teste..."

# Usuário Admin (já existe, então vamos pular)
echo "✓ Admin já existe (admin@gasautomation.local)"

# Usuário Operator
echo "Criando Operator..."
docker exec gas_postgres psql -U "$DB_USER" -d "$DB_NAME" << EOF
INSERT INTO users (username, email, full_name, hashed_password, role, is_active, created_at, updated_at)
VALUES ('operador', 'operador@gasautomation.local', 'Operador Teste', '$PASSWORD_HASH', 'operator', true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;
EOF
echo "✓ Operator criado"

# Usuário Owner
echo "Criando Owner..."
docker exec gas_postgres psql -U "$DB_USER" -d "$DB_NAME" << EOF
INSERT INTO users (username, email, full_name, hashed_password, role, is_active, created_at, updated_at)
VALUES ('dono', 'dono@gasautomation.local', 'Dono Teste', '$PASSWORD_HASH', 'owner', true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;
EOF
echo "✓ Owner criado"

# Usuário User (role padrão)
echo "Criando User..."
docker exec gas_postgres psql -U "$DB_USER" -d "$DB_NAME" << EOF
INSERT INTO users (username, email, full_name, hashed_password, role, is_active, created_at, updated_at)
VALUES ('usuario', 'usuario@gasautomation.local', 'Usuário Teste', '$PASSWORD_HASH', 'user', true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;
EOF
echo "✓ User criado"

# Listar todos os usuários criados
echo ""
echo "==================================="
echo "Usuários criados com sucesso!"
echo "==================================="
echo ""

docker exec gas_postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT id, email, username, full_name, role, is_active FROM users ORDER BY id;
"

echo ""
echo "Credenciais de teste (todos com senha: Teste@123456):"
echo "  ✓ admin@gasautomation.local (Admin)"
echo "  ✓ operador@gasautomation.local (Operator)"
echo "  ✓ dono@gasautomation.local (Owner)"
echo "  ✓ usuario@gasautomation.local (User)"
echo ""
