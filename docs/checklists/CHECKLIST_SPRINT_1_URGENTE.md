# ✅ CHECKLIST SPRINT 1 - CORREÇÕES URGENTES

**Objetivo:** Tornar o sistema seguro para produção  
**Prioridade:** 🔴 CRÍTICA  
**Tempo Estimado:** 3-5 dias  
**Desenvolvedor Responsável:** _________________

---

## 🚀 QUICK START

1. Criar branch: `git checkout -b fix/security-sprint-1`
2. Ler este checklist completamente
3. Marcar ✅ conforme concluir cada item
4. Fazer commit a cada item completo
5. PR ao final com todos itens marcados

---

## 📋 ITENS OBRIGATÓRIOS

### **1. [ ] Chaves de Segurança Obrigatórias**

**Arquivo:** `backend/app/config.py`

**Antes:**
```python
secret_key: str = "supersecretkey123changeme"
jwt_secret_key: str = "your-jwt-secret-key-change-in-production"
```

**Depois:**
```python
from pydantic import Field, field_validator

secret_key: str = Field(..., min_length=32)
jwt_secret_key: str = Field(..., min_length=32)

@field_validator('secret_key', 'jwt_secret_key')
def validate_secret_keys(cls, v, info):
    dangerous_keys = [
        "supersecretkey123changeme",
        "your-jwt-secret-key-change-in-production",
        "changeme",
        "secret",
        "key123"
    ]
    if v.lower() in dangerous_keys or len(v) < 32:
        raise ValueError(
            f"{info.field_name} deve ter no mínimo 32 caracteres "
            "e não pode ser uma chave padrão. "
            "Gere uma nova: openssl rand -hex 32"
        )
    return v
```

**Adicionar ao .env:**
```bash
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

**Testar:**
```bash
# Deve falhar com chave fraca
SECRET_KEY=123 python -m app.main

# Deve funcionar com chave forte
SECRET_KEY=$(openssl rand -hex 32) python -m app.main
```

**Commit:** `fix: enforce strong secret keys from environment`

---

### **2. [ ] Remover CORS "*" e Whitelist Específica**

**Arquivo:** `backend/app/config.py`

**Antes:**
```python
cors_origins: list[str] = [
    "http://localhost:3003",
    "http://192.168.10.167:3003",
    "*"  # ❌ REMOVE ISSO
]
```

**Depois:**
```python
cors_origins: list[str] = [
    "http://localhost:3003",
    "http://192.168.10.167:3003",
    # Em produção, adicionar apenas domínio real
    # "https://seu-dominio.com.br"
]

@field_validator('cors_origins')
def validate_cors_origins(cls, v):
    if "*" in v:
        raise ValueError(
            "CORS com '*' não é permitido. "
            "Especifique apenas as origens necessárias."
        )
    return v
```

**Testar:**
```bash
# Deve rejeitar requisição de origem não autorizada
curl -H "Origin: http://malicious-site.com" \
  http://localhost:8000/api/orders
```

**Commit:** `fix: remove wildcard CORS and enforce whitelist`

---

### **3. [ ] Implementar Rate Limiting**

**Arquivo:** `backend/app/main.py`

**Instalar dependência:**
```bash
cd backend
pip install slowapi
pip freeze > requirements.txt
```

**Adicionar ao início do main.py:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**No arquivo `backend/app/api/auth.py`:**
```python
from app.main import limiter

