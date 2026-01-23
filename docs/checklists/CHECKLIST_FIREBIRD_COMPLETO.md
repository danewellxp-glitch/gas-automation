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

### 3. ⏳ **ESTOQUE** - PRECISA MAPEAR
- **Tabela:** `ITEMSALDO` (descoberta)
- **Status:** ⚠️ **PRECISA IMPLEMENTAR**
- **Campos necessários:**
  - ⏳ Código do produto (ITEM_ID → ITEM.REFERENCIA)
  - ⏳ Quantidade atual (SALDO)
  - ⏳ Estoque mínimo (verificar se existe)
  - ⏳ Local de estoque (ESTLOCAL_ID)
  - ⏳ Tipo de estoque (ESTTIPO_ID)

**Query sugerida:**
```sql
SELECT 
    I.REFERENCIA,
    IS.SALDO,
    IS.ESTLOCAL_ID,
    IS.ESTTIPO_ID,
    IS.ANO,
    IS.MES
FROM ITEMSALDO IS
JOIN ITEM I ON IS.ITEM_ID = I.ID
WHERE IS.ESTLOCAL_ID = 1  -- Estoque principal
  AND IS.ESTTIPO_ID = 1   -- Tipo principal
  AND IS.ANO = ?           -- Ano atual
  AND IS.MES = ?           -- Mês atual
```

**⚠️ AÇÃO NECESSÁRIA:** Você precisa verificar no banco:
- Qual `ESTLOCAL_ID` é o estoque principal?
- Qual `ESTTIPO_ID` usar?
- Como buscar o saldo mais recente (último mês/ano)?

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

## 🔍 Informações que Preciso de Você

### Estoque (ITEMSALDO)
1. Qual `ESTLOCAL_ID` representa o estoque principal?
2. Qual `ESTTIPO_ID` usar para estoque disponível?
3. Como buscar o saldo mais recente? (último mês/ano ou sempre atualiza?)
4. Existe campo de estoque mínimo? (ou está em outra tabela?)

### Pedidos/Vendas (TRADE)
1. Qual tabela armazena os **itens** de uma venda? (`TRADEITEM`?)
2. Como criar uma nova venda? (campos obrigatórios)
3. Qual o fluxo de status? (Pendente → Faturado → etc.)
4. Como relacionar com cliente? (PESSOA_ID já vi)
5. Como relacionar com produtos? (ITEM_ID?)

### Outras Tabelas
1. Existe tabela de **bairros** para cálculo de frete? (vi `BAIRRO`)
2. Existe tabela de **rotas** para entregas? (vi `ROTA`)
3. Existe tabela de **transportadores/entregadores**? (vi `TRANSPORTADOR`)

---

## ✅ O que Já Está Pronto

1. ✅ Conexão configurada
2. ✅ Produtos mapeados e implementados
3. ✅ Clientes mapeados e implementados
4. ✅ Pontos de venda mapeados e implementados
5. ✅ Conversão de centavos para reais
6. ✅ Busca de endereços
7. ✅ Busca de telefones

---

## 📝 Próximos Passos

1. **Configurar `.env`** (fazer agora)
2. **Reconstruir container** (fazer agora)
3. **Testar produtos e clientes** (fazer agora)
4. **Aguardar suas descobertas** sobre estoque e pedidos
5. **Implementar estoque** (após suas descobertas)
6. **Implementar exportação de pedidos** (após suas descobertas)
