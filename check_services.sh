#!/bin/bash

echo "=========================================="
echo "VERIFICAÇÃO DE SERVIÇOS - GAS AUTOMATION"
echo "=========================================="
echo ""

echo "🔍 Status dos Containers Docker:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd /home/daniel/gas-automation
docker-compose ps | grep -E "CONTAINER|backend|frontend|postgres|redis|waha"
echo ""

echo "🌐 Teste de Conectividade:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Backend
echo "✓ Backend (localhost:8000):"
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "  ✅ RODANDO"
else
    echo "  ❌ NÃO RESPONDENDO"
fi

# Frontend
echo "✓ Frontend (localhost:3001):"
if curl -s http://localhost:3001 > /dev/null 2>&1; then
    echo "  ✅ RODANDO"
else
    echo "  ❌ NÃO RESPONDENDO"
fi

# WAHA WhatsApp
echo "✓ WhatsApp API (localhost:3000):"
if curl -s http://localhost:3000/health > /dev/null 2>&1; then
    echo "  ✅ RODANDO"
else
    echo "  ❌ NÃO RESPONDENDO"
fi

# Redis
echo "✓ Redis (localhost:6379):"
if docker exec gas_redis redis-cli ping > /dev/null 2>&1; then
    echo "  ✅ RODANDO"
else
    echo "  ❌ NÃO RESPONDENDO"
fi

# PostgreSQL
echo "✓ PostgreSQL (localhost:5433):"
if docker exec gas_postgres psql -U gasadmin -d gas_automation -c "SELECT 1" > /dev/null 2>&1; then
    echo "  ✅ RODANDO"
else
    echo "  ❌ NÃO RESPONDENDO"
fi

# Ollama
echo "✓ Ollama (localhost:11434):"
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "  ✅ RODANDO"
else
    echo "  ❌ NÃO RESPONDENDO"
fi

echo ""
echo "📍 Acessar os Serviços:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔗 API Backend:      http://192.168.10.167:8000"
echo "🔗 API Docs:         http://192.168.10.167:8000/docs"
echo "🔗 Frontend Web:     http://192.168.10.167:3001"
echo "🔗 WhatsApp API:     http://192.168.10.167:3000"
echo "🔗 Redis Commander:  http://192.168.10.167:8081"
echo "🔗 Grafana:          http://192.168.10.167:3002"
echo "🔗 Prometheus:       http://192.168.10.167:9090"
echo "🔗 MinIO:            http://192.168.10.167:9000"
echo "🔗 Ollama:           http://192.168.10.167:11434"
echo ""
