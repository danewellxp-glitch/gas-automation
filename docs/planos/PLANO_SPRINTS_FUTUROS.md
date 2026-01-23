# PLANO DETALHADO - SPRINTS FUTUROS

**Data:** 21 de Janeiro de 2026
**Status Atual:** Sprints 1-5 Completos
**Pontuação Estimada:** 8.0/10 (era 6.5/10)

---

# SPRINT 6: INFRAESTRUTURA E PRODUÇÃO (1-2 semanas)

## Objetivo: Preparar ambiente de produção seguro e monitorado

### 6.1 HTTPS e Certificados SSL 🔴 CRÍTICO

**Tarefa:** Configurar HTTPS com Let's Encrypt

```yaml
# docker-compose.prod.yml - Traefik com HTTPS
traefik:
  command:
    - "--certificatesresolvers.letsencrypt.acme.email=admin@seudominio.com"
    - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    - "--entrypoints.websecure.address=:443"
```

**Arquivos a criar/modificar:**
| Arquivo | Ação |
|---------|------|
| `docker-compose.prod.yml` | Criar versão de produção |
| `traefik/traefik.yml` | Configuração HTTPS |
| `traefik/dynamic.yml` | Rotas com TLS |

**Estimativa:** 4 horas

---

### 6.2 Headers de Segurança 🔴 CRÍTICO

**Tarefa:** Adicionar middleware de segurança no FastAPI

```python
# backend/app/middleware/security.py
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response
```

**Estimativa:** 2 horas

---

### 6.3 Rate Limiting Real 🟠 ALTA

**Tarefa:** Implementar rate limiting por IP/usuário

```python
# backend/app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Em endpoints críticos:
@router.post("/api/auth/token")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...

@router.post("/api/orders")
@limiter.limit("30/minute")
async def create_order(request: Request, ...):
    ...
```

**Estimativa:** 3 horas

---

### 6.4 Monitoramento com Prometheus/Grafana 🟠 ALTA

**Tarefa:** Configurar métricas e dashboards

**Métricas a implementar:**
```python
# backend/app/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Contadores
orders_created = Counter('orders_created_total', 'Total de pedidos criados')
orders_by_status = Counter('orders_by_status', 'Pedidos por status', ['status'])

# Histogramas
request_duration = Histogram('request_duration_seconds', 'Tempo de resposta')
order_processing_time = Histogram('order_processing_seconds', 'Tempo de processamento')

# Gauges
active_websocket_connections = Gauge('websocket_connections', 'Conexões WebSocket ativas')
pending_orders = Gauge('pending_orders', 'Pedidos pendentes')
```

**Dashboards Grafana:**
1. **Overview:** Pedidos/hora, tempo médio de entrega, conversão
2. **Performance:** Latência de API, uso de recursos
3. **Erros:** Taxa de erro, exceções por tipo
4. **Integrações:** Status WAHA, Asaas, latência

**Estimativa:** 6 horas

---

### 6.5 Logging Centralizado 🟠 ALTA

**Tarefa:** Configurar Loki + Promtail para agregação de logs

```yaml
# docker-compose.prod.yml
loki:
  image: grafana/loki:latest
  ports:
    - "3100:3100"
  volumes:
    - ./loki/config.yml:/etc/loki/config.yml

promtail:
  image: grafana/promtail:latest
  volumes:
    - /var/log:/var/log
    - ./promtail/config.yml:/etc/promtail/config.yml
```

**Formato de log estruturado:**
```python
# backend/app/logging_config.py
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
logger.info("order_created", order_id=order.id, customer_id=customer.id)
```

**Estimativa:** 4 horas

---

### 6.6 Backup Automático 🟠 ALTA

**Tarefa:** Configurar backup de PostgreSQL e Redis

```bash
# scripts/backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups

# PostgreSQL
docker exec gas_postgres pg_dump -U gasadmin gas_automation | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Redis
docker exec gas_redis redis-cli BGSAVE
docker cp gas_redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Manter últimos 7 dias
find $BACKUP_DIR -mtime +7 -delete

# Upload para S3/MinIO (opcional)
mc cp $BACKUP_DIR/*.gz minio/backups/
```

**Cron:**
```cron
# Backup diário às 3h
0 3 * * * /opt/gas-automation/scripts/backup.sh
```

**Estimativa:** 3 horas

---

