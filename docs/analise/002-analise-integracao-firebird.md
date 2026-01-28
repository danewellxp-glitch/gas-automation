# Análise da Integração Firebird - Estado Atual

**Data:** 27/01/2026  
**Objetivo:** Analisar o estado atual da integração Firebird e identificar o que falta para completar 100%

---

## 📊 Resumo Executivo

A integração Firebird está **parcialmente implementada** com:
- ✅ **Importação** (Firebird → PostgreSQL): Produtos, Clientes, Estoque
- ✅ **Exportação** (PostgreSQL → Firebird): Pedidos (TRADE/TRADEITEM)
- ⚠️ **Configuração**: 3 configurações críticas faltando (ver `003-varredura-profunda-firebird.md`)
- ⚠️ **Sincronização**: 0% dos dados sincronizados (ver `003-varredura-profunda-firebird.md`)

**📋 Para análise detalhada, consulte:** `docs/analise/003-varredura-profunda-firebird.md`

---

## 🔄 Fluxo de Dados

### 1. Importação (Firebird → PostgreSQL)

#### Produtos
- **Fonte:** Tabelas `ITEM` + `ITEMPRECO` do Firebird
- **Destino:** Tabela `products` no PostgreSQL
- **Status:** ✅ Implementado
- **Métodos:**
  - `firebird_client.get_products()` - Lista todos os produtos
  - `firebird_client.get_product_by_code(code)` - Busca produto específico
- **Sincronização:** Via `sync-service` (scheduler)

#### Clientes
- **Fonte:** Tabelas `PESSOA`, `PESSOAFISICA`, `PESSOAJURIDICA`, `ENDERECO`, `FONE` do Firebird
- **Destino:** Tabela `customers` no PostgreSQL
- **Status:** ✅ Implementado
- **Métodos:**
  - `firebird_client.get_customer_by_phone(phone)` - Busca por telefone
- **Sincronização:** Busca automática quando necessário (não há sync automático de todos)

#### Estoque
- **Fonte:** Tabela `ITEMSALDO` do Firebird
- **Destino:** Eventos Redis para `inventory-service`
- **Status:** ✅ Implementado
- **Métodos:**
  - `firebird_client.get_stock_levels(estlocal_id, esttipo_id, year, month)`
- **Sincronização:** Via `sync-service` (scheduler)

### 2. Exportação (PostgreSQL → Firebird)

#### Pedidos
- **Fonte:** Tabela `orders` + `order_items` no PostgreSQL
- **Destino:** Tabelas `TRADE` + `TRADEITEM` no Firebird
- **Status:** ✅ Implementado
- **Método:**
  - `export_order_to_firebird(order_id)` - Exporta pedido específico
- **Trigger:** Automático quando pedido é marcado como `DELIVERED` (se configurado)

---

## 🔍 Análise Detalhada

### Arquivos Principais

1. **`backend/app/integrations/firebird.py`**
   - Cliente Firebird para leitura (importação)
   - Métodos: `get_products()`, `get_customer_by_phone()`, `get_stock_levels()`

2. **`backend/app/services/firebird_export_service.py`**
   - Serviço de exportação de pedidos
   - Classe: `FirebirdOrderExporter`
   - Método: `export_order_to_firebird(order_id)`

3. **`backend/services/sync-service/app/sync/scheduler.py`**
   - Sincronização automática de produtos e estoque
   - Executa periodicamente (configurável)

4. **`backend/app/api/orders.py`**
   - Endpoint: `POST /api/orders/{order_id}/export-firebird`
   - Trigger automático quando pedido é entregue

### Configurações Necessárias

#### Variáveis de Ambiente (.env)

```bash
# Conexão Firebird
FIREBIRD_HOST=192.168.10.156
FIREBIRD_DATABASE=/var/firebird/Gas.fdb
FIREBIRD_USER=SYSDBA
FIREBIRD_PASSWORD=masterkey
FIREBIRD_CHARSET=UTF8

# Exportação de Pedidos
FIREBIRD_EXPORT_ON_DELIVERED=true  # ⚠️ IMPORTANTE: Habilitar exportação automática

# Configurações do TRADE (tabela de vendas no Firebird)
FIREBIRD_TRADE_TABLE=TRADE
FIREBIRD_TRADE_ITEM_TABLE=TRADEITEM
FIREBIRD_TRADE_ESTAB_ID=1  # ⚠️ ID do estabelecimento (verificar no Firebird)
FIREBIRD_TRADE_TIPOMOVEST_ID=1  # ⚠️ ID do tipo de movimento (verificar no Firebird)
FIREBIRD_TRADE_ESTLOCAL_ID=1  # ID do local de estoque
FIREBIRD_TRADE_BXESTOQUE=N  # Baixar estoque? (S/N)
FIREBIRD_TRADE_BXFINANC=N  # Baixar financeiro? (S/N)
```

### Validações e Requisitos

#### Para Exportação de Pedidos

1. **Pedido deve estar com status `DELIVERED`**
   - Código: `backend/app/services/firebird_export_service.py:309`

2. **Cliente deve ter `firebird_id`**
   - Se não tiver, tenta buscar pelo telefone
   - Se não encontrar, exportação falha

3. **Produtos devem existir no Firebird**
   - Cada item do pedido precisa ter `product_code` válido
   - Busca variações do código (ex: "P13" → ["P13", "P-13"])

4. **Idempotência**
   - Se pedido já tem `firebird_trade_id`, não exporta novamente
   - Código: `backend/app/services/firebird_export_service.py:305`

### Campos Mapeados

