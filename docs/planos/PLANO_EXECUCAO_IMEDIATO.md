# 🎯 Plano de Execução Imediato - Próximos 3 Passos

## 📌 Situação Atual (21 Jan 2026)

- ✅ **73% do código está implementado** e em produção
- ✅ **Fases 1-5 estruturalmente prontas** (config, auth, integrações, APIs)
- ⚠️ **Fase 6-9 precisam de validação e consolidação**
- 🎯 **Tempo restante estimado: 2-3 semanas**

---

## 🚀 PASSO 1: Validação Rápida (2-3 horas)

### Objetivo
Confirmar que toda a infraestrutura FASE 1-5 está funcionando

### Checklist
```bash
# 1. Entrar no diretório do backend
cd /home/daniel/gas-automation/backend

# 2. Verificar requirements.txt
cat requirements.txt | wc -l
# Esperado: ~35 linhas com todas as dependências principais

# 3. Testar imports críticos
python3 -c "
from app.config import settings
from app.database import AsyncSessionLocal, Base, get_db
from app.auth import get_password_hash, verify_password
print('✅ Config OK')
print('✅ Database OK')
print('✅ Auth OK')
print('✅ Tudo pronto!')
"

# 4. Verificar se env.py do Alembic está configurado
cat alembic/env.py | head -50

# 5. Verificar docker-compose
docker-compose config > /tmp/docker-check.log 2>&1 && echo "✅ Docker OK" || echo "❌ Erro no docker-compose"

# 6. Listar todos os endpoints
python3 -c "
import re
import os

endpoints = {}
for root, dirs, files in os.walk('app/api'):
    for file in files:
        if file.endswith('.py') and not file.startswith('__'):
            path = os.path.join(root, file)
            with open(path) as f:
                content = f.read()
                routers = re.findall(r'@router\.(get|post|put|delete|patch)\((.*?)\)', content)
                if routers:
                    endpoints[file] = len(routers)

print('📍 Endpoints por arquivo:')
for file, count in sorted(endpoints.items()):
    print(f'  {file}: {count} rotas')
print(f'✅ Total: {sum(endpoints.values())} endpoints')
"
```

### Saída Esperada
```
✅ Config OK
✅ Database OK
✅ Auth OK
✅ Tudo pronto!
✅ Docker OK
📍 Endpoints por arquivo:
  auth.py: 2 rotas
  users.py: 4 rotas
  customers.py: 4 rotas
  ...
✅ Total: 45+ endpoints
```

---

## ⚙️ PASSO 2: Gerar .env.example (1 hora)

### Problema
Não existe `.env.example` para novos desenvolvedores

### Solução
Criar baseado em `app/config.py`

```bash
cd /home/daniel/gas-automation/backend

# Crie o arquivo:
cat > .env.example << 'EOF'
# ==================== APLICAÇÃO ====================
APP_NAME="Gas Automation API"
APP_VERSION="1.0.0"
DEBUG=false
ENVIRONMENT=development
SECRET_KEY=sua_chave_secreta_muito_longa_aqui_32_chars_minimo

# ==================== POSTGRESQL ====================
DATABASE_URL=postgresql+asyncpg://gasadmin:gasadmin123@localhost:5432/gas_automation
DATABASE_ECHO=false

# ==================== REDIS ====================
REDIS_URL=redis://localhost:6379/0
REDIS_CONVERSATION_TTL=1800

# ==================== JWT ====================
JWT_SECRET_KEY=sua_chave_jwt_muito_longa_aqui_32_chars_minimo
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ==================== WAHA (WhatsApp) ====================
WAHA_URL=http://localhost:3000
WAHA_API_KEY=gasautomation123
WAHA_SESSION_NAME=default

# ==================== ASAAS (Pagamentos) ====================
ASAAS_API_KEY=seu_token_asaas_aqui
ASAAS_API_URL=https://api.asaas.com/v3
ASAAS_WEBHOOK_TOKEN=seu_webhook_token_aqui

# ==================== OLLAMA (IA Local) ====================
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT=30
AI_CONFIDENCE_THRESHOLD=0.7

# ==================== FIREBIRD (Legacy) ====================
FIREBIRD_HOST=seu_host_firebird
FIREBIRD_DATABASE=seu_database_firebird
FIREBIRD_USER=SYSDBA
FIREBIRD_PASSWORD=sua_senha_firebird
FIREBIRD_CHARSET=UTF8

# ==================== MINIO (Storage) ====================
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_SECURE=false

# ==================== CORS ====================
CORS_ORIGINS=["http://localhost:3001","http://localhost:3000","http://192.168.10.156:3001"]

# ==================== RATE LIMITING ====================
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# ==================== MÉTRICAS ====================
METRICS_TOKEN=seu_token_prometheus_aqui
EOF

echo "✅ .env.example criado!"
```