### Entregáveis Sprint 6:
- [ ] HTTPS funcionando em produção
- [ ] Headers de segurança implementados
- [ ] Rate limiting ativo
- [ ] Dashboards Grafana operacionais
- [ ] Logs centralizados no Loki
- [ ] Backups automáticos configurados
- [ ] Runbook de operações documentado

**Estimativa Total Sprint 6:** 22-25 horas

---

# SPRINT 7: MELHORIAS DE UX E MOBILE (2 semanas)

## Objetivo: Melhorar experiência do operador e preparar para mobile

### 7.1 PWA (Progressive Web App) 🟠 ALTA

**Tarefa:** Transformar frontend em PWA para uso em tablets/celulares

```javascript
// frontend/vite.config.js
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Gas Automation',
        short_name: 'GasApp',
        theme_color: '#FF6B00',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
        ]
      }
    })
  ]
})
```

**Estimativa:** 4 horas

---

### 7.2 Notificações Push 🟠 ALTA

**Tarefa:** Implementar notificações para novos pedidos

```javascript
// frontend/src/services/notifications.js
export async function requestNotificationPermission() {
  const permission = await Notification.requestPermission();
  if (permission === 'granted') {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: VAPID_PUBLIC_KEY
    });
    await api.post('/api/push/subscribe', subscription);
  }
}

// Quando receber novo pedido via WebSocket:
function showOrderNotification(order) {
  new Notification('Novo Pedido!', {
    body: `Pedido #${order.order_number} - ${order.product}`,
    icon: '/icon-192.png',
    vibrate: [200, 100, 200]
  });
}
```

**Estimativa:** 6 horas

---

### 7.3 Interface do Entregador 🟠 ALTA

**Tarefa:** Criar dashboard simplificado para entregadores

**Telas necessárias:**
1. **Login:** Simples, apenas telefone + senha
2. **Minhas Entregas:** Lista de pedidos atribuídos
3. **Detalhes da Entrega:** Endereço, cliente, Waze/Maps
4. **Confirmar Entrega:** Botão + foto opcional

```jsx
// frontend/src/pages/driver/DriverDashboard.jsx
function DriverDashboard() {
  const { deliveries } = useDriverDeliveries();

  return (
    <div className="driver-app">
      <header>Olá, {user.name}</header>

      <div className="delivery-list">
        {deliveries.map(d => (
          <DeliveryCard
            key={d.id}
            order={d}
            onNavigate={() => openMaps(d.address)}
            onComplete={() => completeDelivery(d.id)}
          />
        ))}
      </div>

      <StatusToggle /> {/* Disponível / Ocupado / Offline */}
    </div>
  );
}
```

**Estimativa:** 12 horas

---

### 7.4 Som de Notificação 🟡 MÉDIA

**Tarefa:** Tocar som quando novo pedido chegar

```javascript
// frontend/src/hooks/useNotificationSound.js
const notificationSound = new Audio('/sounds/new-order.mp3');

export function useNotificationSound() {
  const playSound = useCallback(() => {
    notificationSound.currentTime = 0;
    notificationSound.play().catch(() => {
      // Autoplay bloqueado - ignorar
    });
  }, []);

  return { playSound };
}

