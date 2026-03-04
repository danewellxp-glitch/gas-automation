#!/usr/bin/env python3
"""
Reset completo para testes do zero:
- Todas as mensagens (EventLog: message_received, message_sent, etc.)
- Streams Redis (stream:messages, stream:dlq)
- Dedup e locks Redis (msg_dedup:*, lock:process:*, lock:phone:*)
- Contextos de conversa e pedido no Redis (conversation:*, order:*, customer:*)
- Cache LID (lid_resolve:*)
- Pedidos (orders) e depois Clientes (customers) no PostgreSQL

Uso (na raiz do projeto ou de backend):
  cd backend && python -m scripts.reset_messages_and_customers
  ou
  python backend/scripts/reset_messages_and_customers.py

Requer: REDIS_URL e DATABASE_URL configurados.
"""

import asyncio
import logging
import os
import sys

# Garantir que o backend está no path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def clear_redis(redis_client):
    """Limpa streams, dedup, locks e contextos no Redis."""
    deleted = 0

    # Padrões de chaves
    patterns = [
        "msg_dedup:*",
        "lock:process:*",
        "lock:phone:*",
        "conversation:*",
        "order:*",
        "customer:*",
        "lid_resolve:*",
    ]

    for pattern in patterns:
        try:
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=500)
                if keys:
                    await redis_client.delete(*keys)
                    deleted += len(keys)
                    logger.info("  Redis: apagadas %d chaves %s", len(keys), pattern)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning("  Redis scan/delete %s: %s", pattern, e)

    # Streams: deletar e recriar vazios não é trivial; XTRIM maxlen 0 ou DEL
    try:
        for stream_name in ("stream:messages", "stream:dlq"):
            try:
                await redis_client.delete(stream_name)
                deleted += 1
                logger.info("  Redis: stream removido %s", stream_name)
            except Exception as e:
                logger.warning("  Redis delete stream %s: %s", stream_name, e)
    except Exception as e:
        logger.warning("  Redis streams: %s", e)

    return deleted


async def main():
    from app.config import settings
    from app.database import redis_manager, AsyncSessionLocal
    from app.models.event_log import EventLog
    from app.models.order import Order
    from app.models.customer import Customer
    from app.models.auth_models import Conversation, Message, Contact
    from sqlalchemy import delete

    logger.info("=== Reset: mensagens, testes e clientes ===\n")

    # 1) Redis
    logger.info("1) Limpando Redis (streams, dedup, locks, contextos)...")
    await redis_manager.connect()
    try:
        n_redis = await clear_redis(redis_manager._redis)
        logger.info("   Total Redis: %d chaves/streams removidos.\n", n_redis)
    finally:
        await redis_manager.disconnect()

    # 2) PostgreSQL
    logger.info("2) Limpando PostgreSQL...")

    async with AsyncSessionLocal() as db:
        try:
            # 2.1 EventLog (todas as mensagens e eventos de chat)
            r = await db.execute(delete(EventLog))
            event_count = r.rowcount
            logger.info("   EventLog: %d registros removidos.", event_count)

            # 2.2 Pedidos (OrderItem, Delivery, Payment têm ondelete=CASCADE no Order; ao deletar Order o banco remove os dependentes)
            r = await db.execute(delete(Order))
            order_count = r.rowcount
            logger.info("   Order: %d removidos (itens/delivery/payment em cascata).", order_count)

            # 2.3 Clientes
            r = await db.execute(delete(Customer))
            customer_count = r.rowcount
            logger.info("   Customer: %d removidos.", customer_count)

            # 2.4 Veloce Chat Features
            r1 = await db.execute(delete(Message))
            r2 = await db.execute(delete(Conversation))
            r3 = await db.execute(delete(Contact))
            logger.info("   Veloce Chat (Conversations/Messages/Contacts): %d/%d/%d removidos.", r2.rowcount, r1.rowcount, r3.rowcount)

            await db.commit()
            logger.info("\n   PostgreSQL: commit ok.")
        except Exception as e:
            await db.rollback()
            logger.exception("Erro ao limpar PostgreSQL: %s", e)
            raise

    logger.info("\n=== Reset concluído. Pode testar do zero. ===")


if __name__ == "__main__":
    asyncio.run(main())
