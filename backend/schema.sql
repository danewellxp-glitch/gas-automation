-- ============================================================================
-- GAS AUTOMATION - SCHEMA COMPLETO DO POSTGRESQL
-- Atualizado em: 2026-01-22
-- ============================================================================
-- Este arquivo contém todas as tabelas do sistema.
-- Executar na ordem para respeitar as foreign keys.
-- ============================================================================

-- Extensão para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- SEQUÊNCIAS
-- ============================================================================

-- Sequência para número do pedido
CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1000;

-- ============================================================================
-- TABELAS DE AUTENTICAÇÃO E CHAT (SQLModel - ID INTEGER)
-- ============================================================================

-- Usuários do sistema (admin, operador, driver)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    hashed_password VARCHAR(500) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- Conversas do WhatsApp
CREATE TABLE IF NOT EXISTS conversation (
    id SERIAL PRIMARY KEY,
    customer_number VARCHAR(20) NOT NULL,
    name VARCHAR(200),
    assigned_to INTEGER REFERENCES users(id),
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending'
);

-- Mensagens das conversas
CREATE TABLE IF NOT EXISTS message (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id),
    sender VARCHAR(50) NOT NULL,
    message_type VARCHAR(50) DEFAULT 'customer',
    content TEXT NOT NULL,
    bot_service VARCHAR(50),
    n8n_workflow_id VARCHAR(100),
    n8n_execution_id VARCHAR(100),
    n8n_processed BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Logs de auditoria (sistema antigo)
CREATE TABLE IF NOT EXISTS auditlog (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    conversation_id INTEGER REFERENCES conversation(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

-- Interações com o chatbot
CREATE TABLE IF NOT EXISTS botinteraction (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    customer_name VARCHAR(200),
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    bot_type VARCHAR(50) DEFAULT 'enhanced',
    escalated BOOLEAN DEFAULT FALSE,
    escalation_reason VARCHAR(500),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INTEGER
);

-- Contexto do chatbot por cliente
CREATE TABLE IF NOT EXISTS botcontext (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    conversation_stage VARCHAR(50) DEFAULT 'greeting',
    user_intent VARCHAR(100),
    collected_info TEXT,
    bot_responses_count INTEGER DEFAULT 0,
    escalation_requested BOOLEAN DEFAULT FALSE,
    escalation_reason VARCHAR(500),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '2 hours')
);

-- ============================================================================
-- TABELAS PRINCIPAIS DO NEGÓCIO (BaseModel - ID UUID)
-- ============================================================================

-- Clientes
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Identificadores externos
    firebird_id INTEGER UNIQUE,
    asaas_customer_id VARCHAR(50) UNIQUE,

    -- Dados básicos
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200),
    email VARCHAR(255),
    cpf_cnpj VARCHAR(20),

    -- Endereço (JSON)
    address JSONB,

    -- Observações
    notes TEXT
);

CREATE INDEX IF NOT EXISTS ix_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS ix_customers_phone_name ON customers(phone, name);
CREATE INDEX IF NOT EXISTS ix_customers_cpf_cnpj ON customers(cpf_cnpj);

-- Produtos (Botijões de Gás)
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Identificação
    code VARCHAR(10) UNIQUE NOT NULL,
    firebird_code VARCHAR(50) UNIQUE,

    -- Dados do produto
    name VARCHAR(100) NOT NULL,
    description TEXT,
    weight_kg NUMERIC(5,2) NOT NULL,

    -- Preço
    price NUMERIC(10,2) NOT NULL,

    -- Status
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_products_code ON products(code);
CREATE INDEX IF NOT EXISTS ix_products_active ON products(is_active, code);

-- Pedidos
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Relacionamento
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,

    -- Identificação
    order_number INTEGER UNIQUE NOT NULL DEFAULT nextval('order_number_seq'),

    -- Status
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,

    -- Pagamento
    payment_method VARCHAR(50),
    asaas_payment_id VARCHAR(100),

    -- Valores
    total_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00,

    -- Endereço de entrega (snapshot)
    delivery_address JSONB,
    delivery_bairro VARCHAR(100),

    -- Observações
    notes TEXT,

    -- Timestamps específicos
    paid_at TIMESTAMP WITH TIME ZONE,
    dispatched_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancellation_reason VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS ix_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS ix_orders_asaas_payment_id ON orders(asaas_payment_id);
CREATE INDEX IF NOT EXISTS ix_orders_status_created ON orders(status, created_at);
CREATE INDEX IF NOT EXISTS ix_orders_customer_status ON orders(customer_id, status);
CREATE INDEX IF NOT EXISTS ix_orders_bairro_status ON orders(delivery_bairro, status);

