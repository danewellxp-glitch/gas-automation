# ✅ Checklist Completo - Integração Firebird

## 📋 O que o Sistema Precisa do Firebird

### 1. ✅ **PRODUTOS** - JÁ MAPEADO
- **Tabela:** `ITEM`
- **Preços:** `ITEMPRECO`
- **Status:** ✅ Implementado
- **Campos necessários:**
  - ✅ Código (REFERENCIA)
  - ✅ Nome (NOME)
  - ✅ Preço (ITEMPRECO.PRECO - em centavos)
  - ✅ Peso (PESOLIQ)
  - ✅ Status ativo (IS_BLOQUEARVENDA)

---

### 2. ✅ **CLIENTES** - JÁ MAPEADO
- **Tabela principal:** `PESSOA`
- **Dados físicos:** `PESSOAFISICA` (CPF)
- **Dados jurídicos:** `PESSOAJURIDICA` (CNPJ)
- **Endereços:** `ENDERECO` (ISCOBRANCA='S' = principal)
- **Telefones:** `FONE` (NUMEROPURO = telefone limpo)
- **Status:** ✅ Implementado
- **Campos necessários:**
  - ✅ Nome (PESSOA.NOME)
  - ✅ Telefone (FONE.NUMEROPURO)
  - ✅ Email (PESSOA.EMAIL)
  - ✅ CPF/CNPJ (PESSOAFISICA.CPF ou PESSOAJURIDICA.CNPJ)
  - ✅ Endereço completo (ENDERECO)

---

### 3. ✅ **ESTOQUE** - JÁ IMPLEMENTADO
- **Tabela:** `ITEMSALDO`
- **Status:** ✅ Implementado
- **Campos mapeados:**
  - ✅ Código do produto (ITEM_ID → ITEM.REFERENCIA)
  - ✅ Quantidade atual (SALDO)
  - ✅ Local de estoque (ESTLOCAL_ID = 1 padrão)
  - ✅ Tipo de estoque (ESTTIPO_ID = 1 padrão)
  - ✅ Período (ANO, MES)

**Query implementada:**
```sql
SELECT
    I.REFERENCIA,
    I.NOME,
    ITS.SALDO
FROM ITEMSALDO ITS
JOIN ITEM I ON ITS.ITEM_ID = I.ID
WHERE ITS.ESTLOCAL_ID = ?
  AND ITS.ESTTIPO_ID = ?
  AND ITS.ANO = ?
  AND ITS.MES = ?
ORDER BY I.REFERENCIA
```

**Arquivo:** `backend/services/sync-service/app/sync/firebird_client.py` - método `get_stock_levels()`

---

### 4. ⏳ **EXPORTAR PEDIDOS** - PRECISA MAPEAR
- **Tabela:** `TRADE` (descoberta - parece ser vendas)
- **Status:** ⚠️ **PRECISA IMPLEMENTAR**
- **Campos necessários para exportar:**
  - ⏳ Cabeçalho da venda (TRADE)
  - ⏳ Itens da venda (TRADEITEM?)
  - ⏳ Cliente (PESSOA_ID)
  - ⏳ Produtos (ITEM_ID)
  - ⏳ Quantidades e preços

**⚠️ AÇÃO NECESSÁRIA:** Você precisa verificar no banco:
- Como criar uma nova venda/pedido na tabela `TRADE`?
- Qual tabela armazena os itens? (`TRADEITEM`?)
- Quais campos são obrigatórios?
- Qual o fluxo de status de uma venda?

---

### 5. ✅ **PONTOS DE VENDA** - JÁ MAPEADO
- **Views:** `VPESSOAJURIDICA` e `VPESSOAFISICASIMPLES`
- **Status:** ✅ Implementado

---

## 🔍 Informações Pendentes (para exportação de pedidos)

### Pedidos/Vendas (TRADE)
1. Qual tabela armazena os **itens** de uma venda? (`TRADEITEM`?)
2. Como criar uma nova venda? (campos obrigatórios)
3. Qual o fluxo de status? (Pendente → Faturado → etc.)
4. Como relacionar com cliente? (PESSOA_ID já vi)
5. Como relacionar com produtos? (ITEM_ID?)

---

## ✅ O que Já Está Pronto

1. ✅ Conexão configurada (.env com host 192.168.10.156)
2. ✅ Produtos mapeados e implementados
3. ✅ Clientes mapeados e implementados
4. ✅ Pontos de venda mapeados e implementados
5. ✅ Conversão de centavos para reais
6. ✅ Busca de endereços
7. ✅ Busca de telefones (últimos 8 dígitos)
8. ✅ Busca por CEP + número
9. ✅ Estoque implementado (ITEMSALDO)
10. ✅ Integração com bot WhatsApp
11. ✅ Sync-service com schema correto

---

## 📝 Próximos Passos

1. ⏳ **Implementar exportação de pedidos** (tabela TRADE)
2. ⏳ **Configurar sincronização automática** (opcional)
