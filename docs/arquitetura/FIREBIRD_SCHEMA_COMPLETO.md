# 🔥 Schema Completo Firebird - Gasmaster

## ✅ Conexão

```
Host: 192.168.10.156
Database: /var/firebird/Gas.fdb
User: SYSDBA
Port: 3050
```

## 📊 Tabelas Principais

### 1. **ITEM** (Produtos)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `REFERENCIA` (VARCHAR 20) - Código do produto (ex: "P-13", "P-20", "P-45")
- `NOME` (VARCHAR 40) - Nome completo
- `REDUZIDO` (VARCHAR 15) - Nome reduzido
- `ITEMSERVICO` (CHAR 1) - 'I'=Item, 'V'=Vasilhame, 'S'=Serviço
- `PESOLIQ` (INTEGER) - Peso líquido em kg
- `PESOBRUTO` (INTEGER) - Peso bruto em kg
- `CONTESTOQUE` (CHAR 1) - 'S'=Controla estoque
- `IS_BLOQUEARVENDA` (CHAR 1) - 'N'=Ativo, 'S'=Bloqueado
- `CLASTRIB` (VARCHAR 5) - Classificação (ex: "GAS", "AGUA", "IMOB")

**Query para produtos ativos:**
```sql
SELECT 
    I.ID,
    I.REFERENCIA,
    I.NOME,
    I.REDUZIDO,
    I.PESOLIQ,
    (SELECT FIRST 1 IP.PRECO
     FROM ITEMPRECO IP
     WHERE IP.ITEM_ID = I.ID AND IP.TIPOPRECO_ID = 1
     ORDER BY IP.DATAREAJ DESC) AS PRECO
FROM ITEM I
WHERE I.ITEMSERVICO = 'I'
  AND I.IS_BLOQUEARVENDA = 'N'
  AND I.CONTESTOQUE = 'S'
ORDER BY I.REFERENCIA
```

---

### 2. **ITEMPRECO** (Preços)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `ITEM_ID` (INTEGER) - FK para ITEM
- `PRECO` (BIGINT) - Preço em **centavos** (dividir por 100)
- `DATAREAJ` (DATE) - Data do reajuste
- `TIPOPRECO_ID` (INTEGER) - Tipo de preço (1=Padrão)

**⚠️ IMPORTANTE:** Preços estão em centavos!

---

### 3. **PESSOA** (Clientes/Pessoas - Tabela Principal)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `NOME` (VARCHAR 60) - Nome completo
- `PESSOANOME` (VARCHAR 60) - Nome da pessoa
- `POPULAR` (VARCHAR 30) - Nome popular/apelido
- `EMAIL` (VARCHAR 150) - Email
- `NUMEROSMS` (VARCHAR 15) - Telefone para SMS
- `FISJUR` (CHAR 1) - 'F'=Física, 'J'=Jurídica
- `DTINATIVO` (DATE) - Data de inativação (NULL = ativo)
- `ESTAB_ID` (INTEGER) - Estabelecimento
- `DTCAD` (TIMESTAMP) - Data de cadastro

**Query para clientes ativos:**
```sql
SELECT 
    P.ID,
    P.NOME,
    P.PESSOANOME,
    P.EMAIL,
    P.NUMEROSMS,
    P.FISJUR
FROM PESSOA P
WHERE P.DTINATIVO IS NULL
ORDER BY P.NOME
```

---

### 4. **PESSOAFISICA** (Dados de Pessoa Física)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `PESSOA_ID` (INTEGER) - FK para PESSOA
- `CPF` (VARCHAR) - CPF
- `RG` (VARCHAR) - RG
- `DTNASC` (DATE) - Data de nascimento
- `SEXO` (CHAR) - Sexo
- `ESTCIVIL` (VARCHAR) - Estado civil

---

### 5. **PESSOAJURIDICA** (Dados de Pessoa Jurídica)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `PESSOA_ID` (INTEGER) - FK para PESSOA
- `CNPJ` (VARCHAR) - CNPJ
- `INSCESTAD` (VARCHAR) - Inscrição Estadual
- `IS_DEPOSITOGLP` (CHAR) - É depósito GLP?
- `REGANP` (VARCHAR) - Registro ANP
- `BANDEIRA` (VARCHAR) - Bandeira

---

### 6. **CLIENTE** (Relação de Cliente)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `PESSOA_ID` (INTEGER) - FK para PESSOA
- `LIMITE` (BIGINT) - Limite de crédito em **centavos**
- `FORMAPAGPADRAO` (VARCHAR 30) - Forma de pagamento padrão
- `CANALVENDAPADRAO` (INTEGER) - Canal de venda padrão

---

### 7. **ENDERECO** (Endereços)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `PESSOA_ID` (INTEGER) - FK para PESSOA
- `ISCOBRANCA` (CHAR) - 'S'=Endereço de cobrança/principal
- `LOGRADOURO` (VARCHAR) - Rua/Avenida
- `NUMERO` (VARCHAR) - Número
- `COMPLEMENTO` (VARCHAR) - Complemento
- `BAIRRO` (VARCHAR) - Bairro
- `BAIRRO_ID` (INTEGER) - FK para BAIRRO
- `CIDADE_ID` (INTEGER) - FK para CIDADE
- `CEP` (VARCHAR) - CEP
- `LATITUDE` (DOUBLE) - Latitude GPS
- `LONGITUDE` (DOUBLE) - Longitude GPS

