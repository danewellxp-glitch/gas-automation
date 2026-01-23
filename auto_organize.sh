#!/bin/bash
# Script de automação para organizar documentos
# Pode ser executado manualmente ou via cron/watch

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Executando organização automática de documentos..."
python3 organize_docs.py
