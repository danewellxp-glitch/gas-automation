#!/bin/bash
# Script de Ativação Rápida - Flow Engine V2
# Uso: ./ativar_v2.sh [rollout_percentage]

set -e

ROLLOUT=${1:-10}  # Default 10%

echo "🚀 Ativando Flow Engine V2..."
echo "📊 Rollout: ${ROLLOUT}%"
echo ""

# Verificar serviços
echo "🔍 Verificando serviços..."

# Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: OK"
else
    echo "❌ Redis: NÃO ESTÁ RODANDO"
    echo "   Execute: docker-compose up -d redis"
    exit 1
fi

# PostgreSQL
if docker-compose ps postgres | grep -q "Up"; then
    echo "✅ PostgreSQL: OK"
else
    echo "⚠️  PostgreSQL: Verificar manualmente"
fi

# Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama: OK"
else
    echo "⚠️  Ollama: NÃO ESTÁ RODANDO (NLU pode não funcionar)"
    echo "   Execute: ollama serve"
fi

echo ""
echo "🔧 Ativando V2..."

# Backup do arquivo original
cp backend/app/core/flow_config.py backend/app/core/flow_config.py.backup

# Ativar V2
sed -i 's/"flow_engine_v2_enabled": False/"flow_engine_v2_enabled": True/' backend/app/core/flow_config.py

# Definir rollout
sed -i "s/ROLLOUT_PERCENTAGE = 0/ROLLOUT_PERCENTAGE = ${ROLLOUT}/" backend/app/core/flow_config.py

echo "✅ Configuração atualizada"
echo ""

# Reiniciar backend
echo "🔄 Reiniciando backend..."
docker-compose restart backend

echo ""
echo "⏳ Aguardando backend inicializar (10s)..."
sleep 10

echo ""
echo "📋 Verificando logs..."
docker-compose logs --tail=20 backend | grep -E "(FlowEngineV2|HandlerRegistry|Redis)" || true

echo ""
echo "✅ Flow Engine V2 ATIVADO!"
echo ""
echo "📊 Status:"
echo "   - V2 Habilitado: SIM"
echo "   - Rollout: ${ROLLOUT}%"
echo "   - Backup: backend/app/core/flow_config.py.backup"
echo ""
echo "📱 Teste agora enviando uma mensagem no WhatsApp!"
echo ""
echo "🔙 Para desativar, execute: ./desativar_v2.sh"
