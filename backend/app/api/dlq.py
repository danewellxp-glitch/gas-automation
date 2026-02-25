"""
API para monitoramento e gerenciamento da Dead Letter Queue (DLQ).
"""

import json
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import redis.asyncio as redis

from app.config import settings
from app.utils.structured_logging import get_structured_logger

logger = get_structured_logger(__name__)

router = APIRouter(prefix="/api/dlq", tags=["DLQ"])

DLQ_STREAM_NAME = "stream:dlq"


class DLQMessage(BaseModel):
    """Mensagem na DLQ."""
    message_id: str
    original_message_id: str
    error: str
    failed_at: str
    consumer: Optional[str] = None
    retry_count: Optional[int] = None
    phone: Optional[str] = None
    message_text: Optional[str] = None


class DLQStats(BaseModel):
    """Estatísticas da DLQ."""
    total_messages: int
    messages: List[DLQMessage]
    oldest_message: Optional[str] = None
    newest_message: Optional[str] = None


async def get_redis_client() -> redis.Redis:
    """Obtém cliente Redis."""
    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=False,
    )


@router.get("/stats", response_model=DLQStats)
async def get_dlq_stats():
    """
    Obtém estatísticas da DLQ.
    
    Returns:
        Estatísticas incluindo total de mensagens e lista de mensagens
    """
    try:
        client = await get_redis_client()
        
        # Obter todas as mensagens do DLQ
        messages_data = await client.xrange(DLQ_STREAM_NAME, "-", "+", count=1000)
        
        messages = []
        oldest = None
        newest = None
        
        for msg_id_bytes, msg_data in messages_data:
            msg_id = msg_id_bytes.decode() if isinstance(msg_id_bytes, bytes) else msg_id_bytes
            
            # Deserializar dados
            data = {}
            for key, value in msg_data.items():
                key_str = key.decode() if isinstance(key, bytes) else key
                value_str = value.decode() if isinstance(value, bytes) else value
                data[key_str] = value_str
            
            # Extrair informações
            original_message_id = data.get("original_message_id", "")
            error = data.get("error", "Unknown error")
            failed_at = data.get("failed_at", "")
            consumer = data.get("consumer")
            retry_count = int(data.get("retry_count", 3)) if data.get("retry_count") else None
            
            # Tentar extrair phone e message_text
            phone = None
            message_text = None
            message_data_raw = data.get("message_data", {})
            if isinstance(message_data_raw, str):
                try:
                    message_data = json.loads(message_data_raw)
                    if isinstance(message_data, dict):
                        msg = message_data.get("message", {})
                        if isinstance(msg, dict):
                            key = msg.get("key", {})
                            phone = key.get("remoteJid", "").replace("@c.us", "").replace("@lid", "")
                            message_text = msg.get("message", {}).get("conversation", "")
                except:
                    pass
            
            messages.append(DLQMessage(
                message_id=msg_id,
                original_message_id=original_message_id or msg_id,
                error=error,
                failed_at=failed_at,
                consumer=consumer,
                retry_count=retry_count,
                phone=phone,
                message_text=message_text[:100] if message_text else None,
            ))
            
            if not oldest:
                oldest = msg_id
            newest = msg_id
        
        await client.close()
        
        return DLQStats(
            total_messages=len(messages),
            messages=messages,
            oldest_message=oldest,
            newest_message=newest,
        )
        
    except Exception as e:
        logger.error(f"Erro ao obter stats da DLQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=List[DLQMessage])
async def get_dlq_messages(
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de mensagens"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    """
    Lista mensagens na DLQ.
    
    Args:
        limit: Número máximo de mensagens a retornar
        offset: Offset para paginação
        
    Returns:
        Lista de mensagens na DLQ
    """
    try:
        client = await get_redis_client()
        
        # Obter mensagens (mais recentes primeiro)
        messages_data = await client.xrevrange(DLQ_STREAM_NAME, "+", "-", count=limit + offset)
        
        # Aplicar offset
        messages_data = messages_data[offset:offset + limit]
        
        messages = []
        for msg_id_bytes, msg_data in messages_data:
            msg_id = msg_id_bytes.decode() if isinstance(msg_id_bytes, bytes) else msg_id_bytes
            
            # Deserializar dados
            data = {}
            for key, value in msg_data.items():
                key_str = key.decode() if isinstance(key, bytes) else key
                value_str = value.decode() if isinstance(value, bytes) else value
                data[key_str] = value_str
            
            # Extrair informações
            original_message_id = data.get("original_message_id", "")
            error = data.get("error", "Unknown error")
            failed_at = data.get("failed_at", "")
            consumer = data.get("consumer")
            retry_count = int(data.get("retry_count", 3)) if data.get("retry_count") else None
            
            # Tentar extrair phone e message_text
            phone = None
            message_text = None
            message_data_raw = data.get("message_data", {})
            if isinstance(message_data_raw, str):
                try:
                    message_data = json.loads(message_data_raw)
                    if isinstance(message_data, dict):
                        msg = message_data.get("message", {})
                        if isinstance(msg, dict):
                            key = msg.get("key", {})
                            phone = key.get("remoteJid", "").replace("@c.us", "").replace("@lid", "")
                            message_text = msg.get("message", {}).get("conversation", "")
                except:
                    pass
            
            messages.append(DLQMessage(
                message_id=msg_id,
                original_message_id=original_message_id or msg_id,
                error=error,
                failed_at=failed_at,
                consumer=consumer,
                retry_count=retry_count,
                phone=phone,
                message_text=message_text[:100] if message_text else None,
            ))
        
        await client.close()
        
        return messages
        
    except Exception as e:
        logger.error(f"Erro ao listar mensagens da DLQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages/{message_id}")
async def delete_dlq_message(message_id: str):
    """
    Remove uma mensagem específica da DLQ.
    
    Args:
        message_id: ID da mensagem no DLQ stream
        
    Returns:
        Confirmação de remoção
    """
    try:
        client = await get_redis_client()
        
        # Remover mensagem do stream
        deleted = await client.xdel(DLQ_STREAM_NAME, message_id)
        
        await client.close()
        
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada na DLQ")
        
        return {"status": "deleted", "message_id": message_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar mensagem da DLQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_dlq():
    """
    Limpa toda a DLQ (use com cuidado!).
    
    Returns:
        Confirmação de limpeza
    """
    try:
        client = await get_redis_client()
        
        # Obter todas as mensagens
        messages_data = await client.xrange(DLQ_STREAM_NAME, "-", "+")
        
        if not messages_data:
            await client.close()
            return {"status": "cleared", "messages_deleted": 0}
        
        # Deletar todas as mensagens
        message_ids = [msg_id for msg_id, _ in messages_data]
        deleted = await client.xdel(DLQ_STREAM_NAME, *message_ids)
        
        await client.close()
        
        logger.warning(f"DLQ limpa: {deleted} mensagens removidas")
        
        return {"status": "cleared", "messages_deleted": deleted}
        
    except Exception as e:
        logger.error(f"Erro ao limpar DLQ: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