// No WebSocket listener:
useEffect(() => {
  socket.on('new_order', (order) => {
    playSound();
    addOrder(order);
  });
}, []);
```

**Estimativa:** 2 horas

---

### 7.5 Modo Escuro 🟡 MÉDIA

**Tarefa:** Implementar tema escuro para uso noturno

```javascript
// frontend/src/contexts/ThemeContext.jsx
const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [darkMode, setDarkMode] = useState(
    localStorage.getItem('darkMode') === 'true'
  );

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  return (
    <ThemeContext.Provider value={{ darkMode, setDarkMode }}>
      {children}
    </ThemeContext.Provider>
  );
}
```

**Estimativa:** 4 horas

---

### Entregáveis Sprint 7:
- [ ] PWA instalável
- [ ] Notificações push funcionando
- [ ] Dashboard do entregador completo
- [ ] Som de notificação
- [ ] Modo escuro implementado

**Estimativa Total Sprint 7:** 28-32 horas

---

# SPRINT 8: RELATÓRIOS E ANALYTICS (2 semanas)

## Objetivo: Dashboards analíticos para tomada de decisão

### 8.1 Dashboard Administrativo 🟠 ALTA

**Métricas a exibir:**
- Pedidos por dia/semana/mês (gráfico de linha)
- Receita total e média por pedido
- Produtos mais vendidos (gráfico de pizza)
- Bairros com mais pedidos (mapa de calor)
- Tempo médio de entrega
- Taxa de cancelamento
- Clientes novos vs recorrentes

**Estimativa:** 12 horas

---

### 8.2 Relatório de Entregadores 🟠 ALTA

**Métricas por entregador:**
- Entregas realizadas
- Tempo médio de entrega
- Avaliação média (se implementar)
- Km rodados (estimativa)
- Horas trabalhadas

**Estimativa:** 8 horas

---

### 8.3 Exportação de Dados 🟡 MÉDIA

**Formatos:**
- CSV para planilhas
- PDF para relatórios
- Excel para contabilidade

```python
# backend/app/api/reports.py
@router.get("/api/reports/orders/csv")
async def export_orders_csv(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user)
):
    orders = await get_orders_range(start_date, end_date)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Pedido', 'Data', 'Cliente', 'Total', 'Status'])

    for order in orders:
        writer.writerow([
            order.order_number,
            order.created_at.isoformat(),
            order.customer.name,
            order.total_amount,
            order.status
        ])

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pedidos.csv"}
    )
```

**Estimativa:** 6 horas

---

### 8.4 Integração com Google Analytics 🟡 MÉDIA

**Eventos a rastrear:**
- Página visualizada
- Pedido iniciado
- Pedido concluído
- Pagamento realizado
- Erro de API

**Estimativa:** 3 horas

---

### Entregáveis Sprint 8:
- [ ] Dashboard admin com gráficos
- [ ] Relatório de entregadores
- [ ] Exportação CSV/PDF
- [ ] Analytics integrado

**Estimativa Total Sprint 8:** 29-35 horas

---

# SPRINT 9: INTEGRAÇÕES AVANÇADAS (2 semanas)

## Objetivo: Expandir integrações e automações

### 9.1 Integração com Firebird (ERP Legado) 🟠 ALTA

**Tarefa:** Sincronizar clientes e pedidos com sistema legado

```python
# backend/app/services/firebird_sync.py
class FirebirdSyncService:
    async def sync_customer(self, customer: Customer):
        """Sincroniza cliente com Firebird"""
        if customer.firebird_id:
            # Atualizar existente
            await self.firebird.update_customer(customer)
        else:
            # Criar novo e salvar ID
            firebird_id = await self.firebird.create_customer(customer)
            customer.firebird_id = firebird_id
            await self.db.commit()

    async def sync_order(self, order: Order):
        """Sincroniza pedido com Firebird"""
        firebird_order = await self.firebird.create_order({
            'cliente_id': order.customer.firebird_id,
            'produtos': [...],
            'total': order.total_amount,
        })
        order.firebird_order_id = firebird_order['id']
        await self.db.commit()
```

**Estimativa:** 16 horas

---

### 9.2 Webhook de Pagamento Asaas 🟠 ALTA

**Tarefa:** Processar confirmação automática de pagamento

```python
# backend/app/api/webhooks.py
@router.post("/webhooks/asaas")
async def asaas_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    event = payload.get("event")
    payment = payload.get("payment", {})

    if event == "PAYMENT_RECEIVED":
        order = await get_order_by_asaas_id(db, payment["externalReference"])
        if order:
            order.status = OrderStatus.PAID.value
            order.paid_at = datetime.utcnow()
            await db.commit()

            # Notificar cliente via WhatsApp
            await send_whatsapp_message(
                order.customer.phone,
                f"✅ Pagamento confirmado! Pedido #{order.order_number}"
            )

            # Notificar operadores
            await emit_order_update(str(order.id), "paid")

    return {"status": "ok"}
```

**Estimativa:** 8 horas

---

### 9.3 Upload de Imagens para MinIO 🟡 MÉDIA

**Tarefa:** Salvar comprovantes e fotos no MinIO

```python
# backend/app/services/storage.py
from minio import Minio

class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False
        )

    async def upload_payment_proof(self, order_id: str, file: UploadFile) -> str:
        """Upload comprovante de pagamento"""
        filename = f"payments/{order_id}/{file.filename}"
        self.client.put_object(
            "gas-automation",
            filename,
            file.file,
            file.size,
            content_type=file.content_type
        )
        return f"{settings.minio_public_url}/{filename}"
