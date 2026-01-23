# 🔍 Relatório de Varredura - Tabelas Firebird vs Sistema

**Data:** 2026-01-21  
**Objetivo:** Identificar tabelas do Firebird usadas no sistema e possíveis tabelas faltantes

---

## 📊 RESUMO EXECUTIVO

### Tabelas Firebird Identificadas no Código: **15 tabelas**
### Views Firebird Identificadas: **3 views**
### Tabelas PostgreSQL do Sistema: **10 tabelas**
### Tabelas Firebird Potencialmente Faltantes: **~10-15 tabelas** (análise manual necessária)

---

## ✅ TABELAS FIREBIRD USADAS NO SISTEMA

### 1. **ITEM** (Produtos)
- **Uso:** Catálogo de produtos (botijões P13, P20, P45)
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 155-218, 220-269)
- **Colunas principais usadas:**
  - `ID`, `REFERENCIA`, `NOME`, `REDUZIDO`
  - `PESOLIQ`, `PESOBRUTO`
  - `ITEMSERVICO`, `CONTESTOQUE`, `IS_BLOQUEARVENDA`, `CLASTRIB`
- **Status:** ✅ **IMPLEMENTADO**

### 2. **ITEMPRECO** (Preços dos Produtos)
- **Uso:** Buscar preço atual dos produtos
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 167-176, 234-243)
- **Colunas principais usadas:**
  - `ITEM_ID`, `PRECO` (em centavos), `DATAREAJ`, `TIPOPRECO_ID`
- **Status:** ✅ **IMPLEMENTADO**
- **⚠️ IMPORTANTE:** Preços estão em centavos (dividir por 100)

### 3. **PESSOA** (Clientes/Pessoas - Tabela Principal)
- **Uso:** Buscar dados de clientes por telefone ou ID
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 294-326, 380-407)
- **Colunas principais usadas:**
  - `ID`, `NOME`, `PESSOANOME`, `EMAIL`, `NUMEROSMS`, `FISJUR`, `DTINATIVO`
- **Status:** ✅ **IMPLEMENTADO**

### 4. **PESSOAFISICA** (Dados de Pessoa Física)
- **Uso:** Buscar CPF de clientes
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 316, 401)
- **Colunas principais usadas:**
  - `PESSOA_ID`, `CPF`
- **Status:** ✅ **IMPLEMENTADO**

### 5. **PESSOAJURIDICA** (Dados de Pessoa Jurídica)
- **Uso:** Buscar CNPJ de clientes
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 317, 402)
- **Colunas principais usadas:**
  - `PESSOA_ID`, `CNPJ`, `INSCESTAD`
- **Status:** ✅ **IMPLEMENTADO**

### 6. **CLIENTE** (Relação de Cliente)
- **Uso:** Buscar limite de crédito e dados de cliente
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 315, 400)
- **Colunas principais usadas:**
  - `PESSOA_ID`, `LIMITE` (em centavos)
- **Status:** ✅ **IMPLEMENTADO**

### 7. **ENDERECO** (Endereços)
- **Uso:** Buscar endereço principal de entrega
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 318, 403)
- **Colunas principais usadas:**
  - `PESSOA_ID`, `ISCOBRANCA`, `LOGRADOURO`, `NUMERO`, `COMPLEMENTO`, `BAIRRO`, `CEP`, `CIDADE_ID`
- **Status:** ✅ **IMPLEMENTADO**
- **⚠️ IMPORTANTE:** Usar `ISCOBRANCA = 'S'` para endereço principal

### 8. **FONE** (Telefones)
- **Uso:** Buscar cliente por telefone
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 319, 404)
- **Colunas principais usadas:**
  - `PESSOA_ID`, `NUMERO`, `NUMEROPURO` (telefone limpo)
- **Status:** ✅ **IMPLEMENTADO**
- **⚠️ IMPORTANTE:** Usar `NUMEROPURO` para busca (apenas números)

### 9. **ENTREGADORES** (Entregadores)
- **Uso:** Listar entregadores disponíveis
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 462-490)
- **Colunas principais usadas:**
  - `CODIGO`, `NOME`, `TELEFONE`, `ATIVO`