#### TRADE (Cabeçalho da Venda)
- `PESSOA_ID` → ID do cliente no Firebird
- `DTEMISSAO` → Data de criação do pedido
- `DTMOVTO` → Data de criação do pedido
- `TOTAL` → Valor total do pedido
- `CANCELADA` → 'N' (não cancelada)
- `BXESTOQUE` → Configurável (padrão: 'N')
- `BXFINANC` → Configurável (padrão: 'N')
- `ESTAB_ID` → Configurável (obrigatório se tabela tiver coluna)
- `TIPOMOVEST_ID` → Configurável (obrigatório se tabela tiver coluna)
- `ENTSAI` → 'S' (saída/venda)
- `OBS` → Observações do pedido (máx 500 chars)

#### TRADEITEM (Itens da Venda)
- `TRADE_ID` → ID do TRADE criado
- `ITEM_ID` → ID do produto no Firebird
- `QUANTIDADE` → Quantidade do item
- `PRECOTABELA` → Preço unitário
- `TOTAL` → Subtotal do item
- `ESTLOCAL_ID` → Configurável (padrão: 1)
- `SEQUENCIA` → Sequência do item (1, 2, 3...)

---

## ⚠️ O Que Pode Estar Faltando

### 1. Configurações

- [ ] `FIREBIRD_EXPORT_ON_DELIVERED=true` no .env
- [ ] `FIREBIRD_TRADE_ESTAB_ID` configurado (verificar no Firebird)
- [ ] `FIREBIRD_TRADE_TIPOMOVEST_ID` configurado (verificar no Firebird)

### 2. Sincronização de Dados

- [ ] Produtos sem `firebird_id` no PostgreSQL
- [ ] Clientes sem `firebird_id` no PostgreSQL
- [ ] Sincronização inicial de produtos e clientes

### 3. Pedidos Pendentes

- [ ] Pedidos entregues sem exportação
- [ ] Verificar erros de exportação (`firebird_export_error`)

### 4. Campos Adicionais (Opcional)

- [ ] `DOCUMENTO` e `SERIE` para NF-e (se necessário)
- [ ] Campos fiscais adicionais
- [ ] Integração com módulo fiscal do Firebird

---

## 🧪 Como Testar

### 1. Teste de Conexão

```bash
docker exec gas_backend python -c "
from app.integrations.firebird import firebird_client
print('Disponível:', firebird_client.is_available)
"
```

### 2. Teste de Importação

```bash
docker exec gas_backend python -c "
from app.integrations.firebird import firebird_client
products = firebird_client.get_products()
print(f'Produtos: {len(products)}')
customer = firebird_client.get_customer_by_phone('4133460102')
print(f'Cliente: {customer[\"name\"] if customer else \"Não encontrado\"}')
"
```

### 3. Teste de Exportação

```bash
# Executar script de teste completo
docker exec gas_backend python backend/scripts/test_firebird_integration.py
```

### 4. Exportação Manual de Pedido

```bash
# Via API
curl -X POST http://localhost:8000/api/orders/{order_id}/export-firebird \
  -H "Authorization: Bearer {token}"
```

---

## 📋 Checklist de Verificação

### Configuração
- [ ] Firebird está acessível
- [ ] Variáveis de ambiente configuradas
- [ ] `FIREBIRD_EXPORT_ON_DELIVERED=true`
- [ ] IDs de estabelecimento e tipo de movimento configurados

### Dados
- [ ] Produtos sincronizados (têm `firebird_id`)
- [ ] Clientes sincronizados (têm `firebird_id`)
- [ ] Estoque sendo atualizado

### Exportação
- [ ] Pedidos entregues são exportados automaticamente
- [ ] Erros de exportação são logados
- [ ] Pedidos têm `firebird_trade_id` após exportação

### Testes
- [ ] Conexão Firebird funciona
- [ ] Importação de produtos funciona
- [ ] Busca de clientes funciona
- [ ] Exportação de pedido funciona

---

## 🚀 Próximos Passos

1. **Executar script de teste:**
   ```bash
   docker exec gas_backend python backend/scripts/test_firebird_integration.py
   ```

2. **Verificar configurações:**
   - Confirmar valores de `ESTAB_ID` e `TIPOMOVEST_ID` no Firebird
   - Habilitar `FIREBIRD_EXPORT_ON_DELIVERED=true`

3. **Sincronizar dados:**
   - Executar sincronização inicial de produtos
   - Verificar clientes sem `firebird_id` e buscar no Firebird

4. **Exportar pedidos pendentes:**
   - Identificar pedidos entregues sem exportação
   - Exportar manualmente ou aguardar próxima entrega

5. **Monitorar:**
   - Verificar logs de exportação
   - Monitorar erros (`firebird_export_error`)
   - Validar dados no Firebird após exportação

---

## 📝 Notas Técnicas

### Idempotência
- Exportação não duplica pedidos (verifica `firebird_trade_id`)
- Tentativas são contadas (`firebird_export_attempts`)
- Erros são salvos (`firebird_export_error`)

### Tratamento de Erros
- Erros são logados e salvos no pedido
- Exportação não bloqueia o fluxo principal (best-effort)
- Retry manual via endpoint `/export-firebird`

### Performance
- Exportação é assíncrona (não bloqueia)
- Conexão Firebird é aberta/fechada por operação
- Queries otimizadas com índices

---

## 🔗 Referências

- `backend/app/integrations/firebird.py` - Cliente Firebird
- `backend/app/services/firebird_export_service.py` - Exportação
- `backend/services/sync-service/app/sync/scheduler.py` - Sincronização
- `backend/app/api/orders.py` - Endpoints de pedidos
- `docs/outros/INTEGRACAO_FIREBIRD_CONCLUIDA_20260127_192917.md` - Documentação anterior
