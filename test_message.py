#!/usr/bin/env python3
"""
Script para testar envio de mensagem via webhook.
Simula uma mensagem chegando do WhatsApp.
"""

import requests
import json
from datetime import datetime

# URL do webhook
WEBHOOK_URL = "http://localhost:8000/webhooks/waha"

# Dados da mensagem simulada (formato WAHA)
payload = {
    "event": "message",
    "instanceId": "test_instance",
    "data": {
        "key": {
            "remoteJid": "5585987654321@s.whatsapp.net",
            "fromMe": False,
            "id": f"test_{datetime.now().timestamp()}"
        },
        "message": {
            "conversation": "Oi, essa é uma mensagem de teste!"
        },
        "messageTimestamp": int(datetime.now().timestamp())
    }
}

print(f"📤 Enviando mensagem de teste para {WEBHOOK_URL}")
print(f"📱 Telefone: 5585987654321")
print(f"💬 Mensagem: {payload['data']['message']['conversation']}")
print()

try:
    response = requests.post(
        WEBHOOK_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    print(f"✅ Status: {response.status_code}")
    print(f"📝 Resposta: {response.text}")
    
    if response.status_code == 200:
        print("\n✨ Mensagem enviada com sucesso!")
        print("Agora acesse http://localhost:3001/chats para ver a conversa")
    else:
        print(f"\n❌ Erro ao enviar: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ Erro: Não conseguiu conectar ao backend")
    print("   Verifique se o backend está rodando: docker-compose ps")
except Exception as e:
    print(f"❌ Erro: {e}")