- **Status:** ✅ **IMPLEMENTADO**

### 10. **ITEMSALDO** (Estoque)
- **Uso:** Consultar níveis de estoque por produto
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 565-628)
- **Colunas principais usadas:**
  - `ITEM_ID`, `SALDO`, `ANO`, `MES`, `ESTLOCAL_ID`, `ESTTIPO_ID`
- **Status:** ✅ **IMPLEMENTADO**

### 11. **ROTA** (Rotas de Entrega)
- **Uso:** Listar rotas de entrega
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 632-666)
- **Colunas principais usadas:**
  - `ID`, `NOME`
- **Status:** ✅ **IMPLEMENTADO**

### 12. **ROTAPESSOA** (Clientes por Rota)
- **Uso:** Buscar clientes de uma rota específica
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 648, 687-691)
- **Colunas principais usadas:**
  - `ROTA_ID`, `PESSOA_ID`, `POSICAO`
- **Status:** ✅ **IMPLEMENTADO**

### 13. **VEICULO** (Veículos de Entrega)
- **Uso:** Listar veículos disponíveis para entrega
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 709-758)
- **Colunas principais usadas:**
  - `ID`, `NOME`, `PLACA`, `PROPRIO`, `ESTAB_ID`, `TIPOVEIC_ID`, `RENAVAM`, `CHASSI`
- **Status:** ✅ **IMPLEMENTADO**

---

## 📋 VIEWS FIREBIRD USADAS

### 1. **VPESSOAJURIDICA** (Pontos de Venda - Jurídica)
- **Uso:** Listar pontos de venda (pessoas jurídicas)
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 510-536, 768-794)
- **Colunas principais:**
  - `PESSOA_ID`, `PESSOANOME`, `POPULAR`, `CNPJ`, `INSCESTAD`, `ATIVIDADENOME`, `DTCAD`
- **Status:** ✅ **IMPLEMENTADO**

### 2. **VPESSOAFISICASIMPLES** (Pontos de Venda - Física)
- **Uso:** Listar pontos de venda (pessoas físicas)
- **Localização no código:** `backend/app/integrations/firebird.py` (linhas 540-559, 797-815)
- **Colunas principais:**
  - `ID`, `NOME`, `POPULAR`
- **Status:** ✅ **IMPLEMENTADO**

### 3. **RDB$DATABASE** (Sistema Firebird)
- **Uso:** Teste de conexão
- **Localização no código:** `backend/app/integrations/firebird.py` (linha 843)
- **Status:** ✅ **IMPLEMENTADO**

---

## 🗄️ TABELAS POSTGRESQL DO SISTEMA

### Tabelas Principais (10 tabelas):

1. **users** - Usuários do sistema (operadores, admins)
2. **customers** - Clientes (sincronizados do Firebird)
3. **products** - Produtos (sincronizados do Firebird)
4. **orders** - Pedidos criados via WhatsApp
5. **order_items** - Itens dos pedidos
6. **payments** - Pagamentos (integração Asaas)
7. **deliveries** - Entregas (rastreamento)
8. **drivers** - Entregadores
9. **driver_time_logs** - Logs de tempo dos entregadores
10. **event_logs** - Logs de eventos do sistema

### Tabelas de Autenticação:
- **conversation** - Conversas WhatsApp
- **message** - Mensagens das conversas
- **auditlog** - Logs de auditoria
- **botinteraction** - Interações com bot
- **botcontext** - Contexto das conversas

---

## ⚠️ TABELAS FIREBIRD POTENCIALMENTE FALTANTES

### 🔴 **CRÍTICAS** (Provavelmente necessárias para funcionalidades futuras):

#### 1. **TRADE / VENDA / PEDIDO** (Pedidos/Vendas)
- **Motivo:** Sistema precisa exportar pedidos para faturamento no Firebird
- **Possíveis nomes:** `TRADE`, `VENDA`, `PEDIDO`, `ORCAMENTO`
- **Uso esperado:** Exportar pedidos criados no sistema para o Firebird
- **Status:** ❌ **NÃO IMPLEMENTADO** (código tem placeholder em `sync-service`)

