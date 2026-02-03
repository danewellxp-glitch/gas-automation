# Sprints: Melhorias Dashboard do Dono

## Visao Geral

Organizacao das melhorias solicitadas em 4 sprints, ordenadas do menor para o maior risco de quebra:

| Sprint | Descricao | Risco | Estimativa |
|--------|-----------|-------|------------|
| C1 | Metricas de Clientes (Recorrentes/Novos) | Baixo | Frontend + API |
| C2 | Remover Inadimplencia + Metricas de Peso (kg) | Medio | Schema + Migration |
| C3 | Pedidos por Estabelecimento/Unidade | Medio | Novo modelo |
| C4 | IA para Previsoes de Vendas (WhatsApp) | Medio | Novo servico |

## Estado Atual do Repositorio

### Backend
- **API Owner Dashboard**: `backend/app/api/owner_dashboard.py`
  - Endpoint: `GET /owner/dashboard?period=day|week|month`
  - Retorna: `CustomerMetrics`, `FinancialBreakdown`, `BairroMetrics`, etc.
  - Ja tem: `repeat_customers_count`, `new_customers_count`, `repeat_rate`, `top_customers`

### Models
- **Product** (`backend/app/models/product.py`): Ja tem `weight_kg: Numeric(5,2)` ✓
- **Order** (`backend/app/models/order.py`): NAO tem campo de peso total
- **OrderItem** (`backend/app/models/order.py`): NAO tem snapshot de peso

### Frontend
- **OwnerDashboard.jsx**: 8 secoes (Dashboard, Financeiro, Operacao, Performance, Clientes, Relatorios, WhatsApp, Config)
- **CustomersView.jsx**: Usa `owner/dashboard?period=month`, mostra top_customers, repeat_rate
- **FinancialView.jsx**: Tem secao "Inadimplencia" (linhas 212-242) que sera removida

---

## Sprint C1: Metricas de Clientes (BAIXO RISCO)

### Objetivo
Melhorar visualizacao de clientes recorrentes vs novos com tabelas clicaveis ordenadas por volume de compra.

### Estado Atual
- `CustomersView.jsx` ja exibe: total ativos, novos hoje/mes, top 5 por receita
- `FinancialBreakdown` tem: `repeat_customers_count`, `new_customers_count`, `repeat_rate`
- Backend ja categoriza: novo (1 pedido no periodo) vs recorrente (2+ pedidos)

### Mudancas Necessarias

#### Backend (`backend/app/api/owner_dashboard.py`)

**Novo endpoint para lista detalhada (adicionar ao arquivo existente):**
```python
@router.get("/customers/detailed")
async def get_customers_detailed(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    period: str = Query("month", regex="^(week|month|year)$"),
    customer_type: str = Query("all", regex="^(all|new|recurring)$"),
    order_by: str = Query("total_spent", regex="^(total_spent|order_count|last_order)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Lista clientes com filtro por tipo e ordenacao.
    Clicavel a partir dos cards do dashboard.
    """
    _require_owner(current_user)
    # Calcular data inicial do periodo
    # Buscar clientes com agregacoes
    # Filtrar por tipo (new = 1 pedido no periodo, recurring = 2+ pedidos)
    # Ordenar e paginar
```

**Response schema:**
```python
class CustomerDetailedResponse(BaseModel):
    customer_id: str
    name: str
    phone: str
    customer_type: str  # "new" | "recurring"
    total_orders: int
    total_spent: Decimal
    last_order_date: datetime
    first_order_date: datetime
    average_order_value: Decimal
```

#### Frontend (`frontend/src/pages/owner/dashboard/`)

**1. Modificar cards para serem clicaveis:**
```jsx
// CustomersView.jsx
<Card
  onClick={() => setShowDetailModal('new')}
  sx={{ cursor: 'pointer', '&:hover': { boxShadow: 4 } }}
>
  <Typography>Novos Clientes</Typography>
  <Typography variant="h4">{newCustomers}</Typography>
</Card>

<Card onClick={() => setShowDetailModal('recurring')}>
  <Typography>Clientes Recorrentes</Typography>
  <Typography variant="h4">{recurringCustomers}</Typography>
</Card>
```

