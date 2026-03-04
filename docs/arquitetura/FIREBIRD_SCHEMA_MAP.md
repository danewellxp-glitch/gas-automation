# 🔥 Mapeamento do Schema Firebird - Gasmaster

## ✅ Conexão Testada

```
Host: 192.168.10.167
Database: /var/firebird/Gas.fdb
User: SYSDBA
Port: 3050
```

## 📊 Tabelas Principais Descobertas

### 1. **ITEM** (Produtos)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `REFERENCIA` (VARCHAR 20) - Código do produto (ex: "P-13", "P-20", "P-45")
- `NOME` (VARCHAR 40) - Nome completo do produto
- `REDUZIDO` (VARCHAR 15) - Nome reduzido
- `ITEMSERVICO` (CHAR 1) - 'I'=Item, 'V'=Vasilhame, 'S'=Serviço
- `PESOLIQ` (INTEGER) - Peso líquido em kg
- `PESOBRUTO` (INTEGER) - Peso bruto em kg
- `CONTESTOQUE` (CHAR 1) - 'S'=Controla estoque, 'N'=Não controla
- `IS_BLOQUEARVENDA` (CHAR 1) - 'S'=Bloqueado, 'N'=Liberado
- `CLASTRIB` (VARCHAR 5) - Classificação tributária (ex: "GAS", "AGUA", "IMOB")

**Exemplo de dados:**
```python
{
  'ID': 1,
  'REFERENCIA': 'P-13',
  'NOME': 'GLP ENVAZADO EM BOTIJÃO P13 KG',
  'REDUZIDO': 'GLP 13 Kg',
  'PESOLIQ': 13,
  'ITEMSERVICO': 'I',
  'CONTESTOQUE': 'S'
}
```

**Query para produtos ativos:**
```sql
SELECT 
    I.ID,
    I.REFERENCIA,
    I.NOME,
    I.REDUZIDO,
    I.PESOLIQ,
    I.PESOBRUTO,
    I.ITEMSERVICO,
    I.CONTESTOQUE,
    I.IS_BLOQUEARVENDA,
    I.CLASTRIB
FROM ITEM I
WHERE I.ITEMSERVICO = 'I'  -- Apenas itens (não vasilhame)
  AND I.IS_BLOQUEARVENDA = 'N'  -- Apenas não bloqueados
  AND I.CONTESTOQUE = 'S'  -- Que controlam estoque
ORDER BY I.REFERENCIA
```

---

### 2. **ITEMPRECO** (Preços dos Produtos)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `ITEM_ID` (INTEGER) - FK para ITEM
- `PRECO` (BIGINT) - Preço em **centavos** (dividir por 100 para reais)
- `DATAREAJ` (DATE) - Data do reajuste
- `TIPOPRECO_ID` (INTEGER) - Tipo de preço (1=Padrão)

**Query para preço atual:**
```sql
SELECT 
    IP.ITEM_ID,
    IP.PRECO / 100.0 AS PRECO_REAIS,  -- Converter centavos para reais
    IP.DATAREAJ,
    IP.TIPOPRECO_ID
FROM ITEMPRECO IP
WHERE IP.ITEM_ID = ?  -- ID do item
  AND IP.TIPOPRECO_ID = 1  -- Preço padrão
ORDER BY IP.DATAREAJ DESC
ROWS 1  -- Pegar apenas o mais recente
```

**Query combinada (Produtos com preços):**
```sql
SELECT 
    I.ID,
    I.REFERENCIA,
    I.NOME,
    I.REDUZIDO,
    I.PESOLIQ,
    IP.PRECO / 100.0 AS PRECO,
    IP.DATAREAJ AS PRECO_DATA
FROM ITEM I
LEFT JOIN (
    SELECT ITEM_ID, PRECO, DATAREAJ,
           ROW_NUMBER() OVER (PARTITION BY ITEM_ID ORDER BY DATAREAJ DESC) AS RN
    FROM ITEMPRECO
    WHERE TIPOPRECO_ID = 1
) IP ON I.ID = IP.ITEM_ID AND IP.RN = 1
WHERE I.ITEMSERVICO = 'I'
  AND I.IS_BLOQUEARVENDA = 'N'
  AND I.CONTESTOQUE = 'S'
ORDER BY I.REFERENCIA
```

---

### 3. **PESSOA** (Clientes/Pessoas)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `NOME` (VARCHAR 60) - Nome completo
- `PESSOANOME` (VARCHAR 60) - Nome da pessoa
- `EMAIL` (VARCHAR 150) - Email
- `NUMEROSMS` (VARCHAR 15) - Telefone para SMS
- `FISJUR` (CHAR 1) - 'F'=Física, 'J'=Jurídica
- `DTINATIVO` (DATE) - Data de inativação (NULL = ativo)
- `SITPESSOA_ID` (INTEGER) - Situação da pessoa

**Query para clientes ativos:**
```sql
SELECT 
    P.ID,
    P.NOME,
    P.PESSOANOME,
    P.EMAIL,
    P.NUMEROSMS,
    P.FISJUR,
    P.DTINATIVO
FROM PESSOA P
WHERE P.DTINATIVO IS NULL  -- Apenas ativos
ORDER BY P.NOME
```

---

### 4. **VFONE** (View de Telefones)

**Estrutura:**
- `FONE_ID` (INTEGER) - ID do telefone
- `NUMERO` (VARCHAR) - Número do telefone
- `FONETIPO` (VARCHAR) - Tipo (RESIDENCIAL, CELULAR, etc.)

**Nota:** Parece ser uma view. Precisar verificar tabela base.

---

### 5. **CLIENTE** (Relação Cliente)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `PESSOA_ID` (INTEGER) - FK para PESSOA
- `LIMITE` (BIGINT) - Limite de crédito
- `FORMAPAGPADRAO` (VARCHAR 30) - Forma de pagamento padrão

**Query para buscar cliente por telefone:**
```sql
-- Precisar verificar tabela de telefones relacionada
SELECT 
    C.ID AS CLIENTE_ID,
    P.ID AS PESSOA_ID,
    P.NOME,
    P.EMAIL,
    P.NUMEROSMS AS TELEFONE
FROM CLIENTE C
JOIN PESSOA P ON C.PESSOA_ID = P.ID
WHERE P.NUMEROSMS LIKE ?  -- Buscar por telefone
   OR EXISTS (
       SELECT 1 FROM VFONE F 
       WHERE F.PESSOA_ID = P.ID 
       AND F.NUMERO LIKE ?
   )
```

---

## 🔍 Tabelas Relacionadas Importantes

- **BAIRRO**: Bairros de entrega
- **ITEMTIPO**: Tipos de item
- **TIPOPRECO**: Tipos de preço
- **TRADE**: Vendas/Pedidos (precisar mapear)

---

## ⚠️ Observações Importantes

1. **Preços estão em centavos**: Dividir por 100 para obter valor em reais
2. **Datas**: Usar formato TIMESTAMP/DATE do Firebird
3. **Case-sensitive**: Nomes de tabelas/colunas podem ser case-sensitive
4. **Ativos/Inativos**: 
   - Produtos: `IS_BLOQUEARVENDA = 'N'` e `CONTESTOQUE = 'S'`
   - Clientes: `DTINATIVO IS NULL`

---

## 📝 Próximos Passos

1. ✅ Mapeamento concluído
2. ⏳ Ajustar queries no código `backend/app/integrations/firebird.py`
3. ⏳ Testar busca de produtos
4. ⏳ Testar busca de clientes por telefone
5. ⏳ Criar script de sincronização inicial
