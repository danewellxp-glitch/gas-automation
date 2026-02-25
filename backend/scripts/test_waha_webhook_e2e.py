#!/usr/bin/env python3
"""
Teste ponta a ponta: Webhook WAHA -> mensagem no chat do operador.

1. Envia POST para /webhooks/waha simulando uma mensagem do WhatsApp.
2. Aguarda o processamento em background.
3. Verifica se a mensagem aparece em GET /api/conversations e em
   GET /api/conversations/{id}/messages.

Uso:
  BACKEND_URL=http://localhost:8000 python backend/scripts/test_waha_webhook_e2e.py
  python backend/scripts/test_waha_webhook_e2e.py  # usa localhost:8000
"""
import os
import sys
import time
import uuid

try:
    import httpx
except ImportError:
    print("Instale: pip install httpx")
    sys.exit(1)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
WEBHOOK_URL = f"{BACKEND_URL}/webhooks/waha"
CONVERSATIONS_URL = f"{BACKEND_URL}/api/conversations"


def build_waha_payload(phone: str, text: str, message_id=None):
    """Monta o body que o WAHA envia para o webhook (event=message)."""
    msg_id = message_id or f"test_{uuid.uuid4().hex[:12]}"
    return {
        "event": "message",
        "session": "default",
        "payload": {
            "from": phone,
            "fromMe": False,
            "id": msg_id,
            "body": text,
            "timestamp": int(time.time()),
            "pushName": "Teste E2E",
            "_data": {"notifyName": "Teste E2E"},
        },
    }


def main():
    phone = "5541999999999@c.us"
    text = f"Teste E2E WAHA -> Chat Operador ({time.strftime('%H:%M:%S')})"
    payload = build_waha_payload(phone, text)

    print(f"Backend: {BACKEND_URL}")
    print(f"Webhook: {WEBHOOK_URL}")
    print(f"Enviando mensagem simulada: {phone} -> {text!r}")
    print()

    with httpx.Client(timeout=30.0) as client:
        # 1) POST webhook WAHA
        r = client.post(WEBHOOK_URL, json=payload)
        if r.status_code != 200:
            print(f"ERRO: Webhook retornou {r.status_code}: {r.text}")
            sys.exit(1)
        data = r.json()
        if data.get("status") == "ignored" and data.get("reason") == "own_message":
            print("ERRO: Payload interpretado como mensagem própria (fromMe?).")
            sys.exit(1)
        print(f"Webhook OK: {data}")

        # 2) Aguardar processamento em background (EventLog + flow)
        time.sleep(2.5)
        print("Aguardando 2.5s (processamento em background)...")

        # 3) Listar conversas e achar nosso phone
        r2 = client.get(CONVERSATIONS_URL)
        if r2.status_code != 200:
            print(f"ERRO: GET /api/conversations retornou {r2.status_code}: {r2.text}")
            sys.exit(1)
        conversations = r2.json()
        conv = next((c for c in conversations if c.get("id") == phone or c.get("customer_number") == phone), None)
        if not conv:
            print("Conversas retornadas:", [c.get("id") or c.get("customer_number") for c in conversations])
            print("ERRO: Conversa do número de teste não encontrada. Verifique se o backend e o banco estão ok.")
            sys.exit(1)
        print(f"Conversa encontrada: {conv.get('id')} | last_message: {conv.get('last_message')!r}")

        # 4) Mensagens da conversa
        messages_url = f"{CONVERSATIONS_URL}/{phone}/messages"
        r3 = client.get(messages_url)
        if r3.status_code != 200:
            print(f"ERRO: GET {messages_url} retornou {r3.status_code}: {r3.text}")
            sys.exit(1)
        messages = r3.json()
        last_incoming = next((m for m in reversed(messages) if m.get("sender") == "customer"), None)
        if not last_incoming:
            print("Mensagens:", messages)
            print("ERRO: Nenhuma mensagem do cliente na conversa.")
            sys.exit(1)
        if text not in (last_incoming.get("content") or ""):
            print(f"Última mensagem do cliente: {last_incoming.get('content')!r}")
            print(f"ERRO: Texto esperado não encontrado: {text!r}")
            sys.exit(1)

        print()
        print("OK: Mensagem apareceu no chat do operador (conversations + messages).")
        print("    Você pode abrir o painel do operador e ver a conversa e a mensagem.")


if __name__ == "__main__":
    main()