**2. Novo componente modal/drawer:**
```jsx
// CustomerDetailTable.jsx
function CustomerDetailTable({ type, onClose }) {
  const { data, isLoading } = useQuery(
    ['customers-detailed', type],
    () => api.get(`/analytics/customers/detailed?customer_type=${type}&order_by=total_spent`)
  );

  return (
    <DataGrid
      columns={[
        { field: 'name', headerName: 'Nome' },
        { field: 'phone', headerName: 'Telefone' },
        { field: 'total_orders', headerName: 'Pedidos' },
        { field: 'total_spent', headerName: 'Total Gasto' },
        { field: 'last_order_date', headerName: 'Ultimo Pedido' },
      ]}
      rows={data}
      sortModel={[{ field: 'total_spent', sort: 'desc' }]}
    />
  );
}
```

### Arquivos a Modificar
| Arquivo | Mudanca |
|---------|---------|
| `backend/app/api/owner_dashboard.py` | Novo endpoint `/owner/customers/detailed` |
| `frontend/src/components/owner/CustomersView.jsx` | Cards clicaveis + modal |
| `frontend/src/components/owner/CustomerDetailTable.jsx` | Novo componente (criar) |

### Testes
```bash
pytest tests/test_api/test_owner_dashboard.py -k "customers_detailed" -v
```

---

## Sprint C2: Peso (kg) e Remover Inadimplencia (MEDIO RISCO)

### Objetivo
1. Rastrear peso (kg) vendido em cada pedido
2. Exibir metricas de kg no dashboard
3. Remover secao de inadimplencia

### Estado Atual - Peso
- `Product` ja tem campo `weight_kg: Numeric(5,2)`
- `OrderItem` NAO snapshot o peso - apenas: `product_code`, `product_name`, `quantity`, `unit_price`, `subtotal`
- `CargaVeiculo` rastreia: `qtd_saida`, `qtd_retorno_cheio`, `qtd_retorno_vazio`, `qtd_vendida`

### Mudancas Necessarias

#### 1. Migration: Adicionar peso no OrderItem

**Nova migration Alembic:**
```python
# alembic/versions/xxx_add_weight_to_order_item.py
def upgrade():
    op.add_column('order_items', sa.Column('weight_kg_unit', sa.Numeric(5, 2), nullable=True))
    op.add_column('order_items', sa.Column('weight_kg_total', sa.Numeric(8, 2), nullable=True))
    op.add_column('orders', sa.Column('total_weight_kg', sa.Numeric(10, 2), nullable=True))

def downgrade():
    op.drop_column('order_items', 'weight_kg_unit')
    op.drop_column('order_items', 'weight_kg_total')
    op.drop_column('orders', 'total_weight_kg')
```

#### 2. Model: Atualizar OrderItem

```python
# backend/app/models/order.py
class OrderItem(Base):
    # ... campos existentes ...

    # NOVOS campos de peso
    weight_kg_unit = Column(Numeric(5, 2), nullable=True, comment="Peso unitario em kg (snapshot do produto)")
    weight_kg_total = Column(Numeric(8, 2), nullable=True, comment="Peso total = weight_kg_unit * quantity")

class Order(Base):
    # ... campos existentes ...

    # NOVO campo
    total_weight_kg = Column(Numeric(10, 2), nullable=True, comment="Soma dos pesos de todos os itens")
```

#### 3. Service: Calcular peso na criacao do pedido

```python
# backend/app/services/order_service.py
async def create_order(self, db, customer_id, items, ...):
    order_items = []
    total_weight = Decimal('0')

    for item in items:
        product = await self._get_product(db, item.product_id)

        weight_unit = product.weight_kg or Decimal('0')
        weight_total = weight_unit * item.quantity
        total_weight += weight_total

        order_item = OrderItem(
            product_id=product.id,
            quantity=item.quantity,
            unit_price=product.price,
            weight_kg_unit=weight_unit,      # NOVO
            weight_kg_total=weight_total,    # NOVO
        )
        order_items.append(order_item)

    order = Order(
        customer_id=customer_id,
        items=order_items,
        total_weight_kg=total_weight,  # NOVO
    )
```

#### 4. Backend: Adicionar metricas de peso no owner_dashboard.py

```python
# backend/app/api/owner_dashboard.py - adicionar ao OwnerDashboardResponse

class WeightMetrics(BaseModel):
    """Metricas de peso (kg)."""
    total_kg_sold: float
    average_kg_per_order: float
    kg_by_product: list[dict[str, Any]]

# No endpoint get_owner_dashboard(), adicionar:

# ==================== WEIGHT METRICS ====================
weight_stmt = (
    select(
        func.coalesce(func.sum(OrderItem.weight_kg_total), 0).label("total_kg"),
    )
    .join(Order, Order.id == OrderItem.order_id)
    .where(
        and_(
            Order.created_at >= month_start,
            Order.status != OrderStatus.CANCELLED.value,
        )
    )
)
total_kg = float((await session.execute(weight_stmt)).scalar() or 0)
avg_kg = total_kg / orders_today_count if orders_today_count > 0 else 0.0
```

