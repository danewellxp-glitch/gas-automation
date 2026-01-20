#!/usr/bin/env python3
"""
Script para testar o fluxo completo de pedido com cartão.
Simula um cliente fazendo um pedido do começo até a confirmação.
"""

import requests
import json
from datetime import datetime
import time

WEBHOOK_URL = "http://localhost:8000/webhooks/waha"
PHONE = "5541987654321"  # Um número que vai criar nova conversa

def send_message(message_text, push_name="Cliente Teste"):
    """Envia uma mensagem simulando o WhatsApp."""
    payload = {
        "event": "message",
        "instanceId": "test_instance",
        "data": {
            "key": {
                "remoteJid": f"{PHONE}@s.whatsapp.net",
                "fromMe": False,
                "id": f"test_{datetime.now().timestamp()}"
            },
            "message": {
                "conversation": message_text
            },
            "messageTimestamp": int(datetime.now().timestamp())
        }
    }

    print(f"📤 Enviando: {message_text[:50]}...")
    response = requests.post(
        WEBHOOK_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    if response.status_code == 200:
        print(f"   ✅ Recebido (status: {response.status_code})")
        return True
    else:
        print(f"   ❌ Erro: {response.status_code}")
        return False

def test_order_flow():
    """Testa o fluxo completo de pedido."""
    print("\n" + "="*60)
    print("🛒 TESTE DE FLUXO COMPLETO DE PEDIDO COM CARTÃO")
    print("="*60 + "\n")

    steps = [
        ("1", "Selecionar produto P13"),
        ("1", "Confirmar quantidade 1"),
        ("1", "Confirmar endereço (vai pedir para mudar)"),
        ("rua teste 123, curitiba pr brasil", "Alterar endereço"),
        ("3", "Escolher cartão como pagamento"),
        ("1", "CONFIRMAR PEDIDO COM CARTÃO (aqui estava dando erro)"),
    ]

    for i, (input_text, description) in enumerate(steps, 1):
        print(f"\n[Passo {i}] {description}")
        if not send_message(input_text):
            print("❌ Erro ao enviar mensagem")
            return False
        
        time.sleep(2)  # Aguardar processamento

    print("\n" + "="*60)
    print("✅ TESTE COMPLETO!")
    print("="*60)
    print("\nVerifique:")
    print("1. No WhatsApp, a última resposta deve ser: '✅ Pedido Confirmado!'")
    print("2. No dashboard, a conversa deve estar em 'order_confirmed'")
    print("3. No banco de dados, deve haver um novo pedido criado\n")

if __name__ == "__main__":
    try:
        test_order_flow()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
