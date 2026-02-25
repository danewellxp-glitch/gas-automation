# Guia de Configuração - Observabilidade Completa

Este guia descreve como configurar e usar o stack completo de observabilidade do Gas Automation System.

## Componentes

1. **Prometheus** - Coleta e armazena métricas
2. **Grafana** - Visualização de métricas e dashboards
3. **Alertmanager** - Gerenciamento de alertas
4. **Loki** - Agregação de logs
5. **Promtail** - Coleta e envio de logs para Loki
6. **Datadog** (opcional) - Integração com Datadog APM
7. **New Relic** (opcional) - Integração com New Relic APM

## Iniciando o Stack

### 1. Iniciar serviços de observabilidade

```bash
docker-compose --profile monitoring up -d
```

Isso iniciará:
- Prometheus (porta 9090)
- Grafana (porta 3002)
- Alertmanager (porta 9093)
- Loki (porta 3100)
- Promtail

### 2. Acessar interfaces

- **Grafana**: http://grafana.localhost:3002 (admin/admin123)
- **Prometheus**: http://prometheus.localhost:9090
- **Alertmanager**: http://alertmanager.localhost:9093
- **Loki**: http://loki.localhost:3100

## Configuração

### Prometheus

Arquivo: `prometheus/prometheus.yml`

- Configura targets para coletar métricas
- Define regras de alerta em `prometheus/alerts/`
- Conecta ao Alertmanager

### Alertmanager

Arquivo: `alertmanager/alertmanager.yml`

- Roteia alertas por severidade
- Configura receivers (webhook, email, Slack, etc)
- Define inibição de alertas

**Configurar notificações:**

1. **Email**: Descomente e configure `smtp_*` no `alertmanager.yml`
2. **Slack**: Configure `slack_api_url` no `alertmanager.yml`
3. **Webhook customizado**: Já configurado para `http://backend:8000/api/alerts/webhook`

### Grafana

**Dashboards provisionados:**
- `stream-metrics.json` - Métricas do Redis Streams

**Datasources provisionados:**
- Prometheus (http://prometheus:9090)
- Loki (http://loki:3100)

### Loki

Arquivo: `loki/loki-config.yml`

- Configura retenção de logs (7 dias por padrão)
- Define limites de ingestão
- Configura compactação

### Promtail

Arquivo: `promtail/promtail-config.yml`

- Coleta logs de containers Docker
- Envia logs estruturados para Loki
- Extrai labels de logs (message_id, trace_id, etc)

## Integrações Opcionais

### Datadog

1. Instalar SDK:
```bash
pip install datadog ddtrace
```

2. Configurar no `.env`:
```bash
DATADOG_API_KEY=your_api_key
DATADOG_APP_KEY=your_app_key  # Opcional
DATADOG_HOST=localhost
DATADOG_PORT=8125
```

3. Inicializar no código:
```python
from app.integrations.datadog import datadog_integration

datadog_integration.initialize(
    api_key=settings.datadog_api_key,
    env=settings.environment,
    service="gas-automation",
)
```

### New Relic

1. Instalar SDK:
```bash
pip install newrelic
```

2. Configurar no `.env`:
```bash
NEW_RELIC_LICENSE_KEY=your_license_key
NEW_RELIC_APP_NAME=Gas Automation
NEW_RELIC_ENVIRONMENT=production
```

3. Inicializar no código:
```python
from app.integrations.newrelic import newrelic_integration

newrelic_integration.initialize(
    license_key=settings.newrelic_license_key,
    app_name="Gas Automation",
    environment=settings.environment,
)
```

## Dashboards Grafana

### Redis Streams Dashboard

Visualiza:
- Mensagens adicionadas ao stream
- Taxa de sucesso vs erro
- Lag do stream (mensagens pendentes)
- Tempo de processamento (p50, p95, p99)
- Mensagens na DLQ
- Distribuição de retries
- Taxa de erro

**Acessar**: Grafana → Dashboards → "Redis Streams - Message Processing"

## Alertas Configurados

### Alertas Críticos

1. **StreamConsumerDown** - Consumer parado por > 2min
2. **MessagesInDLQ** - Mensagens na DLQ
3. **RedisDown** - Redis inacessível
4. **PostgreSQLDown** - PostgreSQL inacessível
5. **WAHASessionDown** - Sessão WhatsApp desconectada

### Alertas de Aviso

1. **HighStreamLag** - Lag > 100 mensagens por > 5min
2. **HighStreamErrorRate** - Taxa de erro > 10%
3. **HighRetryRate** - Muitos retries
4. **HighProcessingTime** - p95 > 10s

## Logs Estruturados

Logs são coletados pelo Promtail e enviados para Loki com labels:
- `message_id` - ID da mensagem WhatsApp
- `trace_id` - ID de rastreamento
- `phone` - Número de telefone
- `level` - Nível do log (INFO, ERROR, etc)
- `module` - Módulo que gerou o log

**Query exemplo no Grafana:**
```
{job="backend"} |= "message_id=ABC123"
```

## Monitoramento de Saúde

Endpoint `/health` verifica:
- Redis
- PostgreSQL
- Stream Consumer
- DLQ Alerter

## Troubleshooting

### Prometheus não coleta métricas

1. Verificar se backend está expondo `/metrics`
2. Verificar conectividade: `curl http://backend:8000/metrics`
3. Verificar logs: `docker logs gas_prometheus`

### Alertmanager não envia alertas

1. Verificar configuração em `alertmanager/alertmanager.yml`
2. Verificar conectividade com receivers
3. Verificar logs: `docker logs gas_alertmanager`

### Loki não recebe logs

1. Verificar se Promtail está rodando
2. Verificar configuração em `promtail/promtail-config.yml`
3. Verificar logs: `docker logs gas_promtail`

### Grafana não mostra dados

1. Verificar datasources em Grafana → Configuration → Data Sources
2. Testar query no Prometheus diretamente
3. Verificar permissões de acesso

## Próximos Passos

1. Configurar notificações (email/Slack) no Alertmanager
2. Criar dashboards customizados no Grafana
3. Configurar alertas adicionais conforme necessário
4. Integrar com Datadog/New Relic se necessário
5. Configurar retenção de logs conforme política da empresa