#### 5. Frontend: Adicionar metricas de peso no OperationalView

```jsx
// frontend/src/components/owner/OperationalView.jsx
// Adicionar secao de peso usando dados do dashboardData

{/* Metricas de Peso */}
<div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
  <h2 className="mb-4 text-lg font-semibold text-gray-900">Peso Vendido (kg)</h2>
  <div className="grid grid-cols-2 gap-4">
    <div>
      <p className="text-sm text-gray-600">Total kg Vendido</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">
        {dashboardData?.weight_metrics?.total_kg_sold?.toFixed(1) || 0} kg
      </p>
    </div>
    <div>
      <p className="text-sm text-gray-600">Media por Pedido</p>
      <p className="mt-1 text-2xl font-bold text-blue-600">
        {dashboardData?.weight_metrics?.average_kg_per_order?.toFixed(1) || 0} kg
      </p>
    </div>
  </div>
</div>
```

#### 6. Remover Inadimplencia

```jsx
// frontend/src/components/owner/FinancialView.jsx
// REMOVER linhas 212-242 (secao "Inadimplencia")
// Manter apenas: Clientes Novos e Clientes Recorrentes (que ja estao em CustomersView)
```

### Arquivos a Modificar/Criar
| Arquivo | Mudanca |
|---------|---------|
| `backend/alembic/versions/xxx_add_weight.py` | Nova migration (criar) |
| `backend/app/models/order.py` | Campos `weight_kg_unit`, `weight_kg_total` em OrderItem, `total_weight_kg` em Order |
| `backend/app/services/order_service.py` | Calcular peso na criacao do pedido |
| `backend/app/api/owner_dashboard.py` | Adicionar `WeightMetrics` ao response |
| `frontend/src/components/owner/OperationalView.jsx` | Adicionar secao de metricas de peso |
| `frontend/src/components/owner/FinancialView.jsx` | Remover secao "Inadimplencia" (linhas 212-242) |

### Migracao de Dados Existentes
```sql
-- Script para preencher peso em pedidos antigos
UPDATE order_items oi
SET weight_kg_unit = p.weight_kg,
    weight_kg_total = p.weight_kg * oi.quantity
FROM products p
WHERE oi.product_id = p.id
  AND oi.weight_kg_unit IS NULL;

UPDATE orders o
SET total_weight_kg = (
    SELECT COALESCE(SUM(weight_kg_total), 0)
    FROM order_items
    WHERE order_id = o.id
)
WHERE total_weight_kg IS NULL;
```

### Testes
```bash
pytest tests/test_services/test_order_service.py -k "weight" -v
pytest tests/test_api/test_analytics.py -k "weight_metrics" -v
```

---

## Sprint C3: Pedidos por Estabelecimento/Unidade (MEDIO RISCO)

### Objetivo
Permitir visualizar pedidos agrupados por estabelecimento (filial/unidade).

### Estado Atual
- Nao existe modelo `Establishment` formal
- Pedidos usam `bairro` como agrupamento geografico
- `Address` tem `bairro`, `city`, etc.

### Opcoes de Implementacao

#### Opcao A: Usar bairro como "unidade" (RECOMENDADO - menor risco)
- Sem mudancas no schema
- Agrupar pedidos por bairro do cliente
- Dashboard filtra por bairro

#### Opcao B: Criar modelo Establishment (maior flexibilidade)
- Nova tabela `establishments`
- Relacionar `Order` com `establishment_id`
- Permite multiplas filiais da empresa

### Implementacao Opcao A (Recomendada)

#### Backend: Ja existe! (orders_by_bairro em owner_dashboard.py)

O endpoint `GET /owner/dashboard` ja retorna `orders_by_bairro` com:
- `bairro`, `orders`, `revenue`, `cancelled`, `avg_delivery_time`

**Apenas adicionar `total_weight_kg` ao agrupamento por bairro (apos Sprint C2):**

```python
# backend/app/api/owner_dashboard.py - modificar query orders_by_bairro_stmt
orders_by_bairro_stmt = (
    select(
        Order.delivery_bairro,
        func.count(Order.id).label("orders"),
        func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        func.coalesce(func.sum(Order.total_weight_kg), 0).label("total_kg"),  # NOVO
        func.sum(case((Order.status == OrderStatus.CANCELLED.value, 1), else_=0)).label("cancelled"),
    )
    ...
)
```