```

**Estimativa:** 6 horas

---

### 9.4 IA para Atendimento (Ollama) 🟡 MÉDIA

**Tarefa:** Melhorar respostas do chatbot com IA local

```python
# backend/app/services/ai_assistant.py
class AIAssistant:
    async def understand_intent(self, message: str) -> dict:
        """Usa Ollama para entender intenção"""
        prompt = f"""
        Analise a mensagem do cliente e retorne JSON:
        - intent: pedido|duvida|reclamacao|outro
        - product: P13|P20|P45|null
        - quantity: number|null
        - sentiment: positivo|neutro|negativo

        Mensagem: {message}
        """

        response = await self.ollama.generate(prompt)
        return json.loads(response)

    async def generate_response(self, context: dict) -> str:
        """Gera resposta personalizada"""
        prompt = f"""
        Você é um assistente de uma distribuidora de gás.
        Cliente: {context['customer_name']}
        Histórico: {context['order_history']}
        Mensagem: {context['message']}

        Responda de forma amigável e objetiva.
        """
        return await self.ollama.generate(prompt)
```

**Estimativa:** 12 horas

---

### Entregáveis Sprint 9:
- [ ] Sincronização Firebird funcionando
- [ ] Webhook Asaas processando pagamentos
- [ ] Upload de imagens no MinIO
- [ ] IA assistente básica

**Estimativa Total Sprint 9:** 42-48 horas

---

# SPRINT 10: ESCALABILIDADE (2 semanas)

## Objetivo: Preparar sistema para alto volume

### 10.1 Cache com Redis 🟠 ALTA

**Implementar cache para:**
- Lista de produtos (TTL: 5 min)
- Dados de cliente (TTL: 1 min)
- Estatísticas do dashboard (TTL: 30 seg)

**Estimativa:** 8 horas

---

### 10.2 Filas com Redis/Celery 🟠 ALTA

**Processar em background:**
- Envio de WhatsApp
- Sincronização Firebird
- Geração de relatórios
- Notificações push

**Estimativa:** 12 horas

---

### 10.3 Múltiplas Instâncias 🟠 ALTA

**Configurar:**
- Load balancer Traefik
- Session stickiness para WebSocket
- Redis como broker de mensagens

**Estimativa:** 8 horas

---

### 10.4 Database Optimizations 🟡 MÉDIA

**Otimizações:**
- Índices compostos
- Particionamento de tabela orders por data
- Connection pooling

**Estimativa:** 6 horas

---

### Entregáveis Sprint 10:
- [ ] Cache Redis implementado
- [ ] Filas Celery funcionando
- [ ] Sistema escalável horizontalmente
- [ ] Database otimizado

**Estimativa Total Sprint 10:** 34-40 horas

---

# CRONOGRAMA RESUMIDO

| Sprint | Foco | Duração | Horas |
|--------|------|---------|-------|
| ~~1~~ | ~~Segurança Crítica~~ | ✅ | ✅ |
| ~~2~~ | ~~Qualidade de Código~~ | ✅ | ✅ |
| ~~3~~ | ~~Testes e Documentação~~ | ✅ | ✅ |
| ~~4~~ | ~~TypeScript e Performance~~ | ✅ | ✅ |
| ~~5~~ | ~~Funcionalidades Incompletas~~ | ✅ | ✅ |
| **6** | Infraestrutura e Produção | 1-2 sem | 22-25h |
| **7** | Melhorias UX e Mobile | 2 sem | 28-32h |
| **8** | Relatórios e Analytics | 2 sem | 29-35h |
| **9** | Integrações Avançadas | 2 sem | 42-48h |
| **10** | Escalabilidade | 2 sem | 34-40h |

**Total Restante:** ~9-10 semanas / ~155-180 horas

---

# PRIORIZAÇÃO RECOMENDADA

## Fazer Primeiro (Sprint 6):
1. HTTPS em produção
2. Backups automáticos
3. Monitoramento básico

## Fazer Depois (Sprint 7-8):
1. PWA para operadores
2. Dashboard do entregador
3. Relatórios básicos

## Fazer Por Último (Sprint 9-10):
1. Integração Firebird
2. IA avançada
3. Escalabilidade

---

**Documento gerado em:** 21/01/2026
**Próxima revisão:** Após Sprint 6
