#!/bin/bash
# Script de Desativação - Flow Engine V2

set -e

echo "🔙 Desativando Flow Engine V2..."
echo ""

# Verificar se existe backup
if [ -f backend/app/core/flow_config.py.backup ]; then
    echo "📦 Restaurando backup..."
    cp backend/app/core/flow_config.py.backup backend/app/core/flow_config.py
    rm backend/app/core/flow_config.py.backup
else
    echo "🔧 Desativando manualmente..."
    # Desativar V2
    sed -i 's/"flow_engine_v2_enabled": True/"flow_engine_v2_enabled": False/' backend/app/core/flow_config.py
    
    # Rollout para 0
    sed -i 's/ROLLOUT_PERCENTAGE = [0-9]\+/ROLLOUT_PERCENTAGE = 0/' backend/app/core/flow_config.py
fi

echo "✅ Configuração restaurada"
echo ""

# Reiniciar backend
echo "🔄 Reiniciando backend..."
docker-compose restart backend

echo ""
echo "⏳ Aguardando backend inicializar (10s)..."
sleep 10

echo ""
echo "✅ Flow Engine V2 DESATIVADO!"
echo ""
echo "📊 Status:"
echo "   - V2 Habilitado: NÃO"
echo "   - Sistema voltou para V1"
echo ""
echo "📱 Mensagens agora usarão o fluxo antigo (V1)"