#### 2. **TRADEITEM / VENDAITEM / PEDIDOITEM** (Itens de Pedido)
- **Motivo:** Itens dos pedidos para exportação
- **Possíveis nomes:** `TRADEITEM`, `VENDAITEM`, `PEDIDOITEM`, `ORCAMENTOITEM`
- **Status:** ❌ **NÃO IMPLEMENTADO**

#### 3. **BAIRRO** (Bairros)
- **Motivo:** Sistema usa `delivery_bairro` para alocação de entregadores
- **Uso esperado:** Listar bairros disponíveis, validar bairros
- **Status:** ⚠️ **PARCIALMENTE USADO** (referenciado em `ENDERECO.BAIRRO_ID`)

#### 4. **CIDADE** (Cidades)
- **Motivo:** Sistema usa endereços com cidade
- **Uso esperado:** Validar/mapear cidades
- **Status:** ⚠️ **PARCIALMENTE USADO** (referenciado em `ENDERECO.CIDADE_ID`)

#### 5. **ESTAB** / **ESTABELECIMENTO** (Estabelecimentos)
- **Motivo:** Sistema pode precisar identificar pontos de venda
- **Uso esperado:** Filtrar por estabelecimento
- **Status:** ⚠️ **PARCIALMENTE USADO** (referenciado em `PESSOA.ESTAB_ID`, `VEICULO.ESTAB_ID`)

### 🟡 **IMPORTANTES** (Podem ser úteis):

#### 6. **TIPOPRECO** (Tipos de Preço)
- **Motivo:** Sistema usa `TIPOPRECO_ID = 1` (hardcoded)
- **Uso esperado:** Validar tipos de preço disponíveis
- **Status:** ⚠️ **HARDCODED** (valor 1 fixo no código)

#### 7. **ESTLOCAL** (Locais de Estoque)
- **Motivo:** Sistema usa `ESTLOCAL_ID = 1` (hardcoded)
- **Uso esperado:** Listar locais de estoque disponíveis
- **Status:** ⚠️ **HARDCODED** (valor 1 fixo no código)

#### 8. **ESTTIPO** (Tipos de Estoque)
- **Motivo:** Sistema usa `ESTTIPO_ID = 1` (hardcoded)
- **Uso esperado:** Listar tipos de estoque (Físico, Fiscal, etc.)
- **Status:** ⚠️ **HARDCODED** (valor 1 fixo no código)

#### 9. **TIPOVEIC** / **TIPOVEICULO** (Tipos de Veículo)
- **Motivo:** Sistema busca veículos mas não valida tipo
- **Uso esperado:** Filtrar veículos por tipo
- **Status:** ⚠️ **PARCIALMENTE USADO** (referenciado em `VEICULO.TIPOVEIC_ID`)

#### 10. **FORMAPAG** / **FORMAPAGAMENTO** (Formas de Pagamento)
- **Motivo:** Sistema pode precisar sincronizar formas de pagamento
- **Uso esperado:** Validar formas de pagamento aceitas
- **Status:** ⚠️ **PARCIALMENTE USADO** (referenciado em `CLIENTE.FORMAPAGPADRAO`)

### 🟢 **OPCIONAIS** (Pode não ser necessário):

#### 11. **ITEMTIPO** (Tipos de Item)
- **Motivo:** Sistema filtra apenas `ITEMSERVICO = 'I'`
- **Uso esperado:** Classificar tipos de item
- **Status:** ⚠️ **PARCIALMENTE USADO** (filtro hardcoded)

#### 12. **FONETIPO** / **TIPOFONE** (Tipos de Telefone)
- **Motivo:** Sistema busca telefones mas não valida tipo
- **Uso esperado:** Filtrar por tipo de telefone (celular, fixo)
- **Status:** ⚠️ **PARCIALMENTE USADO** (referenciado em `FONE.TIPOFONE_ID`)

