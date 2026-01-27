#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste isolado do webhook de localizacao.
Simula o fluxo completo sem precisar dos servicos externos.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch


# ===== Simular ConversationContext =====
@dataclass
class MockConversationContext:
    phone: str
    state: str = "start"
    address: Optional[dict] = None
    last_message_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        return {
            "phone": self.phone,
            "state": self.state,
            "address": self.address,
            "last_message_at": self.last_message_at.isoformat()
        }


# ===== Simular WAHAMessage =====
@dataclass
class MockWAHAMessage:
    phone: str
    location: dict

    @property
    def is_location(self):
        return self.location is not None


# ===== Funcao process_location_message (copia simplificada) =====
async def process_location_message(
    phone: str,
    location: dict,
    message_id: str = None,
    # Mocks injetados
    emit_func=None,
    save_event_func=None,
    flow_engine=None,
    waha_client=None
):
    """
    Processa mensagem de localizacao do WhatsApp.
    Versao de teste com dependencias injetadas.
    """
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    address = location.get("address", "")
    name = location.get("name", "")

    results = {
        "websocket_emitted": False,
        "event_saved": False,
        "context_updated": False,
        "confirmation_sent": False,
        "errors": []
    }

    # 1. Emitir via WebSocket
    try:
        location_text = f"📍 Localização recebida: {name or address or f'{latitude}, {longitude}'}"
        if emit_func:
            await emit_func(phone, location_text, "incoming")
        results["websocket_emitted"] = True
        results["websocket_message"] = location_text
    except Exception as e:
        results["errors"].append(f"WebSocket: {e}")

    # 2. Salvar EventLog
    try:
        event_payload = {
            "phone": phone,
            "latitude": latitude,
            "longitude": longitude,
            "address": address,
            "name": name,
        }
        if save_event_func:
            await save_event_func("location_received", event_payload)
        results["event_saved"] = True
        results["event_payload"] = event_payload
    except Exception as e:
        results["errors"].append(f"EventLog: {e}")

    # 3. Atualizar contexto
    try:
        if flow_engine:
            context = await flow_engine.get_context(phone)
            if context:
                context.address = context.address or {}
                context.address["location"] = {
                    "latitude": latitude,
                    "longitude": longitude,
                }
                if address:
                    context.address["formatted"] = address
                if name:
                    context.address["name"] = name
                await flow_engine.save_context(context)
                results["context_updated"] = True
                results["context_address"] = context.address
    except Exception as e:
        results["errors"].append(f"Context: {e}")

    # 4. Enviar confirmacao ao cliente
    try:
        confirmation = (
            f"📍 Localização recebida!\n"
            f"Coordenadas: {latitude:.6f}, {longitude:.6f}\n"
            f"{f'Endereço: {address}' if address else ''}\n\n"
            f"Vamos usar esta localização para a entrega."
        )
        if waha_client:
            await waha_client.send_text(phone, confirmation)
        results["confirmation_sent"] = True
        results["confirmation_message"] = confirmation
    except Exception as e:
        results["errors"].append(f"WhatsApp: {e}")

    return results


async def run_test():
    print("=" * 60)
    print("TESTE: Webhook de Localização do WhatsApp")
    print("=" * 60)

    # Dados de teste
    phone = "5541999887766@c.us"
    location = {
        "latitude": -25.4284,
        "longitude": -49.2733,
        "name": "Casa do Cliente",
        "address": "Rua XV de Novembro, 123 - Centro, Curitiba"
    }

    print(f"\n📱 INPUT:")
    print(f"   Phone: {phone}")
    print(f"   Location: {location}")

    # Criar mocks
    mock_emit = AsyncMock()
    mock_save_event = AsyncMock()

    mock_context = MockConversationContext(phone=phone)
    mock_flow_engine = MagicMock()
    mock_flow_engine.get_context = AsyncMock(return_value=mock_context)
    mock_flow_engine.save_context = AsyncMock()

    mock_waha = MagicMock()
    mock_waha.send_text = AsyncMock()

    # Executar
    results = await process_location_message(
        phone=phone,
        location=location,
        emit_func=mock_emit,
        save_event_func=mock_save_event,
        flow_engine=mock_flow_engine,
        waha_client=mock_waha
    )

    # Verificar resultados
    print(f"\n✅ RESULTADOS:")
    print(f"   WebSocket emitido: {results['websocket_emitted']}")
    print(f"   EventLog salvo: {results['event_saved']}")
    print(f"   Contexto atualizado: {results['context_updated']}")
    print(f"   Confirmação enviada: {results['confirmation_sent']}")

    if results.get("errors"):
        print(f"\n❌ ERROS:")
        for err in results["errors"]:
            print(f"   - {err}")

    print(f"\n📡 WEBSOCKET (operador vê):")
    print(f"   {results.get('websocket_message', 'N/A')}")

    print(f"\n💾 EVENTLOG (banco):")
    print(f"   {results.get('event_payload', 'N/A')}")

    print(f"\n🔄 CONTEXTO (Redis):")
    print(f"   {results.get('context_address', 'N/A')}")

    print(f"\n💬 WHATSAPP (cliente recebe):")
    for line in results.get('confirmation_message', 'N/A').split('\n'):
        print(f"   {line}")

    # Verificar chamadas dos mocks
    print(f"\n🔍 VERIFICAÇÃO DOS MOCKS:")
    print(f"   emit_new_message chamado: {mock_emit.called}")
    print(f"   save_event chamado: {mock_save_event.called}")
    print(f"   flow_engine.get_context chamado: {mock_flow_engine.get_context.called}")
    print(f"   flow_engine.save_context chamado: {mock_flow_engine.save_context.called}")
    print(f"   waha_client.send_text chamado: {mock_waha.send_text.called}")

    # Resultado final
    all_passed = all([
        results['websocket_emitted'],
        results['event_saved'],
        results['context_updated'],
        results['confirmation_sent'],
        not results.get('errors')
    ])

    print(f"\n{'=' * 60}")
    if all_passed:
        print("✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_test())
    sys.exit(0 if success else 1)
