# 🔥 Guia de Integração Firebird - Gasmaster

## ✅ Status Atual

Você já conseguiu conectar ao banco Firebird:
```sql
CONNECT '192.168.10.167:/var/firebird/Gas.fdb'
USER 'SYSDBA'
PASSWORD 'masterkey';
```

## 📋 Próximos Passos

### 1. **Mapear o Schema do Firebird** ⭐ PRIORITÁRIO

Execute o script de mapeamento para descobrir as tabelas e estruturas:

```bash
cd /home/daniel/gas-automation/backend
python scripts/map_firebird_schema.py
```

Este script irá:
- ✅ Listar todas as tabelas do banco
- ✅ Mostrar estrutura das tabelas importantes (PRODUTOS, CLIENTES, PEDIDOS, etc.)
- ✅ Exibir dados de exemplo para entender o formato

**Resultado esperado:** Identificar os nomes reais das tabelas e colunas no Firebird da Gasmaster.

---

### 2. **Configurar Variáveis de Ambiente**

Adicione as configurações do Firebird no arquivo `.env`:

```bash
# Firebird (Sistema Legado Gasmaster)
FIREBIRD_HOST=192.168.10.167
FIREBIRD_DATABASE=/var/firebird/Gas.fdb
FIREBIRD_USER=SYSDBA
FIREBIRD_PASSWORD=masterkey
FIREBIRD_CHARSET=UTF8
```

**Nota:** O formato da conexão no código usa `host/port:database`, então será:
- Host: `192.168.10.167`
- Port: `3050` (padrão Firebird)
- Database: `/var/firebird/Gas.fdb`

---

### 3. **Instalar Dependência fdb no Backend**

Verifique se a biblioteca `fdb` está instalada:

```bash
docker exec gas_backend pip list | grep fdb
```

Se não estiver, adicione ao `requirements.txt` e reconstrua:

```bash
# Adicionar fdb==2.0.2 ao requirements.txt
docker-compose build backend
docker-compose restart backend
```

---

### 4. **Ajustar Queries no Código**

Após mapear o schema, você precisará ajustar as queries em:

**Arquivo:** `backend/app/integrations/firebird.py`

**Queries que precisam ser ajustadas:**

#### 4.1. Produtos (linha ~150)
```python
def get_products(self, active_only: bool = True) -> list[dict]:
    # AJUSTAR: Nome real da tabela e colunas
    query = """
        SELECT
            CODIGO,           # ← Verificar nome real
            DESCRICAO,        # ← Verificar nome real
            PRECO_VENDA,      # ← Verificar nome real
            UNIDADE,          # ← Verificar nome real
            ATIVO             # ← Verificar nome real
        FROM PRODUTOS         # ← Verificar nome real da tabela
        WHERE TIPO = 'GAS'    # ← Verificar se existe este campo
    """
```

#### 4.2. Clientes (linha ~220)
```python
def get_customer_by_phone(self, phone: str) -> Optional[dict]:
    # AJUSTAR: Nome real da tabela e colunas
    query = """
        SELECT
            CODIGO,           # ← Verificar nome real
            NOME,             # ← Verificar nome real
            TELEFONE,         # ← Verificar nome real
            CELULAR,          # ← Verificar nome real
            ENDERECO,         # ← Verificar nome real
            ...
        FROM CLIENTES         # ← Verificar nome real da tabela
        WHERE ...
    """
```

---

### 5. **Testar Conexão**

Após configurar, teste a conexão:

```bash
# Via API (se tiver endpoint de teste)
curl http://localhost:8000/api/integrations/firebird/test

# Ou via Python no container
docker exec -it gas_backend python -c "
from app.integrations.firebird import firebird_client
print('Disponível:', firebird_client.is_available)
print('Teste:', firebird_client.test_connection())
"
```

---

### 6. **Criar Script de Sincronização Inicial**

Após mapear o schema, crie um script para importar dados iniciais:

```python
# backend/scripts/sync_firebird_initial.py
"""
Sincronização inicial: Importa produtos e clientes do Firebird para PostgreSQL.
"""

from app.integrations.firebird import firebird_client
from app.database import AsyncSessionLocal
from app.models.product import Product
from app.models.customer import Customer

async def sync_initial_data():
    """Sincroniza dados iniciais do Firebird."""
    
    # 1. Importar produtos
    fb_products = firebird_client.get_products()
    print(f"📦 Importando {len(fb_products)} produtos...")
    
    # 2. Importar clientes (opcional - pode ser sob demanda)
    # fb_customers = firebird_client.get_customers()
    
    # 3. Salvar no PostgreSQL
    # ...
```

---

### 7. **Estrutura de Dados Esperada**

#### Produtos
O sistema espera produtos com:
- `code`: Código do produto (ex: "P13", "P20", "P45")
- `name`: Nome/descrição
- `price`: Preço de venda
- `weight_kg`: Peso em kg (opcional)
- `is_active`: Se está ativo

#### Clientes
O sistema espera clientes com:
- `phone`: Telefone (chave principal)
- `name`: Nome completo
- `address`: Endereço completo (JSON ou campos separados)
- `cpf_cnpj`: CPF/CNPJ (opcional)

---

### 8. **Checklist de Integração**

- [ ] ✅ Conectar ao Firebird (FEITO)
- [ ] ⏳ Mapear schema (executar script)
- [ ] ⏳ Configurar variáveis de ambiente
- [ ] ⏳ Instalar dependência fdb
- [ ] ⏳ Ajustar queries de produtos
- [ ] ⏳ Ajustar queries de clientes
- [ ] ⏳ Testar conexão
- [ ] ⏳ Testar busca de produtos
- [ ] ⏳ Testar busca de clientes
- [ ] ⏳ Criar script de sincronização inicial
- [ ] ⏳ Importar produtos iniciais
- [ ] ⏳ Configurar sincronização automática (opcional)

---

### 9. **Comandos Úteis**

```bash
# Testar conexão direta
docker exec gas_backend python -c "
import fdb
conn = fdb.connect(
    dsn='192.168.10.167/3050:/var/firebird/Gas.fdb',
    user='SYSDBA',
    password='masterkey',
    charset='UTF8'
)
cursor = conn.cursor()
cursor.execute('SELECT 1 FROM RDB\$DATABASE')
print('✅ Conectado!')
conn.close()
"

# Ver logs do backend
docker logs gas_backend --tail 50 | grep -i firebird

# Verificar se fdb está instalado
docker exec gas_backend pip show fdb
```

---

### 10. **Próximas Ações Imediatas**

1. **Execute o script de mapeamento:**
   ```bash
   cd /home/daniel/gas-automation/backend
   python scripts/map_firebird_schema.py > firebird_schema_map.txt
   ```

2. **Analise o resultado** e identifique:
   - Nome real da tabela de produtos
   - Nome real da tabela de clientes
   - Estrutura das colunas

3. **Compartilhe o resultado** para ajustarmos as queries no código.

---

## 📞 Suporte

Se encontrar problemas:
- Verifique os logs: `docker logs gas_backend | grep -i firebird`
- Teste conexão direta com `isql` ou `fdb`
- Verifique firewall/rede entre containers e servidor Firebird