#### Frontend: Tabela/Grafico por Unidade

```jsx
// frontend/src/pages/owner/dashboard/LocationMetricsView.jsx
function LocationMetricsView() {
  const { data } = useQuery(['orders-by-location'], ...);

  return (
    <>
      <Typography variant="h6">Pedidos por Bairro/Unidade</Typography>
      <DataGrid
        columns={[
          { field: 'bairro', headerName: 'Bairro' },
          { field: 'order_count', headerName: 'Pedidos' },
          { field: 'total_revenue', headerName: 'Faturamento' },
          { field: 'total_kg', headerName: 'kg Vendido' },
        ]}
        rows={data}
      />
      <PieChart data={data} dataKey="total_revenue" nameKey="bairro" />
    </>
  );
}
```

### Implementacao Opcao B (Caso necessario no futuro)

#### Novo modelo Establishment

```python
# backend/app/models/establishment.py
class Establishment(Base):
    __tablename__ = "establishments"

    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True)  # Ex: "FILIAL-01"
    address = Column(String(200))
    city = Column(String(100))
    is_active = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="establishment")

# Em Order:
class Order(Base):
    establishment_id = Column(UUID, ForeignKey("establishments.id"), nullable=True)
    establishment = relationship("Establishment", back_populates="orders")
```

### Arquivos a Modificar
| Arquivo | Mudanca |
|---------|---------|
| `backend/app/api/owner_dashboard.py` | Adicionar `total_kg` ao `OrdersByBairro` |
| `frontend/src/components/owner/OperationalView.jsx` | Melhorar tabela de bairros com kg |

**Nota**: A maior parte ja existe! `orders_by_bairro` ja retorna dados por bairro.
Apenas adicionar a coluna de peso (kg) apos Sprint C2.

---

## Sprint C4: IA para Previsoes de Vendas - WhatsApp (MEDIO RISCO)

### Objetivo
Integrar IA para gerar insights e previsoes de vendas baseado no historico de conversas WhatsApp.

### Arquitetura Proposta

```
[WhatsApp Messages] -> [Message Store] -> [AI Analysis Service]
                                                  |
                                                  v
                                         [Predictions API]
                                                  |
                                                  v
                                         [Dashboard Widget]
```

### Componentes

#### 1. Armazenar mensagens para analise

```python
# backend/app/models/whatsapp.py
class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(UUID, primary_key=True)
    phone = Column(String(20), index=True)
    direction = Column(String(10))  # "inbound" | "outbound"
    content = Column(Text)
    message_type = Column(String(20))  # "text", "order", "question", etc
    sentiment = Column(String(20), nullable=True)  # "positive", "neutral", "negative"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    customer_id = Column(UUID, ForeignKey("customers.id"), nullable=True)
    order_id = Column(UUID, ForeignKey("orders.id"), nullable=True)
```

#### 2. Servico de Analise IA

```python
# backend/app/services/ai_analytics_service.py
from anthropic import Anthropic

class AIAnalyticsService:
    def __init__(self):
        self.client = Anthropic()

    async def analyze_sales_patterns(self, messages: List[dict], orders: List[dict]) -> dict:
        """
        Analisa padroes de venda baseado em conversas e pedidos.
        """
        prompt = f"""
        Analise os seguintes dados de vendas via WhatsApp:

        Ultimas {len(messages)} conversas:
        {self._format_messages(messages)}

        Ultimos {len(orders)} pedidos:
        {self._format_orders(orders)}

        Forneca:
        1. Tendencias de demanda (aumentando/diminuindo)
        2. Produtos mais solicitados
        3. Horarios de pico
        4. Previsao para proxima semana
        5. Sugestoes para aumentar vendas

        Responda em JSON.
        """

        response = await self.client.messages.create(
            model="claude-3-haiku-20240307",  # Modelo rapido para analytics
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        return json.loads(response.content[0].text)

    async def get_sales_prediction(self, historical_data: dict) -> dict:
        """
        Previsao de vendas para proximos dias.
        """
        # Usar dados historicos para previsao
        # Considerar: dia da semana, clima, eventos, etc
        pass
```

#### 3. API Endpoint

