"""
Metrics Collector - Sistema de Métricas Prometheus
Coleta e expõe métricas do Flow Engine 2.0.

Baseado em: GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md - Parte 7
"""

import logging
from typing import Dict, Optional
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Coletor de métricas para o Flow Engine 2.0.
    
    Métricas coletadas:
    - Mensagens processadas
    - Tempo de processamento
    - Erros
    - Transições de estado
    - Confiança do NLU
    - Taxa de conclusão de pedidos
    - Taxa de escalação para humano
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Inicializa o coletor de métricas.
        
        Args:
            registry: Registry do Prometheus (usa default se None)
        """
        self.registry = registry
        
        # ═══════════════════════════════════════════════════════════════════
        # MÉTRICAS DE MENSAGENS
        # ═══════════════════════════════════════════════════════════════════
        
        self.messages_total = Counter(
            name="flow_engine_messages_total",
            documentation="Total de mensagens processadas",
            labelnames=["status"],  # success, error
            registry=registry,
        )
        
        self.messages_processing_time = Histogram(
            name="flow_engine_processing_time_seconds",
            documentation="Tempo de processamento de mensagens",
            labelnames=["state"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
            registry=registry,
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # MÉTRICAS DE ESTADOS
        # ═══════════════════════════════════════════════════════════════════
        
        self.state_transitions_total = Counter(
            name="flow_engine_state_transitions_total",
            documentation="Total de transições de estado",
            labelnames=["from_state", "to_state"],
            registry=registry,
        )
        
        self.active_conversations = Gauge(
            name="flow_engine_active_conversations",
            documentation="Número de conversas ativas",
            registry=registry,
        )
        
        self.conversations_by_state = Gauge(
            name="flow_engine_conversations_by_state",
            documentation="Conversas por estado",
            labelnames=["state"],
            registry=registry,
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # MÉTRICAS DE NLU
        # ═══════════════════════════════════════════════════════════════════
        
        self.nlu_intent_detections = Counter(
            name="flow_engine_nlu_intent_detections_total",
            documentation="Total de detecções de intenção",
            labelnames=["intent", "layer"],  # layer: keyword, pattern, llm
            registry=registry,
        )
        
        self.nlu_confidence = Histogram(
            name="flow_engine_nlu_confidence",
            documentation="Confiança das detecções do NLU",
            labelnames=["intent"],
            buckets=[0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0],
            registry=registry,
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # MÉTRICAS DE PEDIDOS
        # ═══════════════════════════════════════════════════════════════════
        
        self.orders_created_total = Counter(
            name="flow_engine_orders_created_total",
            documentation="Total de pedidos criados",
            labelnames=["payment_method", "operation_type"],
            registry=registry,
        )
        
        self.orders_abandoned_total = Counter(
            name="flow_engine_orders_abandoned_total",
            documentation="Total de pedidos abandonados",
            labelnames=["last_state"],
            registry=registry,
        )
        
        self.order_completion_rate = Gauge(
            name="flow_engine_order_completion_rate",
            documentation="Taxa de conclusão de pedidos (0-1)",
            registry=registry,
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # MÉTRICAS DE ATENDIMENTO HUMANO
        # ═══════════════════════════════════════════════════════════════════
        
        self.human_escalations_total = Counter(
            name="flow_engine_human_escalations_total",
            documentation="Total de escalações para atendimento humano",
            labelnames=["reason"],  # timeout, error, explicit_request
            registry=registry,
        )
        
        self.human_escalation_rate = Gauge(
            name="flow_engine_human_escalation_rate",
            documentation="Taxa de escalação para humano (0-1)",
            registry=registry,
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # MÉTRICAS DE ERROS
        # ═══════════════════════════════════════════════════════════════════
        
        self.errors_total = Counter(
            name="flow_engine_errors_total",
            documentation="Total de erros",
            labelnames=["error_type", "state"],
            registry=registry,
        )
        
        self.error_rate = Gauge(
            name="flow_engine_error_rate",
            documentation="Taxa de erro (0-1)",
            registry=registry,
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # MÉTRICAS DE FAST-TRACK
        # ═══════════════════════════════════════════════════════════════════
        
        self.fast_track_usage_total = Counter(
            name="flow_engine_fast_track_usage_total",
            documentation="Total de usos de fast-track",
            labelnames=["type"],  # repeat_order, full_order
            registry=registry,
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # INFORMAÇÕES DO SISTEMA
        # ═══════════════════════════════════════════════════════════════════
        
        self.system_info = Info(
            name="flow_engine_system",
            documentation="Informações do sistema",
            registry=registry,
        )
        
        self.system_info.info({
            "version": "2.0.0",
            "engine": "flow_engine_v2",
        })
        
        logger.info("MetricsCollector inicializado")
    
    # ═══════════════════════════════════════════════════════════════════════
    # MÉTODOS DE COLETA
    # ═══════════════════════════════════════════════════════════════════════
    
    def increment_message_count(self, status: str = "success"):
        """Incrementa contador de mensagens."""
        self.messages_total.labels(status=status).inc()
    
    def record_processing_time(self, time_ms: float, state: Optional[str] = None):
        """Registra tempo de processamento."""
        time_seconds = time_ms / 1000.0
        self.messages_processing_time.labels(
            state=state or "unknown"
        ).observe(time_seconds)
    
    def record_state_transition(
        self,
        from_state: Optional[str],
        to_state: Optional[str]
    ):
        """Registra transição de estado."""
        self.state_transitions_total.labels(
            from_state=from_state or "none",
            to_state=to_state or "none"
        ).inc()
    
    def set_active_conversations(self, count: int):
        """Define número de conversas ativas."""
        self.active_conversations.set(count)
    
    def set_conversations_by_state(self, state: str, count: int):
        """Define número de conversas em um estado."""
        self.conversations_by_state.labels(state=state).set(count)
    
    def record_nlu_detection(
        self,
        intent: str,
        layer: str,  # keyword, pattern, llm
    ):
        """Registra detecção de intenção."""
        self.nlu_intent_detections.labels(
            intent=intent,
            layer=layer
        ).inc()
    
    def record_nlu_confidence(self, intent: str, confidence: float):
        """Registra confiança do NLU."""
        self.nlu_confidence.labels(intent=intent).observe(confidence)
    
    def increment_orders_created(
        self,
        payment_method: str,
        operation_type: str
    ):
        """Incrementa contador de pedidos criados."""
        self.orders_created_total.labels(
            payment_method=payment_method,
            operation_type=operation_type
        ).inc()
    
    def increment_orders_abandoned(self, last_state: str):
        """Incrementa contador de pedidos abandonados."""
        self.orders_abandoned_total.labels(last_state=last_state).inc()
    
    def set_order_completion_rate(self, rate: float):
        """Define taxa de conclusão de pedidos."""
        self.order_completion_rate.set(rate)
    
    def increment_human_escalation(self, reason: str):
        """Incrementa contador de escalações para humano."""
        self.human_escalations_total.labels(reason=reason).inc()
    
    def set_human_escalation_rate(self, rate: float):
        """Define taxa de escalação para humano."""
        self.human_escalation_rate.set(rate)
    
    def increment_error_count(
        self,
        error_type: str,
        state: Optional[str] = None
    ):
        """Incrementa contador de erros."""
        self.errors_total.labels(
            error_type=error_type,
            state=state or "unknown"
        ).inc()
    
    def set_error_rate(self, rate: float):
        """Define taxa de erro."""
        self.error_rate.set(rate)
    
    def increment_fast_track_usage(self, fast_track_type: str):
        """Incrementa contador de fast-track."""
        self.fast_track_usage_total.labels(type=fast_track_type).inc()
    
    # ═══════════════════════════════════════════════════════════════════════
    # MÉTODOS DE ANÁLISE
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_summary(self) -> Dict:
        """
        Retorna resumo das métricas atuais.
        
        Returns:
            Dicionário com resumo das métricas
        """
        # Nota: Este método é simplificado
        # Em produção, você consultaria o Prometheus diretamente
        return {
            "system": "flow_engine_v2",
            "version": "2.0.0",
            "status": "operational",
        }


# Singleton do metrics collector
_METRICS_COLLECTOR: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Obtém instância singleton do metrics collector.
    
    Returns:
        MetricsCollector
    """
    global _METRICS_COLLECTOR
    
    if _METRICS_COLLECTOR is None:
        _METRICS_COLLECTOR = MetricsCollector()
    
    return _METRICS_COLLECTOR