-- Itens do Pedido
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Relacionamento
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,

    -- Dados do produto (snapshot)
    product_code VARCHAR(10) NOT NULL,
    product_name VARCHAR(100) NOT NULL,

    -- Quantidade e valores
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(10,2) NOT NULL,
    subtotal NUMERIC(10,2) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items(order_id);

-- Pagamentos
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Relacionamento
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,

    -- Identificação Asaas
    asaas_payment_id VARCHAR(100) UNIQUE,
    asaas_customer_id VARCHAR(100),

    -- Método e status
    method VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,

    -- Valores
    amount NUMERIC(10,2) NOT NULL,
    net_amount NUMERIC(10,2),
    fee NUMERIC(10,2),

    -- Dados Pix
    pix_qr_code TEXT,
    pix_copy_paste TEXT,
    pix_expiration TIMESTAMP WITH TIME ZONE,

    -- Dados Boleto
    boleto_url VARCHAR(500),
    boleto_barcode VARCHAR(100),
    boleto_digitable_line VARCHAR(100),

    -- Dados Cartão
    card_last_digits VARCHAR(4),
    card_brand VARCHAR(20),

    -- Datas
    due_date TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,

    -- Metadados
    gateway_response JSONB
);

CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS ix_payments_asaas_payment_id ON payments(asaas_payment_id);
CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS ix_payments_status_method ON payments(status, method);
CREATE INDEX IF NOT EXISTS ix_payments_order_status ON payments(order_id, status);

-- Entregadores (Drivers)
CREATE TABLE IF NOT EXISTS drivers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Identificadores
    firebird_id INTEGER UNIQUE,
    user_id INTEGER UNIQUE REFERENCES users(id),

    -- Dados básicos
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255),
    cpf VARCHAR(14),
    cnh VARCHAR(20),

    -- Status
    status VARCHAR(20) DEFAULT 'offline' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    -- Localização
    current_location JSONB,
    last_location_update TIMESTAMP WITH TIME ZONE,

    -- Bairros atendidos
    assigned_bairros JSONB DEFAULT '[]',

    -- Veículo
    vehicle_plate VARCHAR(10),
    vehicle_model VARCHAR(50),

    -- Estatísticas
    total_deliveries INTEGER DEFAULT 0,
    rating NUMERIC(3,2) DEFAULT 5.00
);

CREATE INDEX IF NOT EXISTS ix_drivers_phone ON drivers(phone);
CREATE INDEX IF NOT EXISTS ix_drivers_status ON drivers(status);
CREATE INDEX IF NOT EXISTS ix_drivers_user_id ON drivers(user_id);
CREATE INDEX IF NOT EXISTS ix_drivers_active_status ON drivers(is_active, status);

-- Entregas
CREATE TABLE IF NOT EXISTS deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Relacionamentos
    order_id UUID UNIQUE NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    driver_id UUID REFERENCES drivers(id),

    -- Entregador (simplificado)
    driver_name VARCHAR(100),
    driver_phone VARCHAR(20),

    -- Status
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,

    -- Localização
    bairro VARCHAR(100),

    -- Tempos
    estimated_minutes INTEGER DEFAULT 40,
    actual_delivery_minutes INTEGER,

    -- Timestamps de cada etapa
    assigned_at TIMESTAMP WITH TIME ZONE,
    picked_up_at TIMESTAMP WITH TIME ZONE,
    in_transit_at TIMESTAMP WITH TIME ZONE,
    arrived_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,

    -- Observações
    notes TEXT,
    failure_reason VARCHAR(500),

    -- GPS
    last_location JSONB
);

CREATE INDEX IF NOT EXISTS ix_deliveries_order_id ON deliveries(order_id);
CREATE INDEX IF NOT EXISTS ix_deliveries_driver_id ON deliveries(driver_id);
CREATE INDEX IF NOT EXISTS ix_deliveries_status ON deliveries(status);
CREATE INDEX IF NOT EXISTS ix_deliveries_bairro ON deliveries(bairro);
CREATE INDEX IF NOT EXISTS ix_deliveries_status_bairro ON deliveries(status, bairro);
CREATE INDEX IF NOT EXISTS ix_deliveries_driver_status ON deliveries(driver_id, status);

