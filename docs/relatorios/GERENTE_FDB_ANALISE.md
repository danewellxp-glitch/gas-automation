# 📊 Análise Completa - Gerente.fdb

## 🎯 Descobertas Importantes

O banco **Gerente.fdb** é o banco **principal** e mais completo do sistema Gasmaster!

### Comparação Gas.fdb vs Gerente.fdb

| Tabela | Gas.fdb | Gerente.fdb | Diferença |
|--------|---------|-------------|-----------|
| PESSOA | 131.899 | 330.128 | +198.229 (mais completo) |
| CLIENTE | 131.892 | 330.094 | +198.202 (mais completo) |
| TRADE | 728.242 | 601.868 | Gas.fdb tem mais histórico |
| ITEM | 61 | 71 | Gerente.fdb tem mais produtos |

**Conclusão:** `Gerente.fdb` é o banco principal para operações atuais!

---

## ✅ Tabelas Importantes Descobertas

### 1. **ESTOQUE** - Resolvido! ✅

**ESTLOCAL (Locais de Estoque):**
- ID 1: **GASMASTER - Fiscal** ← **ESTOQUE PRINCIPAL**
- ID 3: DURAGAS PARANAGUA
- ID 6: TUPAGAZ
- ID 8: SILVA GAS
- ... (16 locais no total)

**ESTTIPO (Tipos de Estoque):**
- ID 1: **FISICO** ← **ESTOQUE DISPONÍVEL**
- ID 4: Comodato Clientes
- ID 5: Remessa Fornecedor
- ID 6: Avariado
- ... (12 tipos no total)

**Query de Estoque:**
```sql
SELECT 
    I.REFERENCIA,
    I.NOME,
    ITS.SALDO,
    ITS.ANO,
    ITS.MES
FROM ITEMSALDO ITS
JOIN ITEM I ON ITS.ITEM_ID = I.ID
WHERE ITS.ESTLOCAL_ID = 1      -- GASMASTER - Fiscal (estoque principal)
  AND ITS.ESTTIPO_ID = 1       -- FISICO (estoque disponível)
  AND ITS.ANO = 2026           -- Ano atual
  AND ITS.MES = 1              -- Mês atual
ORDER BY I.REFERENCIA
```

**Exemplo de dados:**
- P-13: Saldo 420 (Local: 8, Tipo: 1)
- P-13: Saldo 2027 (Local: 6, Tipo: 1)
- P-13: Saldo -25653 (Local: 3, Tipo: 1)

---

### 2. **ROTAS DE ENTREGA** ✅

**ROTA:**
- ID 1: FAZENDA
- ID 2: XAXIM
- ID 3: CAJURU / PINHAIS
- ID 4: ROTA CAJURU, PINHAS, PIRAQUARA
- ID 5: Rota Geremias

**ROTAPESSOA (Clientes por Rota):**
- Rota 3: Pessoa 112 - Posição 1
- Rota 2: Pessoa 23735 - Posição 11
- Rota 3: Pessoa 27595 - Posição 26

**Estrutura:**
```sql
SELECT 
    R.ID,
    R.NOME,
    COUNT(RP.PESSOA_ID) AS TOTAL_CLIENTES
FROM ROTA R
LEFT JOIN ROTAPESSOA RP ON R.ID = RP.ROTA_ID
GROUP BY R.ID, R.NOME
```

---

### 3. **VEÍCULOS DE ENTREGA** ✅

**VEICULO:**
- HR - Placa: ABD9005 (Próprio: S)
- O Proprio cliente veio retirar - Placa: AAA9999 (Próprio: S)
- Mercedes 915 C - Placa: ABD4008 (Próprio: S)

**Colunas principais:**
- ID, NOME, PLACA, PROPRIO, ESTAB_ID, TIPOVEIC_ID, RENAVAM, CHASSI, TARA, CAPKG

---

### 4. **TRANSPORTADORES** ✅

**TRANSPORTADOR:**
- ID: 19067, Pessoa: ?
- ID: 36463, Pessoa: ?

**Estrutura:**
- ID, PESSOA_ID (relaciona com PESSOA)

---

### 5. **PEDIDOS/VENDAS** (TRADE + TRADEITEM) ✅

