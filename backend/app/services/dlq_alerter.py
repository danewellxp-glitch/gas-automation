"""
Serviço de Alertas para Dead Letter Queue (DLQ).

Monitora mensagens que vão para DLQ e envia alertas via email/webhook.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import redis.asyncio as redis

from app.config import settings
from app.utils.structured_logging import get_structured_logger

logger = get_structured_logger(__name__)


class DLQAlerter:
    """
    Serviço de alertas para DLQ.
    
    Monitora o stream:dlq e envia alertas quando novas mensagens são adicionadas.
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self.last_alert_time: Dict[str, float] = {}  # Para rate limiting
        self.alert_cooldown = 300  # 5 minutos entre alertas do mesmo tipo

    async def connect(self):
        """Conecta ao Redis."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=False,
            )
            logger.info("[DLQAlerter] Conectado ao Redis")
        except Exception as e:
            logger.error(f"[DLQAlerter] Erro ao conectar: {e}")
            raise

    async def disconnect(self):
        """Desconecta do Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def send_alert(
        self,
        message_id: str,
        error: str,
        message_data: Dict[str, Any],
        retry_count: int,
    ):
        """
        Envia alerta sobre mensagem na DLQ.
        
        Args:
            message_id: ID da mensagem
            error: Mensagem de erro
            message_data: Dados da mensagem
            retry_count: Número de tentativas antes de ir para DLQ
        """
        try:
            # Rate limiting: não alertar muito frequentemente
            alert_key = f"dlq_alert_{message_id[:8]}"
            current_time = datetime.now(timezone.utc).timestamp()
            
            if alert_key in self.last_alert_time:
                if current_time - self.last_alert_time[alert_key] < self.alert_cooldown:
                    logger.debug(f"[DLQAlerter] Alert cooldown ativo para {message_id}")
                    return
            
            self.last_alert_time[alert_key] = current_time

            # Construir mensagem de alerta
            alert_message = self._build_alert_message(
                message_id, error, message_data, retry_count
            )

            # Enviar alerta via múltiplos canais
            await self._send_email_alert(alert_message)
            await self._send_webhook_alert(alert_message)
            
            # Log estruturado
            logger.error(
                f"[DLQAlerter] Alerta enviado: message_id={message_id} "
                f"error={error} retry_count={retry_count}",
                extra={
                    "message_id": message_id,
                    "alert_type": "dlq",
                    "error": error,
                    "retry_count": retry_count,
                }
            )

        except Exception as e:
            logger.error(f"[DLQAlerter] Erro ao enviar alerta: {e}", exc_info=True)

    def _build_alert_message(
        self,
        message_id: str,
        error: str,
        message_data: Dict[str, Any],
        retry_count: int,
    ) -> Dict[str, Any]:
        """Constrói mensagem de alerta estruturada."""
        # Extrair informações úteis da mensagem
        phone = ""
        text = ""
        if isinstance(message_data, dict):
            msg_data = message_data.get("message_data", {})
            if isinstance(msg_data, str):
                try:
                    msg_data = json.loads(msg_data)
                except:
                    pass
            
            if isinstance(msg_data, dict):
                msg = msg_data.get("message", {})
                if isinstance(msg, dict):
                    key = msg.get("key", {})
                    phone = key.get("remoteJid", "").replace("@c.us", "").replace("@lid", "")
                    text = msg.get("message", {}).get("conversation", "") or ""

        return {
            "alert_type": "dlq",
            "message_id": message_id,
            "error": error,
            "retry_count": retry_count,
            "phone": phone,
            "message_text": text[:100],  # Primeiros 100 caracteres
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "high",
        }

    async def _send_email_alert(self, alert_message: Dict[str, Any]):
        """Envia alerta por email."""
        try:
            # Verificar se email está configurado
            alert_email = getattr(settings, "dlq_alert_email", None)
            if not alert_email:
                logger.debug("[DLQAlerter] Email de alerta não configurado")
                return

            # Usar notification-service se disponível
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"{settings.sync_service_url.replace(':8003', ':8002')}/api/notify/email",
                        json={
                            "to_email": alert_email,
                            "subject": f"🚨 DLQ Alert: Mensagem falhou após {alert_message['retry_count']} tentativas",
                            "body_text": self._format_email_body(alert_message),
                            "body_html": self._format_email_html(alert_message),
                        },
                        timeout=5.0,
                    )
                    if response.status_code == 200:
                        logger.info(f"[DLQAlerter] Email de alerta enviado para {alert_email}")
            except Exception as e:
                logger.debug(f"[DLQAlerter] Erro ao enviar email (notification-service): {e}")

        except Exception as e:
            logger.debug(f"[DLQAlerter] Erro ao enviar email: {e}")

    async def _send_webhook_alert(self, alert_message: Dict[str, Any]):
        """Envia alerta via webhook."""
        try:
            webhook_url = getattr(settings, "dlq_alert_webhook_url", None)
            if not webhook_url:
                logger.debug("[DLQAlerter] Webhook de alerta não configurado")
                return

            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    webhook_url,
                    json=alert_message,
                    timeout=5.0,
                )
                if response.status_code in [200, 201, 204]:
                    logger.info(f"[DLQAlerter] Webhook de alerta enviado para {webhook_url}")
        except Exception as e:
            logger.debug(f"[DLQAlerter] Erro ao enviar webhook: {e}")

    def _format_email_body(self, alert: Dict[str, Any]) -> str:
        """Formata corpo do email em texto plano."""
        return f"""
🚨 ALERTA DLQ - Mensagem Falhou

ID da Mensagem: {alert['message_id']}
Telefone: {alert.get('phone', 'N/A')}
Erro: {alert['error']}
Tentativas: {alert['retry_count']}
Texto da Mensagem: {alert.get('message_text', 'N/A')}
Timestamp: {alert['timestamp']}

Esta mensagem foi movida para Dead Letter Queue após múltiplas tentativas de processamento.
Verifique o sistema e investigue a causa do erro.
"""

    def _format_email_html(self, alert: Dict[str, Any]) -> str:
        """Formata corpo do email em HTML."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .alert {{ background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 10px 0; }}
        .info {{ margin: 5px 0; }}
        .label {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="alert">
        <h2>🚨 ALERTA DLQ - Mensagem Falhou</h2>
        <div class="info"><span class="label">ID da Mensagem:</span> {alert['message_id']}</div>
        <div class="info"><span class="label">Telefone:</span> {alert.get('phone', 'N/A')}</div>
        <div class="info"><span class="label">Erro:</span> {alert['error']}</div>
        <div class="info"><span class="label">Tentativas:</span> {alert['retry_count']}</div>
        <div class="info"><span class="label">Texto da Mensagem:</span> {alert.get('message_text', 'N/A')}</div>
        <div class="info"><span class="label">Timestamp:</span> {alert['timestamp']}</div>
    </div>
    <p>Esta mensagem foi movida para Dead Letter Queue após múltiplas tentativas de processamento.</p>
    <p>Verifique o sistema e investigue a causa do erro.</p>
</body>
</html>
"""

    async def monitor_dlq(self):
        """Monitora o stream DLQ e envia alertas."""
        self.running = True
        logger.info("[DLQAlerter] Iniciando monitoramento do DLQ")

        last_id = "0"  # Começar do início

        while self.running:
            try:
                # Ler novas mensagens do DLQ
                messages = await self.redis_client.xread(
                    {"stream:dlq": last_id},
                    count=10,
                    block=5000,  # 5 segundos
                )

                if not messages:
                    continue

                for stream, msgs in messages:
                    for msg_id, msg_data in msgs:
                        last_id = msg_id.decode() if isinstance(msg_id, bytes) else msg_id

                        # Deserializar dados
                        data = {}
                        for key, value in msg_data.items():
                            key_str = key.decode() if isinstance(key, bytes) else key
                            value_str = (
                                value.decode() if isinstance(value, bytes) else value
                            )
                            data[key_str] = value_str

                        # Extrair informações
                        original_message_id = data.get("original_message_id", "")
                        error = data.get("error", "Unknown error")
                        message_data = data.get("message_data", {})
                        retry_count = int(data.get("retry_count", 3))

                        # Enviar alerta
                        await self.send_alert(
                            message_id=original_message_id or last_id,
                            error=error,
                            message_data=message_data,
                            retry_count=retry_count,
                        )

            except redis.ConnectionError as e:
                logger.error(f"[DLQAlerter] Conexão Redis perdida: {e}")
                await asyncio.sleep(5)
                await self.connect()

            except asyncio.CancelledError:
                logger.info("[DLQAlerter] Monitor cancelado")
                break

            except Exception as e:
                logger.error(f"[DLQAlerter] Erro no monitor: {e}", exc_info=True)
                await asyncio.sleep(10)

        logger.info("[DLQAlerter] Monitor parado")

    async def start(self):
        """Inicia o monitor em background."""
        if self.running:
            logger.warning("[DLQAlerter] Monitor já está rodando")
            return

        await self.connect()
        self._task = asyncio.create_task(self.monitor_dlq())
        logger.info("[DLQAlerter] Monitor iniciado")

    async def stop(self):
        """Para o monitor."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.disconnect()
        logger.info("[DLQAlerter] Monitor parado")


# Instância global (será inicializada no main.py)
dlq_alerter: Optional[DLQAlerter] = None
