#!/usr/bin/env python3
"""
Script para testar WebSocket do Gas Automation.

Uso:
    python3 TEST_WEBSOCKET.py
"""

import subprocess
import json
import time
import threading
from datetime import datetime

def print_section(title):
    """Imprime seção formatada"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")

def send_webhook_message(phone: str, message: str) -> bool:
    """Envia mensagem via webhook WAHA"""
    import time
    timestamp = int(time.time())
    
    payload = {
        "event": "message",
        "session": "default",
        "payload": {
            "from": f"{phone}@c.us",
            "fromMe": False,
            "id": f"msg_{timestamp}_{phone}",
            "body": message,
            "timestamp": timestamp,
            "pushName": "Cliente Teste",
            "_data": {"notifyName": "Cliente Teste"}
        }
    }
    
    try:
        cmd = [
            'curl', '-s', '-X', 'POST',
            'http://localhost:8000/webhooks/waha',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        response = json.loads(result.stdout) if result.stdout else {}
        success = response.get('status') == 'processing'
        return success
    except Exception as e:
        print(f"❌ Erro ao enviar webhook: {e}")
        return False

def check_websocket_endpoint():
    """Verifica se endpoint WebSocket está acessível"""
    try:
        cmd = ['curl', '-s', '-I', 'http://localhost:8000/api/docs']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return '200' in result.stdout or 'HTML' in result.stdout
    except:
        return False

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  GAS AUTOMATION - TESTE DE WEBSOCKET".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")

    print_section("1. VERIFICANDO CONEXÃO COM BACKEND")
    
    try:
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost:8000/api/docs'],
            capture_output=True,
            text=True,
            timeout=5
        )
        status = result.stdout
        if status == '200':
            print("✅ Backend está acessível (HTTP 200)")
        else:
            print(f"❌ Backend retornou HTTP {status}")
            print("⚠️  Certifique-se que o backend está rodando:")
            print("   docker-compose -f docker-compose.yml up -d backend")
            return
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return

    print_section("2. TESTANDO WEBHOOK")
    
    phone = "5541987654321"
    test_message = f"🧪 Teste automático em {datetime.now().strftime('%H:%M:%S')}"
    
    print(f"📱 Enviando mensagem de teste...")
    print(f"   Telefone: {phone}")
    print(f"   Mensagem: {test_message}")
    
    if send_webhook_message(phone, test_message):
        print("✅ Webhook enviado com sucesso (status: processing)")
    else:
        print("❌ Erro ao enviar webhook")
        return
    
    print_section("3. MONITORANDO WEBSOCKET")
    
    print("💡 Para visualizar as mensagens em tempo real:")
    print("")
    print("   📌 OPÇÃO 1 - Página de Teste:")
    print("      Abra em seu navegador:")
    print("      http://localhost:8888/test_websocket.html")
    print("")
    print("   📌 OPÇÃO 2 - Dashboard Admin:")
    print("      Acesse:")
    print("      http://localhost:3001")
    print("      (Faça login e vá para a aba de conversas)")
    print("")
    
    print_section("4. VERIFICAÇÃO MANUAL DE LOGS")
    
    print("Se as mensagens ainda não aparecem, execute:")
    print("")
    print("  docker-compose -f docker-compose.yml logs backend -f | grep -i websocket")
    print("")
    print("Você deveria ver mensagens como:")
    print('  "WebSocket conectado. Total: X"')
    print('  "Broadcasting \'new_message\' para X conexões"')
    print('  "WebSocket emitido para..."')
    print("")
    
    print_section("5. PRÓXIMOS PASSOS")
    
    print("✅ Se a mensagem apareceu - WebSocket está funcionando!")
    print("")
    print("❌ Se NÃO apareceu:")
    print("")
    print("   1. Verifique os logs do backend:")
    print("      docker-compose logs backend --tail=50")
    print("")
    print("   2. Verifique se há erro de autenticação (403/401)")
    print("")
    print("   3. Verifique no console do navegador (F12):")
    print("      - Abra DevTools → Console")
    print("      - Procure por 'WebSocket conectado' ou erro")
    print("")
    print("   4. Se houver erro de autenticação, o frontend pode estar")
    print("      enviando token JWT que o backend não está validando")
    print("")
    
    print_section("RESUMO DO TESTE")
    
    print("✅ Código enviado para webhook")
    print("✅ Arquivo de teste criado em:")
    print("   http://localhost:8888/test_websocket.html")
    print("")
    print("Aguarde a mensagem aparecer no navegador...")
    print("")

if __name__ == '__main__':
    main()