**Estrutura igual ao Gas.fdb:**
- TRADE: Cabeçalho da venda
- TRADEITEM: Itens da venda

**Dados mais recentes:**
- ID: 1750090, Cliente: 333698, Total: 130, Data: 2026-01-19
- ID: 1750092, Cliente: 314686, Total: 190, Data: 2026-01-19

---

## 📋 Tabelas Totais no Gerente.fdb

**272 tabelas** no total, incluindo:

### Operacionais:
- ✅ ROTA, ROTAPESSOA - Rotas de entrega
- ✅ VEICULO, TRANSPORTADOR - Veículos e transportadores
- ✅ TRADE, TRADEITEM - Pedidos/vendas
- ✅ ITEMSALDO - Estoque
- ✅ ESTLOCAL, ESTTIPO - Locais e tipos de estoque
- ✅ PESSOA, CLIENTE - Clientes
- ✅ ITEM, ITEMPRECO - Produtos e preços

### Financeiro:
- TITULO, TITULOBAIXA - Títulos a receber/pagar
- LANCTO - Lançamentos financeiros
- FORMAPAG - Formas de pagamento

### Fiscal:
- NFETRADE - Notas fiscais
- MDFE - Manifesto de Documentos Fiscais Eletrônicos
- CTRC - Conhecimento de Transporte Rodoviário de Cargas

### Outros:
- AGENDA - Agendamentos
- AVARIA - Avarias
- BRINDE - Brindes
- CONVENIO - Convênios
- META - Metas
- RONDA - Rondas

---

## 🔧 Próximos Passos

### 1. Atualizar Integração para Usar Gerente.fdb

**Configuração:**
```bash
# .env
FIREBIRD_HOST=192.168.10.167
FIREBIRD_DATABASE=/var/firebird/Gerente.fdb  # Mudar de Gas.fdb para Gerente.fdb
FIREBIRD_USER=SYSDBA
FIREBIRD_PASSWORD=masterkey
```

### 2. Implementar Métodos

**Estoque:**
```python
def get_stock_levels(self) -> List[Dict]:
    query = """
        SELECT 
            I.REFERENCIA,
            I.NOME,
            ITS.SALDO,
            ITS.ANO,
            ITS.MES
        FROM ITEMSALDO ITS
        JOIN ITEM I ON ITS.ITEM_ID = I.ID
        WHERE ITS.ESTLOCAL_ID = 1      -- GASMASTER - Fiscal
          AND ITS.ESTTIPO_ID = 1      -- FISICO
          AND ITS.ANO = ?              -- Ano atual
          AND ITS.MES = ?              -- Mês atual
        ORDER BY I.REFERENCIA
    """
```

**Rotas:**
```python
def get_routes(self) -> List[Dict]:
    query = """
        SELECT 
            R.ID,
            R.NOME,
            COUNT(RP.PESSOA_ID) AS TOTAL_CLIENTES
        FROM ROTA R
        LEFT JOIN ROTAPESSOA RP ON R.ID = RP.ROTA_ID
        GROUP BY R.ID, R.NOME
        ORDER BY R.NOME
    """
```

**Veículos:**
```python
def get_vehicles(self) -> List[Dict]:
    query = """
        SELECT 
            V.ID,
            V.NOME,
            V.PLACA,
            V.PROPRIO,
            V.ESTAB_ID
        FROM VEICULO V
        WHERE V.PROPRIO = 'S'  -- Apenas veículos próprios
        ORDER BY V.NOME
    """
```

---

## ✅ Resumo

1. ✅ **Gerente.fdb é o banco principal** (mais completo)
2. ✅ **Estoque resolvido:** ESTLOCAL_ID=1, ESTTIPO_ID=1
3. ✅ **Rotas descobertas:** ROTA + ROTAPESSOA
4. ✅ **Veículos descobertos:** VEICULO + TRANSPORTADOR
5. ⏳ **Próximo:** Atualizar integração para usar Gerente.fdb

---

## 📝 Observações

- **Gas.fdb** parece ser um banco histórico ou backup
- **Gerente.fdb** é o banco operacional atual
- Ambos têm estrutura similar, mas Gerente.fdb tem mais dados atuais
- Tabelas de rotas e veículos só existem no Gerente.fdb

**Recomendação:** Usar **Gerente.fdb** como banco principal!