#### 13. **SITPESSOA** (Situação da Pessoa)
- **Motivo:** Sistema filtra apenas `DTINATIVO IS NULL`
- **Uso esperado:** Validar situações de pessoa
- **Status:** ⚠️ **PARCIALMENTE USADO** (referenciado em `PESSOA.SITPESSOA_ID`)

---

## 📝 ANÁLISE DETALHADA POR FUNCIONALIDADE

### ✅ **FUNCIONALIDADES IMPLEMENTADAS:**

1. **Sincronização de Produtos** ✅
   - Tabelas: `ITEM`, `ITEMPRECO`
   - Status: Funcional

2. **Busca de Clientes** ✅
   - Tabelas: `PESSOA`, `PESSOAFISICA`, `PESSOAJURIDICA`, `CLIENTE`, `ENDERECO`, `FONE`
   - Status: Funcional

3. **Consulta de Estoque** ✅
   - Tabelas: `ITEMSALDO`, `ITEM`
   - Status: Funcional

4. **Gestão de Entregadores** ✅
   - Tabelas: `ENTREGADORES`
   - Status: Funcional

5. **Gestão de Rotas** ✅
   - Tabelas: `ROTA`, `ROTAPESSOA`
   - Status: Funcional

6. **Gestão de Veículos** ✅
   - Tabelas: `VEICULO`
   - Status: Funcional

7. **Pontos de Venda** ✅
   - Views: `VPESSOAJURIDICA`, `VPESSOAFISICASIMPLES`
   - Status: Funcional

### ❌ **FUNCIONALIDADES NÃO IMPLEMENTADAS:**

1. **Exportação de Pedidos** ❌
   - Tabelas necessárias: `TRADE`/`VENDA`/`PEDIDO`, `TRADEITEM`/`VENDAITEM`
   - Status: Código placeholder existe mas não implementado
   - **AÇÃO NECESSÁRIA:** Verificar nome exato das tabelas no Firebird

2. **Validação de Bairros** ⚠️
   - Tabela: `BAIRRO`
   - Status: Referenciada mas não consultada diretamente
   - **AÇÃO NECESSÁRIA:** Verificar se precisa listar bairros

3. **Validação de Cidades** ⚠️
   - Tabela: `CIDADE`
   - Status: Referenciada mas não consultada diretamente
   - **AÇÃO NECESSÁRIA:** Verificar se precisa listar cidades

---

## 🔍 QUERIES PARA ANÁLISE MANUAL NO FIREBIRD

Execute estas queries no Firebird para identificar tabelas faltantes:

### 1. Listar todas as tabelas do sistema:
```sql
SELECT RDB$RELATION_NAME
FROM RDB$RELATIONS
WHERE RDB$SYSTEM_FLAG = 0
  AND RDB$RELATION_TYPE = 0
ORDER BY RDB$RELATION_NAME;
```

### 2. Buscar tabelas relacionadas a pedidos/vendas:
```sql
SELECT RDB$RELATION_NAME
FROM RDB$RELATIONS
WHERE RDB$SYSTEM_FLAG = 0
  AND RDB$RELATION_TYPE = 0
  AND (RDB$RELATION_NAME CONTAINING 'TRADE'
    OR RDB$RELATION_NAME CONTAINING 'VENDA'
    OR RDB$RELATION_NAME CONTAINING 'PEDIDO'
    OR RDB$RELATION_NAME CONTAINING 'ORCAMENTO')
ORDER BY RDB$RELATION_NAME;
```

### 3. Buscar tabelas de configuração:
```sql
SELECT RDB$RELATION_NAME
FROM RDB$RELATIONS
WHERE RDB$SYSTEM_FLAG = 0
  AND RDB$RELATION_TYPE = 0
  AND (RDB$RELATION_NAME CONTAINING 'TIPO'
    OR RDB$RELATION_NAME CONTAINING 'CONFIG'
    OR RDB$RELATION_NAME CONTAINING 'PARAM')
ORDER BY RDB$RELATION_NAME;
```