```python
# backend/app/api/analytics.py
@router.get("/ai-insights")
async def get_ai_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Insights gerados por IA baseado em dados de WhatsApp.
    """
    # Buscar ultimas mensagens e pedidos
    messages = await get_recent_messages(db, days=30)
    orders = await get_recent_orders(db, days=30)

    # Gerar insights
    ai_service = AIAnalyticsService()
    insights = await ai_service.analyze_sales_patterns(messages, orders)

    return {
        "generated_at": datetime.utcnow(),
        "insights": insights,
        "predictions": await ai_service.get_sales_prediction(orders),
    }
```

#### 4. Frontend Widget

```jsx
// frontend/src/pages/owner/dashboard/AIInsightsWidget.jsx
function AIInsightsWidget() {
  const { data, isLoading } = useQuery(
    ['ai-insights'],
    () => api.get('/analytics/ai-insights'),
    { staleTime: 1000 * 60 * 30 }  // Cache 30 min
  );

  if (isLoading) return <Skeleton />;

  return (
    <Card>
      <CardHeader title="Insights IA (WhatsApp)" />
      <CardContent>
        <Typography variant="subtitle2">Tendencia de Demanda</Typography>
        <Chip
          label={data.insights.demand_trend}
          color={data.insights.demand_trend === 'increasing' ? 'success' : 'warning'}
        />

        <Typography variant="subtitle2" sx={{ mt: 2 }}>Previsao Proxima Semana</Typography>
        <Typography>{data.predictions.next_week_estimate} pedidos estimados</Typography>

        <Typography variant="subtitle2" sx={{ mt: 2 }}>Sugestoes</Typography>
        <List>
          {data.insights.suggestions.map((s, i) => (
            <ListItem key={i}><ListItemText primary={s} /></ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
}
```

### Consideracoes de Custo
- Usar Claude Haiku para analises (mais barato)
- Cachear resultados por 30 min
- Limitar analise a ultimos 30 dias
- Batch processing diario ao inves de tempo real

### Arquivos a Criar/Modificar
| Arquivo | Mudanca |
|---------|---------|
| `backend/app/models/whatsapp.py` | Modelo WhatsAppMessage (criar) |
| `backend/app/services/ai_analytics_service.py` | Servico IA (criar) |
| `backend/app/api/owner_dashboard.py` | Endpoint `/owner/ai-insights` |
| `frontend/src/components/owner/AIInsightsWidget.jsx` | Widget (criar) |
| `frontend/src/components/owner/DashboardOverview.jsx` | Adicionar AIInsightsWidget |
| `backend/app/config.py` | Config `anthropic_api_key` |
| `backend/alembic/versions/xxx_whatsapp_messages.py` | Migration (criar) |

---

## Ordem de Execucao Recomendada

```
Sprint C1 (1-2 dias)
    |
    v
Sprint C2 (2-3 dias) - Migration requer deploy coordenado
    |
    v
Sprint C3 (1-2 dias) - Depende de C2 para metricas de kg
    |
    v
Sprint C4 (3-4 dias) - Independente, pode ser paralelo
```

## Riscos e Mitigacoes

| Risco | Mitigacao |
|-------|-----------|
| Migration de peso quebra pedidos existentes | Script de backfill, campos nullable |
| IA gera insights incorretos | Disclaimer "gerado por IA", revisao humana |
| Performance dashboard com muitos dados | Paginacao, cache Redis, queries otimizadas |
| Custo API Anthropic | Rate limit, cache agressivo, Haiku |

## Testes Obrigatorios Antes de Deploy

```bash
# Rodar todos os testes
pytest tests/ -v

# Testes especificos por sprint
pytest tests/test_api/test_owner_dashboard.py -v
pytest tests/test_services/test_order_service.py -v

# Verificar migrations
alembic upgrade head --sql  # Ver SQL gerado antes de aplicar

# Testar em staging
docker-compose -f docker-compose.staging.yml up
```

## Verificacao Manual Por Sprint

```bash
# Sprint C1: Testar endpoint de clientes detalhados
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/owner/customers/detailed?customer_type=recurring"

# Sprint C2: Verificar peso no pedido (apos migration)
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/owner/dashboard?period=month" | jq '.weight_metrics'

# Sprint C3: Verificar kg por bairro
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/owner/dashboard?period=month" | jq '.orders_by_bairro'

# Sprint C4: Testar insights IA
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/owner/ai-insights"
```

---

## Notas Importantes

1. **Sprint C1 e muito segura** - apenas adiciona endpoint e componentes
2. **Sprint C2 requer migration** - testar backfill em staging primeiro
3. **Sprint C3 ja esta parcialmente pronta** - `orders_by_bairro` existe
4. **Sprint C4 pode rodar em paralelo** - independente das outras
