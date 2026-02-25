"""
API para receber alertas do Prometheus Alertmanager.
"""

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.utils.structured_logging import get_structured_logger

logger = get_structured_logger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


class Alert(BaseModel):
    """Modelo de alerta do Alertmanager."""
    status: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: str
    endsAt: Optional[str] = None
    generatorURL: str = ""


class AlertmanagerWebhook(BaseModel):
    """Payload do webhook do Alertmanager."""
    version: str
    groupKey: str
    status: str
    receiver: str
    groupLabels: Dict[str, str]
    commonLabels: Dict[str, str]
    commonAnnotations: Dict[str, str]
    externalURL: str
    alerts: List[Alert]


@router.post("/webhook")
async def alertmanager_webhook(
    payload: AlertmanagerWebhook,
    request: Request,
):
    """
    Recebe alertas do Prometheus Alertmanager.
    
    Este endpoint é chamado pelo Alertmanager quando alertas são disparados.
    """
    try:
        logger.info(
            f"Alerta recebido do Alertmanager: status={payload.status} "
            f"receiver={payload.receiver} alerts={len(payload.alerts)}",
            extra={
                "alert_status": payload.status,
                "receiver": payload.receiver,
                "alert_count": len(payload.alerts),
            }
        )

        # Processar cada alerta
        for alert in payload.alerts:
            alert_name = alert.labels.get("alertname", "unknown")
            severity = alert.labels.get("severity", "unknown")
            component = alert.labels.get("component", "unknown")
            
            logger.warning(
                f"Alerta: {alert_name} - {alert.annotations.get('summary', 'No summary')}",
                extra={
                    "alert_name": alert_name,
                    "severity": severity,
                    "component": component,
                    "status": alert.status,
                    "summary": alert.annotations.get("summary"),
                    "description": alert.annotations.get("description"),
                }
            )

            # Enviar para DLQ Alerter se for alerta de DLQ
            if component == "dlq" and alert.status == "firing":
                try:
                    from app.services.dlq_alerter import dlq_alerter
                    if dlq_alerter:
                        # O DLQ Alerter já monitora o stream, mas podemos logar aqui
                        logger.error(
                            f"Alerta DLQ disparado: {alert_name}",
                            extra={
                                "alert_name": alert_name,
                                "alert_labels": alert.labels,
                                "alert_annotations": alert.annotations,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Erro ao processar alerta DLQ: {e}")

        return {"status": "received", "alerts_processed": len(payload.alerts)}

    except Exception as e:
        logger.error(f"Erro ao processar webhook do Alertmanager: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
