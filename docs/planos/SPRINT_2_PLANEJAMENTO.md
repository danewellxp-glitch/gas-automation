# SPRINT 2 - QUALIDADE DE CODIGO E CONSISTENCIA DE DADOS

**Data de Inicio:** 2026-01-22
**Duracao Estimada:** 5-7 dias
**Prioridade:** ALTA
**Prerequisito:** Sprint 1 Finalizado

---

## OBJETIVO

Melhorar a qualidade do codigo, garantir consistencia de dados e corrigir problemas de logica de negocio que podem causar inconsistencias no sistema.

---

## RESUMO EXECUTIVO

| Categoria | Quantidade | Prioridade |
|-----------|------------|------------|
| Backend - Logica | 6 | ALTA |
| Backend - Validacoes | 8 | ALTA |
| Frontend - Error Handling | 5 | MEDIA |
| Frontend - UX | 4 | MEDIA |
| Infra/Docker | 3 | MEDIA |
| **TOTAL** | **26** | - |

---

## PARTE 1: BACKEND - CORRECOES DE LOGICA (Prioridade ALTA)

### 1.1 Validacao de Bairro em Pedidos
**Arquivo:** `backend/app/api/orders.py`
**Problema:** Aceita qualquer bairro, mas config define bairros suportados
**Impacto:** Pedidos de areas nao atendidas

**Solucao:**
```python
from app.config import settings

if order.delivery_bairro and order.delivery_bairro not in settings.supported_bairros:
    raise HTTPException(
        status_code=400,
        detail=f"Nao atendemos o bairro: {order.delivery_bairro}. "
               f"Bairros disponiveis: {', '.join(settings.supported_bairros)}"
    )
```

**Teste:**
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"delivery_bairro": "Bairro Inexistente", ...}'
# Deve retornar 400
```

---

### 1.2 Constraint de Preco Positivo em Produtos
**Arquivo:** `backend/app/models/product.py`
**Problema:** Sem validacao de preco > 0
**Impacto:** Pedidos com valor negativo

**Solucao:**
```python
from sqlalchemy import CheckConstraint

class Product(Base):
    __tablename__ = "products"

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
    )
```

**Migration:**
```sql
ALTER TABLE products ADD CONSTRAINT check_price_positive CHECK (price > 0);
```

---

### 1.3 Validacao de Estoque Antes de Criar Pedido
**Arquivo:** `backend/app/api/orders.py`
**Problema:** Permite quantidade ate 99, mas nao valida estoque
**Impacto:** Vender mais que o disponivel

**Solucao:**
```python
async def create_order(data: OrderCreate, db: AsyncSession):
    # Validar estoque de cada item
    for item in data.items:
        product = await db.execute(
            select(Product).where(Product.code == item.product_code)
        )
        product = product.scalar_one_or_none()

        if not product:
            raise HTTPException(400, f"Produto {item.product_code} nao encontrado")

        if product.stock_quantity is not None and item.quantity > product.stock_quantity:
            raise HTTPException(
                400,
                f"Estoque insuficiente de {product.name}. "
                f"Disponivel: {product.stock_quantity}, Solicitado: {item.quantity}"
            )

    # Continuar criacao do pedido...
```

---

### 1.4 Customer Address com Schema Definido
**Arquivo:** `backend/app/schemas/customer.py`
**Problema:** Qualquer estrutura JSON aceita no address
**Impacto:** Dados inconsistentes de endereco

**Solucao:**
```python
from pydantic import BaseModel, Field
from typing import Optional

class AddressSchema(BaseModel):
    street: str = Field(..., min_length=3, max_length=200)
    number: str = Field(..., min_length=1, max_length=20)
    complement: Optional[str] = Field(None, max_length=100)
    bairro: str = Field(..., min_length=2, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)  # UF
    zipcode: Optional[str] = Field(None, pattern=r'^\d{8}$')
    reference: Optional[str] = Field(None, max_length=200)

class CustomerBase(BaseSchema):
    # ... outros campos
    address: Optional[AddressSchema] = None