### Verificar
```bash
# Comparar com config.py
grep -E "Field\(|:\s" app/config.py | grep -v "^#" | head -30
```

---

## 🧪 PASSO 3: Criar Suite de Testes (1 dia)

### Status
`tests/` não foi localizado - PRECISA SER CRIADO

### Estrutura
```bash
cd /home/daniel/gas-automation

# Criar estrutura de testes
mkdir -p backend/tests/test_api
mkdir -p backend/tests/test_integrations
mkdir -p backend/tests/test_core

# Criar conftest.py (fixtures compartilhadas)
cat > backend/tests/conftest.py << 'EOF'
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.database import Base, get_db
from app.config import settings

# Database de teste
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
async def engine():
    """Cria engine de teste."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    """Cria sessão de teste para cada teste."""
    async_session_local = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session_local() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    """Cria cliente HTTP de teste."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
EOF

echo "✅ conftest.py criado!"
```

### Testes Básicos
```bash
# backend/tests/test_api/test_health.py
cat > backend/tests/test_api/test_health.py << 'EOF'
import pytest

@pytest.mark.asyncio
async def test_health_check(client):
    """Testa endpoint de health check."""
    response = await client.get("/health")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Testa endpoint raiz."""
    response = await client.get("/")
    assert response.status_code in [200, 404]  # Pode não existir
EOF

# backend/tests/test_api/test_auth.py
cat > backend/tests/test_api/test_auth.py << 'EOF'
import pytest
from app.auth import get_password_hash, verify_password

def test_password_hashing():
    """Testa hash de senha."""
    password = "minha_senha_segura_123"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("senha_errada", hashed)
EOF

echo "✅ Testes básicos criados!"
```

### Rodar Testes
```bash
cd /home/daniel/gas-automation/backend

# Instalar pytest se necessário
pip install pytest pytest-asyncio

# Rodar todos os testes
pytest tests/ -v --asyncio-mode=auto

# Com coverage
pytest tests/ -v --asyncio-mode=auto --cov=app --cov-report=html
```

---

## 📋 Checklist de Execução

### Semana 1 (Esta Semana)
- [ ] Passo 1: Validação Rápida (2-3 horas)
- [ ] Passo 2: .env.example (1 hora)
- [ ] Passo 3: Suite de Testes (1 dia)
- [ ] Documentar achados em CHECKLIST_EXECUÇÃO.md
- [ ] Revisar FASE 1-5 contra planejamento

### Semana 2
- [ ] Validação integrada (docker-compose up -d)
- [ ] Testes de integrações externas
- [ ] Health check endpoints
- [ ] Revisão de models/services
- [ ] Atualizar documentação

### Semana 3
- [ ] Deploy em staging
- [ ] Performance tests
- [ ] Linter + code quality
- [ ] Preparar para produção

---

## 📞 Quando Algo Quebrar

### "ModuleNotFoundError: No module named 'app.models'"
```bash
# Solução: Verificar se models tem __init__.py
ls -la backend/app/models/__init__.py

# Se não existir:
touch backend/app/models/__init__.py
echo "from .auth_models import *" > backend/app/models/__init__.py
```

### "No Redis connection"
```python
# Em app/main.py, adicione em lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await redis_manager.connect()
    except Exception as e:
        logger.warning(f"Redis offline: {e}")
    yield
    await redis_manager.disconnect()

app = FastAPI(lifespan=lifespan)
```

### "Alembic: No such table"
```bash
# Solução: Criar primeira migration
cd backend
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

---

## 🎯 Próximo Documento

Após completar estes passos, criar:
- `CHECKLIST_EXECUÇÃO_FASE_1_5.md` - Status de cada componente
- `ROADMAP_TESTES.md` - Cobertura esperada vs atual
- `INTEGRAÇÕES_VALIDADAS.md` - Status ASAAS, WAHA, Firebird, MinIO, Ollama

---

**Preparado para:** Implementação Imediata  
**Tempo Total Estimado:** 2-3 dias para completar Passo 1-3  
**Próximo Status Check:** 24 Janeiro de 2026