### 4. Verificar estrutura de uma tabela específica:
```sql
SELECT 
    RF.RDB$FIELD_NAME AS COLUMN_NAME,
    RF.RDB$FIELD_SOURCE AS DATA_TYPE,
    RF.RDB$NULL_FLAG AS IS_NULLABLE
FROM RDB$RELATION_FIELDS RF
WHERE RF.RDB$RELATION_NAME = 'NOME_DA_TABELA'
ORDER BY RF.RDB$FIELD_POSITION;
```

### 5. Listar todas as views:
```sql
SELECT RDB$RELATION_NAME
FROM RDB$RELATIONS
WHERE RDB$SYSTEM_FLAG = 0
  AND RDB$RELATION_TYPE = 1  -- Views
ORDER BY RDB$RELATION_NAME;
```

---

## 📋 CHECKLIST PARA ANÁLISE MANUAL

### Tabelas para verificar no Firebird:

- [ ] **TRADE** ou **VENDA** ou **PEDIDO** - Tabela de pedidos/vendas
- [ ] **TRADEITEM** ou **VENDAITEM** ou **PEDIDOITEM** - Itens de pedido
- [ ] **BAIRRO** - Tabela de bairros
- [ ] **CIDADE** - Tabela de cidades
- [ ] **ESTAB** ou **ESTABELECIMENTO** - Estabelecimentos
- [ ] **TIPOPRECO** - Tipos de preço
- [ ] **ESTLOCAL** - Locais de estoque
- [ ] **ESTTIPO** - Tipos de estoque
- [ ] **TIPOVEIC** ou **TIPOVEICULO** - Tipos de veículo
- [ ] **FORMAPAG** ou **FORMAPAGAMENTO** - Formas de pagamento
- [ ] **ITEMTIPO** - Tipos de item
- [ ] **FONETIPO** ou **TIPOFONE** - Tipos de telefone
- [ ] **SITPESSOA** - Situações de pessoa

### Verificar também:

- [ ] Tabelas de histórico/auditoria
- [ ] Tabelas de configuração do sistema
- [ ] Tabelas de integração com outros sistemas
- [ ] Tabelas de relatórios/estatísticas

---

## 🎯 RECOMENDAÇÕES

### Prioridade ALTA:
1. **Identificar tabela de pedidos/vendas** no Firebird para implementar exportação
2. **Mapear estrutura completa** das tabelas de pedido (cabeçalho + itens)
3. **Validar nomes exatos** das tabelas (Firebird pode usar nomes diferentes)

### Prioridade MÉDIA:
1. **Implementar consulta a BAIRRO** se necessário para validação
2. **Implementar consulta a CIDADE** se necessário para validação
3. **Substituir valores hardcoded** (TIPOPRECO_ID=1, ESTLOCAL_ID=1) por consultas dinâmicas

### Prioridade BAIXA:
1. **Implementar validações** usando tabelas de configuração (TIPOVEIC, FONETIPO, etc.)
2. **Adicionar logs** de sincronização mais detalhados
3. **Criar views** no PostgreSQL para facilitar consultas

---

## 📊 ESTATÍSTICAS

- **Tabelas Firebird usadas:** 13 tabelas
- **Views Firebird usadas:** 3 views
- **Tabelas PostgreSQL:** 10 tabelas principais + 5 tabelas de autenticação
- **Tabelas potencialmente faltantes:** ~10-15 tabelas
- **Funcionalidades implementadas:** 7/9 (78%)
- **Funcionalidades faltantes:** 2/9 (22%)

---

## 🔗 ARQUIVOS RELEVANTES

- **Integração Firebird:** `backend/app/integrations/firebird.py`
- **Sync Service:** `backend/services/sync-service/app/sync/firebird_client.py`
- **Schema Firebird:** `FIREBIRD_SCHEMA_COMPLETO.md`
- **Mapeamento:** `FIREBIRD_SCHEMA_MAP.md`
- **Modelos PostgreSQL:** `backend/app/models/`
- **Migrations:** `backend/alembic/versions/001_initial_schema.py`

---

**Próximos Passos:**
1. Executar queries de análise no Firebird
2. Documentar estrutura das tabelas faltantes
3. Implementar exportação de pedidos
4. Substituir valores hardcoded por consultas dinâmicas