```

---

### 1.5 Impedir Driver Aceitar Multiplas Entregas
**Arquivo:** `backend/app/api/drivers.py`
**Problema:** Nada impede aceitar 2+ deliveries simultaneas
**Impacto:** Driver sobrecarregado, atrasos

**Solucao:**
```python
@router.post("/{driver_id}/accept-delivery/{delivery_id}")
async def accept_delivery(
    driver_id: UUID,
    delivery_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar entregas ativas
    active_deliveries = await db.execute(
        select(Delivery).where(
            Delivery.driver_id == driver_id,
            Delivery.status.in_(['assigned', 'picked_up', 'in_transit'])
        )
    )

    active_count = len(active_deliveries.scalars().all())
    MAX_ACTIVE_DELIVERIES = 2  # Configuravel

    if active_count >= MAX_ACTIVE_DELIVERIES:
        raise HTTPException(
            400,
            f"Driver ja possui {active_count} entregas ativas. "
            f"Maximo permitido: {MAX_ACTIVE_DELIVERIES}"
        )

    # Continuar aceitacao...
```

---

### 1.6 Relatorios Financeiros com Dados Reais
**Arquivo:** `backend/app/main.py` (linha 445-515)
**Problema:** `/api/reports/financial` retorna dados mock
**Impacto:** Owner toma decisoes em dados falsos

**Solucao:**
```python
@app.get("/api/reports/financial")
async def get_financial_report(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar permissao
    if current_user.role not in ['owner', 'admin']:
        raise HTTPException(403, "Sem permissao para acessar relatorios financeiros")

    # Datas padrao: ultimos 30 dias
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Buscar dados reais
    result = await db.execute(text("""
        SELECT
            COUNT(*) as total_orders,
            COALESCE(SUM(total_amount), 0) as total_revenue,
            COALESCE(AVG(total_amount), 0) as average_ticket,
            COUNT(CASE WHEN status = 'delivered' THEN 1 END) as completed_orders,
            COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_orders
        FROM orders
        WHERE created_at::date BETWEEN :start_date AND :end_date
    """), {"start_date": start_date, "end_date": end_date})

    stats = result.mappings().first()

    return {
        "period": {"start": start_date, "end": end_date},
        "total_orders": stats["total_orders"],
        "total_revenue": float(stats["total_revenue"]),
        "average_ticket": float(stats["average_ticket"]),
        "completed_orders": stats["completed_orders"],
        "cancelled_orders": stats["cancelled_orders"],
        "completion_rate": (
            stats["completed_orders"] / stats["total_orders"] * 100
            if stats["total_orders"] > 0 else 0
        )
    }
```

---

## PARTE 2: BACKEND - VALIDACOES (Prioridade ALTA)

### 2.1 Soft Delete em Modelos Principais
**Arquivos:** `backend/app/models/*.py`
**Problema:** DELETE fisico perde historico
**Impacto:** Problemas legais, perda de dados

**Solucao - Criar Mixin:**
```python
# backend/app/models/mixins.py
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, Boolean

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None

# Aplicar nos modelos:
class Order(Base, SoftDeleteMixin):
    ...

class Customer(Base, SoftDeleteMixin):
    ...
```

---

### 2.2 Order Number Unico e Obrigatorio
**Arquivo:** `backend/app/models/order.py`
**Problema:** `order_number` pode ser NULL
**Impacto:** Dificulta rastreamento

**Solucao:**
```python
import secrets
from datetime import datetime

def generate_order_number():
    return f"ORD-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"

class Order(Base):
    order_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        default=generate_order_number
    )
```

---

### 2.3 Usuario Desativado Nao Pode Acessar
**Arquivo:** `backend/app/auth.py`
**Problema:** `is_active=False` ainda consegue acessar

**Solucao:**
```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # ... validacao de token ...

    user = await db.execute(select(User).where(User.username == username))
    user = user.scalar_one_or_none()

    if not user:
        raise credentials_exception

    # ADICIONAR: Verificar se usuario esta ativo
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Usuario desativado. Contate o administrador."
        )

    return user
```

---

### 2.4 Validacao de Webhook Asaas com HMAC
**Arquivo:** `backend/app/api/webhooks.py`
**Problema:** Confia no status enviado sem validar
**Impacto:** Pagamentos fraudulentos

**Solucao:**
```python
import hmac
import hashlib

async def validate_asaas_webhook(request: Request) -> bool:
    signature = request.headers.get('asaas-signature')
    if not signature:
        return False

    body = await request.body()

    expected_signature = hmac.new(
        settings.asaas_webhook_token.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)

@router.post("/asaas")
async def asaas_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not await validate_asaas_webhook(request):
        logger.warning("Webhook Asaas com assinatura invalida")
        raise HTTPException(403, "Invalid webhook signature")

    # Processar webhook...
```

---

### 2.5 Limite de Conexoes WebSocket por Usuario
**Arquivo:** `backend/app/api/websocket.py`
**Problema:** Usuario pode abrir infinitas conexoes

**Solucao:**
```python
MAX_CONNECTIONS_PER_USER = 5

@router.websocket("/dashboard")
async def websocket_endpoint(websocket: WebSocket, ...):
    # Contar conexoes do usuario
    user_connections = sum(
        1 for conn in manager.active_connections
        if hasattr(conn, 'user_id') and conn.user_id == user.id
    )

    if user_connections >= MAX_CONNECTIONS_PER_USER:
        await websocket.close(
            code=1008,
            reason=f"Maximo de {MAX_CONNECTIONS_PER_USER} conexoes por usuario"
        )
        return

    # Continuar...
```

---

### 2.6 Timeout em Integracoes Externas
**Arquivo:** `backend/app/integrations/*.py`
**Problema:** Requests podem travar indefinidamente

**Solucao:**
```python
import httpx

async def call_external_api(url: str, data: dict, timeout: int = 30):
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            logger.error(f"Timeout ao chamar {url}")
            raise HTTPException(504, "Servico externo nao respondeu a tempo")
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP {e.response.status_code} de {url}")
            raise HTTPException(502, "Erro ao comunicar com servico externo")
```

---

### 2.7 Backup Automatico do PostgreSQL
**Arquivo:** `docker-compose.yml`

**Adicionar servico:**
```yaml
services:
  # ... outros servicos ...

  postgres-backup:
    image: prodrigestivill/postgres-backup-local
    container_name: gas_postgres_backup
    restart: unless-stopped
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_DB: ${POSTGRES_DB:-gas_automation}
      POSTGRES_USER: ${POSTGRES_USER:-gasadmin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-gasadmin123}
      SCHEDULE: "0 2 * * *"  # 2h da manha diariamente
      BACKUP_KEEP_DAYS: 7
      BACKUP_KEEP_WEEKS: 4
      BACKUP_KEEP_MONTHS: 6
      HEALTHCHECK_PORT: 8080
    volumes:
      - ./backups:/backups
    networks:
      - gas_network
    depends_on:
      - postgres
```

---

### 2.8 Audit Logs Automaticos
**Arquivo:** `backend/app/models/audit.py` (novo)

**Criar sistema de audit:**
```python
from sqlalchemy import event
from datetime import datetime, timezone

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50))  # CREATE, UPDATE, DELETE
    table_name: Mapped[str] = mapped_column(String(100))
    record_id: Mapped[str] = mapped_column(String(100))
    old_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

# Decorator para acoes auditaveis
def audit_action(action_type: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            # Log sera criado via middleware/context
            return result
        return wrapper
    return decorator
```

---

## PARTE 3: FRONTEND - ERROR HANDLING (Prioridade MEDIA)

### 3.1 Substituir alert() por Toast Notifications
**Arquivos:** Varios componentes
**Problema:** UX ruim com alert() nativo

**Solucao - Instalar react-hot-toast:**
```bash
cd frontend
npm install react-hot-toast
```

**Configurar no App.jsx:**
```javascript
import { Toaster } from 'react-hot-toast'

function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#333',
            color: '#fff',
          },
          success: {
            iconTheme: {
              primary: '#22c55e',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
      {/* ... resto do app */}
    </>
  )
}
```

**Substituir alerts:**
```javascript
// ANTES:
alert('Pedido criado com sucesso!')

