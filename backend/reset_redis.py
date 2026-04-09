
import asyncio
import json
import os
import sys

# Adicionar o diretório raiz ao path para importar a app
sys.path.append(os.getcwd())

from app.config import settings
from app.database import redis_manager

async def reset_all_sessions():
    await redis_manager.connect()
    redis = redis_manager.client
    
    # Buscar todas as chaves de chat e ordem
    chat_keys = await redis.keys("chat:*")
    order_keys = await redis.keys("order:*")
    lock_keys = await redis.keys("lock:*")
    
    all_keys = chat_keys + order_keys + lock_keys
    
    print(f"Encontradas {len(all_keys)} chaves para remover.")
    
    if all_keys:
        for key in all_keys:
            await redis.delete(key)
            print(f"Removida chave: {key}")
        print("Sucesso: Todos os estados do chatbot foram resetados.")
    else:
        print("Nenhuma sessão ativa encontrada para resetar.")
    
    await redis_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(reset_all_sessions())
