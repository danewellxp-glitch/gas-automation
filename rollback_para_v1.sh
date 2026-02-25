#!/bin/bash
# Script de Rollback V2 → V1
# Restaura versão V1 em caso de problemas

set -e

echo "🔙 ROLLBACK V2 → V1"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Encontrar backup mais recente
BACKUP_DIR=$(ls -td backend/app/core/v1_backup_* 2>/dev/null | head -1)

if [ -z "$BACKUP_DIR" ]; then
    echo "❌ Nenhum backup encontrado!"
    echo "   Não é possível fazer rollback."
    exit 1
fi

echo "📦 Backup encontrado: $BACKUP_DIR"
echo ""
read -p "Deseja restaurar V1 a partir deste backup? (s/N): " confirm

if [[ ! "$confirm" =~ ^[sS]$ ]]; then
    echo "❌ Rollback cancelado"
    exit 0
fi

echo ""
echo "🔄 Restaurando arquivos V1..."

# Restaurar arquivos
if [ -f "$BACKUP_DIR/flow_engine_v1.py" ]; then
    cp "$BACKUP_DIR/flow_engine_v1.py" backend/app/core/flow_engine.py
    echo "✅ flow_engine.py restaurado"
fi

if [ -f "$BACKUP_DIR/handlers_v1.py" ]; then
    cp "$BACKUP_DIR/handlers_v1.py" backend/app/core/handlers.py
    echo "✅ handlers.py restaurado"
fi

if [ -f "$BACKUP_DIR/state_machine_v1.py" ]; then
    cp "$BACKUP_DIR/state_machine_v1.py" backend/app/core/state_machine.py
    echo "✅ state_machine.py restaurado"
fi

echo ""
echo "🔧 Desabilitando V2..."

# Desabilitar V2
sed -i 's/"flow_engine_v2_enabled": True/"flow_engine_v2_enabled": False/' backend/app/core/flow_config.py
sed -i 's/ROLLOUT_PERCENTAGE = 100/ROLLOUT_PERCENTAGE = 0/' backend/app/core/flow_config.py

echo "✅ V2 desabilitado"

echo ""
echo "🔄 Reiniciando backend..."

docker-compose restart backend

echo ""
echo "⏳ Aguardando backend inicializar (15s)..."
sleep 15

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ROLLBACK COMPLETO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Status:"
echo "   ✅ V1 → Restaurado e ativo"
echo "   ✅ V2 → Desabilitado"
echo "   ✅ Sistema → Funcionando com V1"
echo ""
echo "📱 Sistema voltou ao normal (V1)"
echo ""