// DEPOIS:
import toast from 'react-hot-toast'
toast.success('Pedido criado com sucesso!')

// ANTES:
alert('Erro ao criar pedido')

// DEPOIS:
toast.error('Erro ao criar pedido')
```

---

### 3.2 ErrorBoundary Global
**Arquivo:** `frontend/src/components/ErrorBoundary.jsx` (novo)

```javascript
import { Component } from 'react'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo })
    // Em producao, enviar para servico de logging (Sentry)
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
          <div className="bg-white p-8 rounded-lg shadow-lg max-w-md text-center">
            <h1 className="text-2xl font-bold text-red-600 mb-4">
              Algo deu errado
            </h1>
            <p className="text-gray-600 mb-6">
              Ocorreu um erro inesperado. Por favor, tente novamente.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
            >
              Recarregar Pagina
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
```

**Usar no main.jsx:**
```javascript
import ErrorBoundary from './components/ErrorBoundary'

<ErrorBoundary>
  <App />
</ErrorBoundary>
```

---

### 3.3 Validacao Frontend com Zod
**Instalar:**
```bash
npm install zod
```

**Criar schemas de validacao:**
```javascript
// frontend/src/utils/validations.js
import { z } from 'zod'

export const orderSchema = z.object({
  customer: z.object({
    name: z.string().min(3, 'Nome deve ter pelo menos 3 caracteres'),
    phone: z.string().regex(/^\d{10,11}$/, 'Telefone invalido (10-11 digitos)'),
    cpf: z.string().regex(/^\d{11}$/, 'CPF invalido').optional().or(z.literal('')),
  }),
  delivery_address: z.string().min(10, 'Endereco muito curto'),
  delivery_bairro: z.string().min(2, 'Bairro obrigatorio'),
  items: z.array(z.object({
    product_code: z.string().min(1, 'Produto obrigatorio'),
    quantity: z.number().min(1, 'Quantidade minima: 1').max(50, 'Quantidade maxima: 50')
  })).min(1, 'Adicione pelo menos um produto'),
  payment_method: z.enum(['pix', 'cash', 'card'], {
    errorMap: () => ({ message: 'Metodo de pagamento invalido' })
  })
})