**Query para endereço principal:**
```sql
SELECT * FROM ENDERECO
WHERE PESSOA_ID = ? AND ISCOBRANCA = 'S'
```

---

### 8. **FONE** (Telefones)

**Estrutura:**
- `ID` (INTEGER) - Chave primária
- `PESSOA_ID` (INTEGER) - FK para PESSOA
- `NUMERO` (VARCHAR) - Telefone formatado
- `NUMEROPURO` (VARCHAR) - Telefone limpo (apenas números)
- `TIPOFONE_ID` (INTEGER) - Tipo de telefone
- `IS_CONTATODELIV` (CHAR) - É contato para delivery?

**Query para buscar por telefone:**
```sql
SELECT * FROM FONE
WHERE NUMEROPURO LIKE ?
```

---

## 📋 Views Importantes

### 1. **VPESSOAJURIDICA** (Pontos de Venda - Jurídica)

**Colunas:**
- `PESSOA_ID` - ID da pessoa
- `PESSOANOME` - Nome completo
- `POPULAR` - Nome popular
- `CNPJ` - CNPJ
- `INSCESTAD` - Inscrição Estadual
- `ATIVIDADENOME` - Nome da atividade
- `DTCAD` - Data de cadastro

**Uso:** Listar pontos de venda (pessoas jurídicas)

---

### 2. **VPESSOAFISICASIMPLES** (Pontos de Venda - Física)

**Colunas:**
- `ID` - ID da pessoa
- `NOME` - Nome completo
- `POPULAR` - Nome popular

**Uso:** Listar pontos de venda (pessoas físicas)

---

### 3. **VCLIENTE** (View de Clientes)

**Colunas:**
- `PESSOA_ID` - ID da pessoa
- `PESSOANOME` - Nome
- `POPULAR` - Nome popular
- `LIMITE` - Limite de crédito
- `ESTAB_ID` - Estabelecimento

---

## 🔗 Relacionamentos

```
PESSOA (1) ──┬──> PESSOAFISICA (0..1)
            ├──> PESSOAJURIDICA (0..1)
            ├──> CLIENTE (0..1)
            ├──> ENDERECO (0..N) [ISCOBRANCA='S' = principal]
            └──> FONE (0..N) [NUMEROPURO = telefone limpo]

ITEM (1) ──> ITEMPRECO (0..N) [TIPOPRECO_ID=1, mais recente]
```

---

## ⚠️ Observações Importantes

1. **Preços em centavos**: Sempre dividir por 100
2. **Limites em centavos**: Sempre dividir por 100
3. **Endereço principal**: `ENDERECO.ISCOBRANCA = 'S'`
4. **Telefone limpo**: Usar `FONE.NUMEROPURO` para busca
5. **Clientes ativos**: `PESSOA.DTINATIVO IS NULL`
6. **Produtos ativos**: `ITEM.IS_BLOQUEARVENDA = 'N'` e `ITEM.CONTESTOQUE = 'S'`

---

## 📝 Queries Úteis

### Buscar cliente completo por telefone:
```sql
SELECT FIRST 1
    P.ID, P.NOME, P.EMAIL, P.FISJUR,
    PF.CPF, PJ.CNPJ,
    E.LOGRADOURO, E.NUMERO, E.BAIRRO, E.CEP,
    F.NUMERO AS TELEFONE
FROM PESSOA P
LEFT JOIN PESSOAFISICA PF ON PF.PESSOA_ID = P.ID
LEFT JOIN PESSOAJURIDICA PJ ON PJ.PESSOA_ID = P.ID
LEFT JOIN ENDERECO E ON E.PESSOA_ID = P.ID AND E.ISCOBRANCA = 'S'
LEFT JOIN FONE F ON F.PESSOA_ID = P.ID
WHERE P.DTINATIVO IS NULL
  AND F.NUMEROPURO LIKE ?
```

### Buscar produtos com preço:
```sql
SELECT 
    I.REFERENCIA,
    I.NOME,
    I.PESOLIQ,
    (SELECT FIRST 1 IP.PRECO / 100.0
     FROM ITEMPRECO IP
     WHERE IP.ITEM_ID = I.ID AND IP.TIPOPRECO_ID = 1
     ORDER BY IP.DATAREAJ DESC) AS PRECO_REAIS
FROM ITEM I
WHERE I.ITEMSERVICO = 'I'
  AND I.IS_BLOQUEARVENDA = 'N'
```

### Listar pontos de venda:
```sql
-- Jurídicos
SELECT * FROM VPESSOAJURIDICA ORDER BY PESSOANOME

-- Físicos
SELECT * FROM VPESSOAFISICASIMPLES ORDER BY NOME
```