-- Log de tempo dos entregadores
CREATE TABLE IF NOT EXISTS driver_time_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Relacionamento
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,

    -- Status do período
    status VARCHAR(20) NOT NULL,

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,

    -- Duração
    duration_minutes INTEGER,

    -- Data (para queries)
    date DATE NOT NULL,

    -- Metadados
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS ix_driver_time_logs_driver_id ON driver_time_logs(driver_id);
CREATE INDEX IF NOT EXISTS ix_driver_time_logs_date ON driver_time_logs(date);

-- Log de eventos (auditoria)
CREATE TABLE IF NOT EXISTS event_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Tipo do evento
    event_type VARCHAR(100) NOT NULL,

    -- Entidade relacionada
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,

    -- Ator
    actor_type VARCHAR(50) DEFAULT 'system' NOT NULL,
    actor_id VARCHAR(100),

    -- Dados
    payload JSONB,

    -- Metadados
    ip_address VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS ix_event_logs_event_type ON event_logs(event_type);
CREATE INDEX IF NOT EXISTS ix_event_logs_entity_type ON event_logs(entity_type);
CREATE INDEX IF NOT EXISTS ix_event_logs_entity_id ON event_logs(entity_id);
CREATE INDEX IF NOT EXISTS ix_event_logs_created_at ON event_logs(created_at);
CREATE INDEX IF NOT EXISTS ix_event_logs_type_entity ON event_logs(event_type, entity_type);
CREATE INDEX IF NOT EXISTS ix_event_logs_entity_created ON event_logs(entity_type, entity_id, created_at);

-- ============================================================================
-- TABELAS DE CARGA DO VEÍCULO (Novo - 2026-01-22)
-- ============================================================================

-- Carga do veículo
CREATE TABLE IF NOT EXISTS cargas_veiculo (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Relacionamento
    driver_id UUID NOT NULL REFERENCES drivers(id),

    -- Datas
    data_saida TIMESTAMP WITH TIME ZONE,
    data_retorno TIMESTAMP WITH TIME ZONE,

    -- Status: criada, em_rota, finalizada
    status VARCHAR(20) DEFAULT 'criada' NOT NULL,

    -- Observações
    observacoes VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS ix_cargas_driver_id ON cargas_veiculo(driver_id);
CREATE INDEX IF NOT EXISTS ix_cargas_status ON cargas_veiculo(status);
CREATE INDEX IF NOT EXISTS ix_cargas_driver_status ON cargas_veiculo(driver_id, status);
CREATE INDEX IF NOT EXISTS ix_cargas_data_saida ON cargas_veiculo(data_saida);

-- Itens da carga
CREATE TABLE IF NOT EXISTS carga_itens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Relacionamentos
    carga_id UUID NOT NULL REFERENCES cargas_veiculo(id) ON DELETE CASCADE,
    produto_id UUID NOT NULL REFERENCES products(id),

    -- Quantidades
    qtd_saida INTEGER DEFAULT 0 NOT NULL,
    qtd_retorno_cheio INTEGER DEFAULT 0 NOT NULL,
    qtd_retorno_vazio INTEGER DEFAULT 0 NOT NULL,
    qtd_vendida INTEGER DEFAULT 0 NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_carga_itens_carga_id ON carga_itens(carga_id);
CREATE INDEX IF NOT EXISTS ix_carga_itens_produto_id ON carga_itens(produto_id);
CREATE INDEX IF NOT EXISTS ix_carga_itens_carga_produto ON carga_itens(carga_id, produto_id);

-- ============================================================================
-- DADOS INICIAIS
-- ============================================================================

-- Usuário admin padrão (senha: Admin@123456)
INSERT INTO users (username, email, full_name, hashed_password, role, is_active)
VALUES (
    'admin',
    'admin@gasautomation.local',
    'Administrador',
    '$argon2id$v=19$m=65536,t=3,p=4$8YA8RQsrP0ssjXvF8lj6OA$DGWMJ3IrpXNfQH8SQbKsVvAH7w7KhKBXFp8X0j/aOkA',
    'admin',
    true
)
ON CONFLICT (email) DO NOTHING;

-- Produtos padrão (botijões de gás)
INSERT INTO products (code, name, weight_kg, price, is_active)
VALUES
    ('P13', 'Botijão P13 - 13kg', 13.00, 120.00, true),
    ('P20', 'Botijão P20 - 20kg', 20.00, 180.00, true),
    ('P45', 'Botijão P45 - 45kg', 45.00, 400.00, true)
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

SELECT 'Schema criado com sucesso!' AS status;
SELECT COUNT(*) AS total_tabelas FROM information_schema.tables WHERE table_schema = 'public';