export const validateOrder = (data) => {
  const result = orderSchema.safeParse(data)
  if (!result.success) {
    return {
      valid: false,
      errors: result.error.errors.map(e => e.message)
    }
  }
  return { valid: true, data: result.data }
}
```

---

### 3.4 Loading States em Botoes
**Criar componente Button com loading:**
```javascript
// frontend/src/components/ui/Button.jsx
function Button({
  children,
  loading = false,
  disabled = false,
  variant = 'primary',
  ...props
}) {
  const variants = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-800',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
  }

  return (
    <button
      disabled={loading || disabled}
      className={`
        px-4 py-2 rounded-lg font-medium transition-colors
        ${variants[variant]}
        ${(loading || disabled) ? 'opacity-50 cursor-not-allowed' : ''}
        flex items-center justify-center gap-2
      `}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12" cy="12" r="10"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      )}
      {children}
    </button>
  )
}

export default Button
```

---

### 3.5 Timeout em Requests HTTP
**Atualizar api.js:**
```javascript
// frontend/src/services/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://192.168.10.167:8000/api',
  timeout: 15000,  // 15 segundos
})

// Interceptor para tratar timeout
api.interceptors.response.use(
  response => response,
  error => {
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('Servidor demorou muito para responder. Tente novamente.'))
    }
    return Promise.reject(error)
  }
)
```

---

## PARTE 4: INFRA/DOCKER (Prioridade MEDIA)

### 4.1 Remover --reload em Producao
**Arquivo:** `docker-compose.yml` linha 205

**Criar docker-compose.prod.yml:**
```yaml
# docker-compose.prod.yml
services:
  backend:
    command: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
    environment:
      DEBUG: "false"
      ENVIRONMENT: "production"
