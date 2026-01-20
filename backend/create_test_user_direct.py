#!/usr/bin/env python3
"""
Script para criar usuário de teste via SQL direto no PostgreSQL
"""

import subprocess
import sys

# Credenciais do banco
DB_HOST = "postgres"
DB_PORT = "5432"
DB_USER = "gasadmin"
DB_PASSWORD = "gasadmin123"
DB_NAME = "gas_automation"

# Hash da senha "Admin@123456" gerado com argon2
# A senha será hasheada quando inserida
PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$8YA8RQsrP0ssjXvF8lj6OA$DGWMJ3IrpXNfQH8SQbKsVvAH7w7KhKBXFp8X0j/aOkA"

# SQL para criar o usuário
sql_commands = [
    # Criar usuário de teste
    f"""
    INSERT INTO users (username, email, full_name, hashed_password, role, is_active, created_at, updated_at)
    VALUES ('admin', 'admin@gasautomation.local', 'Admin Test', '{PASSWORD_HASH}', 'admin', true, NOW(), NOW())
    ON CONFLICT (email) DO NOTHING;
    """
]

# Executar as queries via psql
for sql_cmd in sql_commands:
    try:
        result = subprocess.run(
            ["psql", "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, "-d", DB_NAME, "-c", sql_cmd],
            env={"PGPASSWORD": DB_PASSWORD},
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Usuário criado com sucesso!")
            print(f"   Email: admin@gasautomation.local")
            print(f"   Senha: Admin@123456")
            print(f"   Role: admin")
        else:
            print(f"❌ Erro ao criar usuário:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)
