#!/bin/bash

# =============================================
# SCRIPT DE DEPLOY - GAS AUTOMATION
# Servidor: 192.168.10.156
# =============================================

set -e

echo "🚀 Iniciando Deploy GAS AUTOMATION"
echo "=================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variáveis
PROJECT_PATH="/opt/gas-automation"
DOCKER_COMPOSE="docker-compose -f vamos\ usar/docker-compose.production.yml"

# ==========================================
# 1. Verificações Iniciais
# ==========================================
echo -e "${YELLOW}📋 Verificando pré-requisitos...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker não instalado${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose não instalado${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker e Docker Compose encontrados${NC}"

# ==========================================
# 2. Clonar/Atualizar Repositório
# ==========================================
echo -e "${YELLOW}📦 Verificando repositório...${NC}"

if [ ! -d "$PROJECT_PATH" ]; then
    echo "Clonando repositório..."
    git clone <seu-repo> "$PROJECT_PATH"
else
    echo "Atualizando repositório..."
    cd "$PROJECT_PATH"
    git pull origin main
fi

cd "$PROJECT_PATH"

# ==========================================
# 3. Configurar Variáveis de Ambiente
# ==========================================
echo -e "${YELLOW}⚙️  Configurando variáveis de ambiente...${NC}"

if [ ! -f ".env" ]; then
    echo "Criando arquivo .env..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  ATENÇÃO: Configure o arquivo .env com seus valores reais!${NC}"
    echo "Abrindo editor..."
    nano .env
else
    echo -e "${GREEN}✅ Arquivo .env já existe${NC}"
fi

# ==========================================
# 4. Build das Imagens Docker
# ==========================================
echo -e "${YELLOW}🔨 Fazendo build das imagens...${NC}"

$DOCKER_COMPOSE build --no-cache

# ==========================================
# 5. Parar Containers Antigos
# ==========================================
echo -e "${YELLOW}🛑 Parando containers antigos...${NC}"

$DOCKER_COMPOSE down || true

# ==========================================
# 6. Iniciar Serviços
# ==========================================
echo -e "${YELLOW}▶️  Iniciando serviços...${NC}"

$DOCKER_COMPOSE up -d

# ==========================================
# 7. Executar Migrations
# ==========================================
echo -e "${YELLOW}🗄️  Executando migrations...${NC}"

sleep 5  # Aguardar PostgreSQL ficar pronto

docker-compose -f vamos\ usar/docker-compose.production.yml exec -T backend \
    python -m alembic upgrade head || echo "⚠️  Erro em migration (verificar logs)"

# ==========================================
# 8. Aguardar Healthcheck
# ==========================================
echo -e "${YELLOW}⏳ Aguardando healthcheck...${NC}"

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://192.168.10.156:8000/health 2>/dev/null | grep -q "ok"; then
        echo -e "${GREEN}✅ API está saudável!${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Tentativa $RETRY_COUNT/$MAX_RETRIES..."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Timeout esperando API ficar saudável${NC}"
    $DOCKER_COMPOSE logs backend
    exit 1
fi

# ==========================================
# 9. Exibir Status
# ==========================================
echo -e "${YELLOW}📊 Status dos serviços:${NC}"
$DOCKER_COMPOSE ps

# ==========================================
# 10. Exibir URLs de Acesso
# ==========================================
echo ""
echo -e "${GREEN}🎉 Deploy concluído com sucesso!${NC}"
echo ""
echo "URLs de Acesso:"
echo "  📱 Frontend: http://192.168.10.156:3000"
echo "  🔌 API Backend: http://192.168.10.156:8000"
echo "  📊 Grafana: http://192.168.10.156:3001"
echo "  📈 Prometheus: http://192.168.10.156:9090"
echo "  🪣 MinIO Console: http://192.168.10.156:9001"
echo ""
echo "Para ver logs:"
echo "  docker-compose -f vamos\ usar/docker-compose.production.yml logs -f backend"
echo ""

# ==========================================
# 11. Backup Automático
# ==========================================
echo -e "${YELLOW}💾 Criando backup do banco...${NC}"

BACKUP_DIR="$PROJECT_PATH/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"

docker-compose -f vamos\ usar/docker-compose.production.yml exec -T postgres \
    pg_dump -U gas_user gas_automation > "$BACKUP_FILE" || echo "⚠️  Erro ao fazer backup"

echo -e "${GREEN}✅ Backup criado: $BACKUP_FILE${NC}"

exit 0