```

---

### 4.2 Build Estatico do Frontend
**Criar Dockerfile.prod para frontend:**
```dockerfile
# frontend/Dockerfile.prod
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**nginx.conf:**
```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

### 4.3 Health Checks Melhorados
**Adicionar ao docker-compose.yml:**
```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## CHECKLIST SPRINT 2

### Backend - Logica
- [ ] 1.1 Validacao de bairro em pedidos
- [ ] 1.2 Constraint de preco positivo
- [ ] 1.3 Validacao de estoque
- [ ] 1.4 Schema de endereco do cliente
- [ ] 1.5 Limitar entregas por driver
- [ ] 1.6 Relatorios financeiros reais

### Backend - Validacoes
- [ ] 2.1 Soft delete em modelos principais
- [ ] 2.2 Order number unico e obrigatorio
- [ ] 2.3 Usuario desativado nao pode acessar
- [ ] 2.4 Validacao HMAC em webhooks Asaas
- [ ] 2.5 Limite de conexoes WebSocket
- [ ] 2.6 Timeout em integracoes externas
- [ ] 2.7 Backup automatico PostgreSQL
- [ ] 2.8 Audit logs automaticos

### Frontend - Error Handling
- [ ] 3.1 Substituir alert() por toast
- [ ] 3.2 ErrorBoundary global
- [ ] 3.3 Validacao com Zod
- [ ] 3.4 Loading states em botoes
- [ ] 3.5 Timeout em requests HTTP

### Infra/Docker
- [ ] 4.1 Remover --reload em producao
- [ ] 4.2 Build estatico do frontend
- [ ] 4.3 Health checks melhorados

---

## ORDEM DE EXECUCAO RECOMENDADA

### Dia 1-2: Backend Critico
1. Validacao de bairro
2. Constraint de preco
3. Usuario desativado bloqueado
4. Order number obrigatorio

### Dia 3-4: Backend Seguranca
1. Soft delete
2. Audit logs
3. Validacao HMAC webhooks
4. Timeout em integracoes

### Dia 5: Frontend
1. Toast notifications
2. ErrorBoundary
3. Loading states
4. Timeout em requests

### Dia 6-7: Infra e Testes
1. Backup automatico
2. Docker producao
3. Testes de integracao
4. Documentacao

---

## TESTES NECESSARIOS

### Backend
```bash
# Testar validacao de bairro
curl -X POST http://localhost:8000/api/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"delivery_bairro": "Bairro Invalido"}'
# Esperado: 400

# Testar usuario desativado
# 1. Desativar usuario no banco
# 2. Tentar fazer login
# Esperado: 403
```

### Frontend
```bash
# Build de producao
cd frontend
npm run build
# Esperado: Sem erros

# Verificar bundle size
npm run build -- --report
```

---

## METRICAS DE SUCESSO

| Metrica | Antes | Meta Sprint 2 |
|---------|-------|---------------|
| Validacoes de dados | 40% | 90% |
| Cobertura de erros UI | 20% | 80% |
| Audit logs | 0% | 100% acoes criticas |
| Backups | Manual | Automatico diario |

---

## RISCOS E MITIGACOES

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Migration quebra dados | Media | Alto | Backup antes, testar em staging |
| Toast notification bugs | Baixa | Baixo | Testar em todos os browsers |
| Audit logs muito verbosos | Media | Medio | Configurar nivel de log |

---

## PROXIMOS PASSOS APOS SPRINT 2

1. **Sprint 3:** Performance e otimizacao
2. **Sprint 4:** UX e funcionalidades avancadas
3. **Sprint 5:** Testes automatizados
4. **Sprint 6:** Deploy em producao

---

**Documento criado em:** 2026-01-22
**Responsavel:** Equipe de Desenvolvimento
**Revisao:** Apos conclusao do Sprint
