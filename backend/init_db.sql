-- Script para criar as tabelas do Gas Automation
-- Hash da senha: Admin@123456 (argon2)

-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    full_name VARCHAR NOT NULL,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Tabela de Conversas
CREATE TABLE IF NOT EXISTS conversation (
    id SERIAL PRIMARY KEY,
    customer_number VARCHAR NOT NULL,
    name VARCHAR,
    assigned_to INTEGER REFERENCES users(id),
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR DEFAULT 'pending'
);

-- Tabela de Mensagens
CREATE TABLE IF NOT EXISTS message (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id),
    sender VARCHAR NOT NULL,
    message_type VARCHAR DEFAULT 'customer',
    content TEXT NOT NULL,
    bot_service VARCHAR,
    n8n_workflow_id VARCHAR,
    n8n_execution_id VARCHAR,
    n8n_processed BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Logs de Auditoria
CREATE TABLE IF NOT EXISTS auditlog (
    id SERIAL PRIMARY KEY,
    action VARCHAR NOT NULL,
    user_id INTEGER REFERENCES users(id),
    conversation_id INTEGER REFERENCES conversation(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- Tabela de Interações Bot
CREATE TABLE IF NOT EXISTS botinteraction (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR NOT NULL,
    customer_name VARCHAR,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    bot_type VARCHAR DEFAULT 'enhanced',
    escalated BOOLEAN DEFAULT FALSE,
    escalation_reason VARCHAR,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER
);

-- Tabela de Contexto Bot
CREATE TABLE IF NOT EXISTS botcontext (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR UNIQUE NOT NULL,
    conversation_stage VARCHAR DEFAULT 'greeting',
    user_intent VARCHAR,
    collected_info TEXT,
    bot_responses_count INTEGER DEFAULT 0,
    escalation_requested BOOLEAN DEFAULT FALSE,
    escalation_reason VARCHAR,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '2 hours'
);

-- Inserir usuário admin de teste
INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
VALUES ('admin', 'admin@gasautomation.local', 'Admin Test', '$argon2id$v=19$m=65536,t=3,p=4$8YA8RQsrP0ssjXvF8lj6OA$DGWMJ3IrpXNfQH8SQbKsVvAH7w7KhKBXFp8X0j/aOkA', 'admin', true)
ON CONFLICT (email) DO NOTHING;

-- Verificar criação
SELECT 'Tabelas criadas com sucesso!' AS status;
SELECT COUNT(*) as total_users FROM users;
