# ⚠️ Informações que Preciso do Firebird

Baseado no mapeamento, identifiquei que **já temos o essencial mapeado**, mas há **2 áreas que precisam de suas descobertas**:

---

## ✅ O que JÁ está Mapeado e Funcionando

1. ✅ **Produtos** (`ITEM` + `ITEMPRECO`) - Completo
2. ✅ **Clientes** (`PESSOA` + `PESSOAFISICA` + `PESSOAJURIDICA` + `ENDERECO` + `FONE`) - Completo
3. ✅ **Pontos de Venda** (`VPESSOAJURIDICA` + `VPESSOAFISICASIMPLES`) - Completo

---

## ⏳ O que Precisa de Suas Descobertas

### 1. **ESTOQUE** (ITEMSALDO) ⚠️

**Tabela descoberta:** `ITEMSALDO`

**Estrutura encontrada:**
- `ITEM_ID` - Produto
- `SALDO` - Quantidade em estoque
- `ANO` / `MES` - Período
- `ESTLOCAL_ID` - Local de estoque
- `ESTTIPO_ID` - Tipo de estoque

**O que preciso que você verifique:**

1. **Qual `ESTLOCAL_ID` é o estoque principal?**
   - Vi que existe `ESTLOCAL_ID = 1`, mas preciso confirmar
   - Pode haver múltiplos locais (depósito, loja, etc.)

2. **Qual `ESTTIPO_ID` usar para estoque disponível?**
   - Vi que existe `ESTTIPO_ID = 1`, mas preciso confirmar
   - Pode haver tipos diferentes (disponível, reservado, etc.)

3. **Como buscar o saldo mais recente?**
   - O saldo é por mês/ano (vi 2026, mês 1)
   - Preciso saber: sempre pegar o último mês? Ou há uma tabela com saldo atual?

4. **Existe estoque mínimo?**
   - Não vi campo de estoque mínimo na `ITEMSALDO`
   - Está em outra tabela? Ou no `ITEM`?

**Query que preciso ajustar:**
```sql
SELECT 
    I.REFERENCIA,
    ITS.SALDO
FROM ITEMSALDO ITS
JOIN ITEM I ON ITS.ITEM_ID = I.ID
WHERE ITS.ESTLOCAL_ID = ?  -- Qual ID?
  AND ITS.ESTTIPO_ID = ?   -- Qual ID?
  AND ITS.ANO = ?           -- Ano atual
  AND ITS.MES = ?           -- Mês atual
```

---

### 2. **EXPORTAR PEDIDOS** (TRADE + TRADEITEM) ⚠️

**Tabelas descobertas:**
- `TRADE` - Cabeçalho da venda/pedido
- `TRADEITEM` - Itens da venda

**Estrutura encontrada:**

**TRADE:**
- `ID` - Chave primária
- `PESSOA_ID` - Cliente
- `DTEMISSAO` - Data de emissão
- `TOTAL` - Valor total
- `CANCELADA` - Se está cancelada
- `BXESTOQUE` - Baixar estoque?
- `BXFINANC` - Baixar financeiro?

**TRADEITEM:**
- `TRADE_ID` - FK para TRADE
- `ITEM_ID` - Produto
- `QUANTIDADE` - Quantidade
- `PRECOTABELA` - Preço
- `TOTAL` - Subtotal

**O que preciso que você verifique:**

1. **Como criar uma nova venda?**
   - Quais campos são **obrigatórios** em `TRADE`?
   - Qual valor usar para `ENTSAI`? (Entrada/Saída)
   - Qual `TIPOMOVEST_ID` usar para venda?
   - Qual `ESTAB_ID` usar?

2. **Fluxo de status:**
   - Como marcar como "Pendente"?
   - Como marcar como "Faturado"?
   - Existe campo de status ou usa `CANCELADA`?

3. **Sequência de documentos:**
   - Como gerar `DOCUMENTO` e `SERIE`?
   - Existe tabela de sequência?

4. **Relacionamentos:**
   - `ENDERECO_ID` - Endereço de entrega?
   - `ENTREGA_ID` - Relacionado a entregas?
   - `VEICULO_ID` - Veículo de entrega?

**Query que preciso criar:**
```sql
-- Criar cabeçalho
INSERT INTO TRADE (
    ENTSAI, DOCUMENTO, SERIE, DTEMISSAO, DTMOVTO,
    PESSOA_ID, ENDERECO_ID, TIPOMOVEST_ID, ESTAB_ID,
    TOTAL, ...
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ...)

-- Criar itens
INSERT INTO TRADEITEM (
    TRADE_ID, SEQUENCIA, ITEM_ID, QUANTIDADE,
    PRECOTABELA, TOTAL, ESTLOCAL_ID
) VALUES (?, ?, ?, ?, ?, ?, ?)
```

---

### 3. **OUTRAS TABELAS ÚTEIS** (Opcional)

Se você descobrir outras tabelas importantes, me avise:

1. **Bairros para frete:**
   - Vi tabela `BAIRRO` - tem valores de frete?
   - Campo `FRETEVALOR` existe?

2. **Rotas de entrega:**
   - Vi tabela `ROTA` - como usar?
   - Relaciona com entregadores?

3. **Transportadores/Entregadores:**
   - Vi tabela `TRANSPORTADOR` - como relacionar?
   - Usado para entregas?

---

## 📋 Resumo do que Você Precisa Verificar

### Estoque (ITEMSALDO)
- [ ] Qual `ESTLOCAL_ID` = estoque principal?
- [ ] Qual `ESTTIPO_ID` = estoque disponível?
- [ ] Como buscar saldo atual? (último mês ou outra forma?)
- [ ] Onde fica estoque mínimo?

### Pedidos/Vendas (TRADE)
- [ ] Campos obrigatórios para criar venda
- [ ] Valores padrão para `ENTSAI`, `TIPOMOVEST_ID`, `ESTAB_ID`
- [ ] Como gerar `DOCUMENTO` e `SERIE`
- [ ] Fluxo de status (Pendente → Faturado)
- [ ] Como relacionar com endereço de entrega

---

## ✅ Próximos Passos Imediatos

1. ✅ **Configuração adicionada ao `.env`**
2. ⏳ **Reconstruir container** (fazer agora)
3. ⏳ **Testar produtos e clientes** (fazer agora)
4. ⏳ **Aguardar suas descobertas** sobre estoque e pedidos

---

## 🧪 Comandos para Testar (Após Reconstruir)

```bash
# Testar conexão
docker exec gas_backend python -c "
from app.integrations.firebird import firebird_client
print('✅ Disponível:', firebird_client.is_available)
print('✅ Conexão:', firebird_client.test_connection())
"

# Testar produtos
docker exec gas_backend python -c "
from app.integrations.firebird import firebird_client
products = firebird_client.get_products()
print(f'📦 Produtos: {len(products)}')
for p in products[:3]:
    print(f'  {p[\"code\"]}: {p[\"name\"]} - R\$ {p[\"price\"]:.2f}')
"
```

---

**Aguardando suas descobertas sobre estoque e exportação de pedidos!** 🚀
