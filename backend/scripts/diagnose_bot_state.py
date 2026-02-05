"""
Script de diagnóstico para o problema de estado do bot.

Uso:
    python scripts/diagnose_bot_state.py <phone>
    python scripts/diagnose_bot_state.py 5541999999999

Este script:
1. Verifica conexão com Redis
2. Mostra estado atual do contexto
3. Simula uma transição de estado
4. Verifica se a transição foi persistida
"""

import asyncio
import sys
import json
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, ".")

async def diagnose(phone: str):
    """Executa diagnóstico completo."""
    from app.database import redis_manager
    from app.core.state_machine import ConversationState, ConversationContext
    from app.config import settings

    print("\n" + "=" * 60)
    print("DIAGNÓSTICO DO BOT - PERSISTÊNCIA DE ESTADO")
    print("=" * 60)

    # 1. Testar conexão com Redis
    print("\n[1] Testando conexão com Redis...")
    try:
        await redis_manager.connect()
        print(f"    ✓ Redis conectado: {settings.redis_url}")
    except Exception as e:
        print(f"    ✗ ERRO ao conectar: {e}")
        return

    # 2. Verificar estado atual
    print(f"\n[2] Verificando estado atual para {phone}...")
    try:
        data = await redis_manager.get_conversation_state(phone)
        if data:
            print(f"    ✓ Contexto encontrado:")
            print(f"      - state: {data.get('state', 'N/A')}")
            print(f"      - customer_name: {data.get('customer_name', 'N/A')}")
            print(f"      - selected_product: {data.get('selected_product', 'N/A')}")
            print(f"      - message_count: {data.get('message_count', 0)}")
            print(f"      - last_message_at: {data.get('last_message_at', 'N/A')}")
        else:
            print("    - Nenhum contexto encontrado (cliente novo)")
    except Exception as e:
        print(f"    ✗ ERRO ao ler: {e}")
        return

    # 3. Testar escrita/leitura
    print(f"\n[3] Testando ciclo escrita/leitura...")
    test_context = ConversationContext(phone=phone)
    test_context.state = ConversationState.AWAITING_PRODUCT
    test_context.message_count = 999  # Valor de teste

    try:
        # Salvar
        await redis_manager.set_conversation_state(
            phone,
            test_context.to_dict(),
            ttl=settings.redis_conversation_ttl
        )
        print(f"    ✓ Escrita: state={test_context.state.value}")

        # Ler de volta
        read_data = await redis_manager.get_conversation_state(phone)
        if read_data:
            read_state = read_data.get("state")
            read_count = read_data.get("message_count")

            if read_state == "awaiting_product" and read_count == 999:
                print(f"    ✓ Leitura: state={read_state}, message_count={read_count}")
                print("    ✓ CICLO ESCRITA/LEITURA OK!")
            else:
                print(f"    ✗ INCONSISTÊNCIA!")
                print(f"      Esperado: state=awaiting_product, message_count=999")
                print(f"      Obtido: state={read_state}, message_count={read_count}")
        else:
            print("    ✗ FALHA: Contexto não encontrado após escrita!")

    except Exception as e:
        print(f"    ✗ ERRO no ciclo: {e}")

    # 4. Verificar TTL
    print(f"\n[4] Verificando TTL...")
    try:
        ttl = await redis_manager.client.ttl(f"chat:{phone}")
        print(f"    - TTL configurado: {settings.redis_conversation_ttl}s ({settings.redis_conversation_ttl/60:.1f} min)")
        print(f"    - TTL atual da chave: {ttl}s ({ttl/60:.1f} min)")
    except Exception as e:
        print(f"    ✗ ERRO ao verificar TTL: {e}")

    # 5. Simular fluxo completo
    print(f"\n[5] Simulando fluxo de transição de estado...")
    from app.core.flow_engine import flow_engine

    try:
        # Carregar contexto
        ctx1 = await flow_engine.get_context(phone)
        print(f"    - Estado inicial: {ctx1.state.value}")

        # Mudar estado
        ctx1.state = ConversationState.AWAITING_QUANTITY
        ctx1.selected_product = "P13"

        # Salvar
        await flow_engine.save_context(ctx1)
        print(f"    - Estado após salvar: {ctx1.state.value}")

        # Carregar novamente (simula próxima mensagem)
        ctx2 = await flow_engine.get_context(phone)
        print(f"    - Estado recarregado: {ctx2.state.value}")

        if ctx2.state == ConversationState.AWAITING_QUANTITY:
            print("    ✓ TRANSIÇÃO DE ESTADO OK!")
        else:
            print("    ✗ FALHA: Estado não foi mantido!")
            print(f"      Esperado: awaiting_quantity")
            print(f"      Obtido: {ctx2.state.value}")

    except Exception as e:
        print(f"    ✗ ERRO no fluxo: {e}")
        import traceback
        traceback.print_exc()

    # 6. Limpar teste
    print(f"\n[6] Restaurando estado original...")
    if data:
        await redis_manager.set_conversation_state(phone, data, ttl=settings.redis_conversation_ttl)
        print("    ✓ Estado original restaurado")
    else:
        await redis_manager.delete_conversation_state(phone)
        print("    ✓ Contexto de teste removido")

    # Desconectar
    await redis_manager.disconnect()

    print("\n" + "=" * 60)
    print("DIAGNÓSTICO CONCLUÍDO")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/diagnose_bot_state.py <phone>")
        print("Exemplo: python scripts/diagnose_bot_state.py 5541999999999")
        sys.exit(1)

    phone = sys.argv[1]
    asyncio.run(diagnose(phone))