@router.post("/token")
@limiter.limit("5/minute")  # 5 tentativas por minuto
async def login(
    request: Request,  # IMPORTANTE: adicionar Request
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # ... código existente
```

**Testar:**
```bash
# Fazer 6 requisições rápidas - a 6ª deve retornar 429
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/auth/token \
    -d "username=test&password=test"
  echo ""
done
```

**Commit:** `feat: add rate limiting to prevent brute force attacks`

---

### **4. [ ] Validar UUIDs em Todos os Endpoints**

**Arquivo:** `backend/app/api/orders.py` e outros

**Antes:**
```python
@router.get("/{order_id}")
async def get_order(order_id: str):  # ❌ str aceita qualquer coisa
    # ...
```

**Depois:**
```python
from uuid import UUID
from pydantic import UUID4

@router.get("/{order_id}")
async def get_order(order_id: UUID4):  # ✅ Valida automaticamente
    # ...
```

**Arquivos para atualizar:**
- `backend/app/api/orders.py`
- `backend/app/api/drivers.py`
- `backend/app/api/customers.py`
- `backend/app/api/chats.py`

**Buscar todos:**
```bash
cd backend
grep -r "/{.*_id}" app/api/*.py | grep "str"
```

**Testar:**
```bash
# Deve retornar 422 Validation Error
curl http://localhost:8000/api/orders/invalid-uuid

# Deve funcionar
curl http://localhost:8000/api/orders/550e8400-e29b-41d4-a716-446655440000
```

**Commit:** `fix: validate UUID format in all path parameters`

---

### **5. [ ] WebSocket com Autenticação no Handshake**

**Arquivo:** `backend/app/api/websocket.py`

**Antes:**
```python
@router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()  # ❌ Aceita antes de validar
    # ... validação do token depois
```

**Depois:**
```python
from fastapi import Query

@router.websocket("/notifications")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token"),
    db: AsyncSession = Depends(get_db)
):
    # Validar token ANTES de aceitar conexão
    user = await get_current_user_ws(token, db)
    
    if not user or not user.is_active:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    # Só aceita se token válido
    await websocket.accept()
    
    # ... resto do código
```

**Frontend:** `frontend/src/services/sharedWebSocket.js`

**Antes:**
```javascript
const url = `${WS_BASE_URL}/ws/notifications`
```

**Depois:**
```javascript
const token = localStorage.getItem('token')
const url = `${WS_BASE_URL}/ws/notifications?token=${encodeURIComponent(token)}`
```

**Testar:**
```bash
# Sem token - deve rejeitar
wscat -c ws://localhost:8000/ws/notifications

# Com token inválido - deve rejeitar
wscat -c "ws://localhost:8000/ws/notifications?token=invalid"

# Com token válido - deve conectar
wscat -c "ws://localhost:8000/ws/notifications?token=eyJ..."
```

**Commit:** `fix: authenticate WebSocket connections before accepting`

---

### **6. [ ] Proteger Endpoint /metrics**

**Arquivo:** `backend/app/config.py`

**Adicionar:**
```python
# Segurança
metrics_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
```

**Arquivo:** `backend/app/main.py`

**Antes:**
```python
@app.get("/metrics", tags=["Monitoring"])
def metrics_endpoint():
    return PlainTextResponse(generate_latest().decode('utf-8'))
```

**Depois:**
```python
from fastapi import Header, HTTPException

@app.get("/metrics", tags=["Monitoring"])
async def metrics_endpoint(
    x_metrics_token: str = Header(..., alias="X-Metrics-Token")
):
    if x_metrics_token != settings.metrics_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing metrics token"
        )
    
    return PlainTextResponse(
        content=generate_latest().decode('utf-8'),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Prometheus config:** `prometheus/prometheus.yml`

```yaml
scrape_configs:
  - job_name: 'gas-automation'
    static_configs:
      - targets: ['backend:8000']
    # Adicionar token
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/metrics_token.txt
```

**Testar:**
```bash
# Sem token - deve retornar 403
curl http://localhost:8000/metrics

# Com token - deve funcionar
curl -H "X-Metrics-Token: seu_token_aqui" http://localhost:8000/metrics
```

**Commit:** `fix: protect metrics endpoint with authentication`

---

### **7. [ ] Validar Formato de Phone Number**

**Arquivo:** `backend/app/schemas/customer.py`

**Adicionar:**
```python
import re
from pydantic import field_validator

class CustomerBase(BaseSchema):
    phone: str = Field(..., min_length=10, max_length=20)
    # ... outros campos
    
    @field_validator('phone')
    def validate_phone(cls, v):
        # Remover caracteres não numéricos
        clean_phone = re.sub(r'\D', '', v)
        
        # Validar formato brasileiro (10-11 dígitos)
        if not re.match(r'^\d{10,11}$', clean_phone):
            raise ValueError(
                'Telefone deve ter 10-11 dígitos numéricos. '
                'Formato: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX'
            )
        
        # Retornar apenas números
        return clean_phone
```

**Testar:**
```python
# backend/tests/test_customer_schema.py
def test_phone_validation():
    # Deve aceitar
    assert CustomerCreate(phone="11999998888", ...).phone == "11999998888"
    assert CustomerCreate(phone="(11) 99999-8888", ...).phone == "11999998888"
    
    # Deve rejeitar
    with pytest.raises(ValidationError):
        CustomerCreate(phone="123", ...)  # Muito curto
    with pytest.raises(ValidationError):
        CustomerCreate(phone="abc123def", ...)  # Não numérico
```

**Commit:** `fix: validate and sanitize phone number format`

---

### **8. [ ] Transações Atômicas em Pedidos**

**Arquivo:** `backend/app/api/orders.py`

**Antes:**
```python
@router.post("")
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    # Criar pedido
    order = Order(...)
    db.add(order)
    await db.flush()  # ❌ Se falhar aqui, pedido órfão
    
    # Adicionar itens
    for item_data in data.items:
        item = OrderItem(...)  # ❌ Se falhar aqui, pedido sem itens
        db.add(item)
    
    await db.commit()
```

**Depois:**
```python
@router.post("")
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    try:
        async with db.begin():  # ✅ Transação explícita
            # Criar pedido
            order = Order(...)
            db.add(order)
            await db.flush()
            
            # Adicionar itens
            for item_data in data.items:
                item = OrderItem(...)
                db.add(item)
            
            # Se chegou aqui, commit automático
            # Se qualquer operação falhar, rollback automático
        
        await db.refresh(order)
        return order
        
    except Exception as e:
        logger.error(f"Erro ao criar pedido: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar pedido")
```

**Testar:**
```python
# backend/tests/test_order_transactions.py
async def test_order_creation_rollback():
    # Simular erro ao criar item
    with patch('app.api.orders.OrderItem', side_effect=Exception("Erro")):
        with pytest.raises(HTTPException):
            await create_order(...)
    
    # Verificar que pedido NÃO foi criado
    orders = await db.execute(select(Order))
    assert len(orders.scalars().all()) == 0
```

**Commit:** `fix: use atomic transactions for order creation`

---

### **9. [ ] Validar Sobreposição de Time Logs**

**Arquivo:** `backend/app/services/driver_time_tracking_service.py`

**Adicionar no início de `start_time_log`:**
```python
@staticmethod
async def start_time_log(db: AsyncSession, driver_id: UUID, status: str):
    # Verificar se já existe log aberto
    existing = await db.execute(
        select(DriverTimeLog).where(
            DriverTimeLog.driver_id == driver_id,
            DriverTimeLog.ended_at == None
        )
    )
    
    open_log = existing.scalar_one_or_none()
    if open_log:
        # Finalizar log anterior automaticamente
        logger.warning(
            f"Driver {driver_id} tinha log aberto desde "
            f"{open_log.started_at}. Finalizando automaticamente."
        )
        open_log.finalize()
        await db.commit()
    
    # Criar novo log
    # ... código existente
```

**Testar:**
```python
async def test_prevent_overlapping_logs():
    # Criar primeiro log
    log1 = await start_time_log(db, driver_id, "available")
    
    # Tentar criar segundo sem finalizar primeiro
    log2 = await start_time_log(db, driver_id, "busy")
    
    # Verificar que log1 foi finalizado
    await db.refresh(log1)
    assert log1.ended_at is not None
    assert log2.ended_at is None
```

**Commit:** `fix: prevent overlapping driver time logs`

---

### **10. [ ] Migrar Tokens para httpOnly Cookies (Frontend)**

**⚠️ Nota:** Mudança mais complexa, pode ser feita em sub-sprint

**Backend:** `backend/app/api/auth.py`

**Antes:**
```python
@router.post("/token")
async def login(...):
    token = create_access_token(...)
    return {"access_token": token, "token_type": "bearer"}
```

**Depois:**
```python
from fastapi import Response

@router.post("/token")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # ... autenticação ...
    
    token = create_access_token(data={"sub": user.username})
    
    # Definir cookie ao invés de retornar token
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,  # JavaScript não pode acessar
        secure=settings.is_production,  # HTTPS only em prod
        samesite="lax",  # Proteção CSRF
        max_age=settings.access_token_expire_minutes * 60
    )
    
    return {"message": "Login successful"}
```

**Middleware para ler cookie:**
```python
# backend/app/auth.py
from fastapi import Cookie

async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not access_token:
        raise credentials_exception()
    
    # Remover "Bearer " se presente
    token = access_token.replace("Bearer ", "")
    
    # ... validação do token ...
```

**Frontend:** Remover uso de localStorage

**Antes:**
```javascript
// useAuth.jsx
const token = localStorage.getItem('token')
```

**Depois:**
```javascript
// Cookie é enviado automaticamente pelo navegador
// Apenas fazer fetch normalmente com credentials
fetch('http://192.168.10.167:8000/api/orders', {
  credentials: 'include'  // Importante!
})
```

**Testar:**
```bash
# Login deve definir cookie
curl -c cookies.txt -X POST http://localhost:8000/api/auth/token \
  -d "username=test&password=test"

# Request subsequente usa cookie
curl -b cookies.txt http://localhost:8000/api/orders
```

**Commit:** `feat: migrate tokens from localStorage to httpOnly cookies`

---

### **11. [ ] Remover console.log Sensíveis**

**Criar logger centralizado:** `frontend/src/utils/logger.js`

```javascript
const isDev = import.meta.env.MODE === 'development'

const logger = {
  log: (...args) => {
    if (isDev) console.log('[LOG]', ...args)
  },
  
  info: (...args) => {
    if (isDev) console.info('[INFO]', ...args)
  },
  
  warn: (...args) => {
    console.warn('[WARN]', ...args)  // Sempre loga warnings
  },
  
  error: (...args) => {
    console.error('[ERROR]', ...args)  // Sempre loga erros
    // Em produção, enviar para Sentry/LogRocket
    if (!isDev) {
      // sendToErrorTracking(args)
    }
  },
  
  debug: (...args) => {
    if (isDev) console.debug('[DEBUG]', ...args)
  }
}

export default logger
```

**Substituir em todos os arquivos:**
```bash
cd frontend
# Buscar todos console.log
grep -r "console\.log" src/

# Substituir por logger
find src/ -name "*.jsx" -exec sed -i 's/console\.log/logger.log/g' {} +
find src/ -name "*.js" -exec sed -i 's/console\.log/logger.log/g' {} +

# Adicionar import
find src/ -name "*.jsx" -exec sed -i "1i import logger from '@/utils/logger'" {} +
```

**Verificar que não vaza dados sensíveis:**
```javascript
// ❌ NUNCA fazer
logger.log('User password:', password)
logger.log('JWT token:', token)
logger.log('Customer data:', customer)

// ✅ OK
logger.log('Login attempt for user:', username)
logger.log('Token validated successfully')
logger.log('Customer loaded:', customer.id)
```

**Commit:** `refactor: replace console.log with centralized logger`

---

### **12. [ ] Adicionar Validação de Password Longa**

**Arquivo:** `backend/app/auth.py`

**Antes:**
```python
def get_password_hash(password):
    password = password.encode('utf-8')[:72].decode('utf-8')  # ❌ Silencioso
    return pwd_context.hash(password)
```

**Depois:**
```python
def get_password_hash(password: str) -> str:
    """Hash a password using Argon2"""
    
    # Validar comprimento
    if len(password) < 8:
        raise ValueError("Senha deve ter no mínimo 8 caracteres")
    
    if len(password) > 72:
        raise ValueError(
            "Senha não pode ter mais de 72 caracteres "
            "(limitação do Argon2)"
        )
    
    return pwd_context.hash(password)
```

**Adicionar validação no schema:**
```python
# backend/app/schemas/auth.py
class UserCreate(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    
    @field_validator('password')
    def validate_password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Senha deve conter pelo menos uma letra maiúscula")
        if not any(c.islower() for c in v):
            raise ValueError("Senha deve conter pelo menos uma letra minúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("Senha deve conter pelo menos um número")
        return v
```

**Testar:**
```python
def test_password_validation():
    # Deve aceitar
    hash = get_password_hash("SenhaForte123")
    
    # Deve rejeitar
    with pytest.raises(ValueError):
        get_password_hash("123")  # Muito curta
    
    with pytest.raises(ValueError):
        get_password_hash("a" * 73)  # Muito longa
```

**Commit:** `fix: validate password length and strength`

---

## 🧪 TESTES FINAIS

Após completar todos os itens, executar:

### **Backend:**
```bash
cd backend

# Testes unitários
pytest tests/ -v

# Testes de segurança
bandit -r app/

# Verificar vulnerabilidades
safety check

# Scan de secrets
trufflehog filesystem . --json
```

### **Frontend:**
```bash
cd frontend

# Build de produção (não deve ter erros)
npm run build

# Verificar bundle size
npm run analyze

# Verificar vulnerabilidades
npm audit
```

### **Integração:**
```bash
# Subir todos os serviços
docker-compose up -d

# Aguardar inicialização
sleep 10

# Testar endpoints críticos
curl http://localhost:8000/health
curl http://localhost:8000/api/info
curl -X POST http://localhost:8000/api/auth/token \
  -d "username=admin&password=admin123"
```

---

## 📝 CHECKLIST DE FINALIZAÇÃO

Antes de criar o Pull Request:

- [ ] Todos os 12 itens acima estão marcados como ✅
- [ ] Testes automatizados passando
- [ ] Nenhum TODO/FIXME introduzido
- [ ] Documentação atualizada (se necessário)
- [ ] `.env.example` atualizado com novas variáveis
- [ ] CHANGELOG.md atualizado
- [ ] Commit messages seguem padrão conventional commits
- [ ] Branch atualizada com main: `git rebase main`
- [ ] Code review solicitado

---

## 🚀 CRIAR PULL REQUEST

```bash
# Push da branch
git push origin fix/security-sprint-1

# Criar PR com template
gh pr create --title "🔐 Sprint 1: Critical Security Fixes" \
  --body "$(cat <<EOF
## 📋 Resumo
Implementa todas as correções críticas de segurança do Sprint 1.

## ✅ Checklist
- [x] Chaves de segurança obrigatórias
- [x] CORS whitelist específica
- [x] Rate limiting implementado
- [x] UUIDs validados
- [x] WebSocket autenticado
- [x] Endpoint /metrics protegido
- [x] Phone numbers validados
- [x] Transações atômicas
- [x] Time logs sem sobreposição
- [x] Tokens em httpOnly cookies
- [x] Logger centralizado
- [x] Password validation

## 🧪 Testes
- Backend: pytest (100% passing)
- Frontend: npm run build (success)
- Security: bandit (no issues)
- Integration: all endpoints working

## 📚 Documentação
- ANALISE_SISTEMA_SPRINTS.md
- RESUMO_EXECUTIVO_ANALISE.md

## ⚠️ Breaking Changes
- Frontend: Tokens agora em cookies (não localStorage)
- API: Endpoints requerem UUIDs válidos
- WebSocket: Requer token na URL

## 🔍 Reviewers
@backend-team @security-team

Closes #XXX
EOF
)"
```

---

## 📊 MÉTRICAS DE SUCESSO

Após merge deste Sprint:

✅ **Segurança:**
- 0 vulnerabilidades críticas no scan
- 100% endpoints com autenticação
- Rate limiting ativo

✅ **Qualidade:**
- 0 console.logs em produção
- 100% UUIDs validados
- Transações atômicas em 100% das operações críticas

✅ **Performance:**
- Sem mudança significativa (foco em segurança)

---

## 🆘 SE ENCONTRAR PROBLEMAS

1. **Erro de importação:** Verifique se instalou dependências
   ```bash
   pip install -r requirements.txt
   ```

2. **Testes falhando:** Verifique se banco está limpo
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

3. **CORS errors:** Verifique se frontend está na whitelist
   ```python
   cors_origins = ["http://192.168.10.167:3003"]
   ```

4. **WebSocket não conecta:** Verifique se está passando token na URL
   ```javascript
   `${WS_URL}?token=${token}`
   ```

---

**Data de Início:** ___ / ___ / ___  
**Data de Conclusão:** ___ / ___ / ___  
**Tempo Real:** _____ horas  

**Próximo Sprint:** Sprint 2 - Consistência de Dados
