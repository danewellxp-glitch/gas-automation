# ✅ Integração Firebird - Atualização Completa

## 🎯 O que foi atualizado

### 1. ✅ Schema Real Mapeado

**Tabelas principais descobertas:**
- ✅ `ITEM` - Produtos (não "PRODUTOS")
- ✅ `ITEMPRECO` - Preços (em centavos)
- ✅ `PESSOA` - Clientes (tabela principal)
- ✅ `PESSOAFISICA` - CPF de pessoas físicas
- ✅ `PESSOAJURIDICA` - CNPJ de pessoas jurídicas
- ✅ `CLIENTE` - Relação de clientes
- ✅ `ENDERECO` - Endereços (ISCOBRANCA='S' = principal)
- ✅ `FONE` - Telefones (NUMEROPURO = telefone limpo)

**Views importantes:**
- ✅ `VPESSOAJURIDICA` - Pontos de venda (jurídica)
- ✅ `VPESSOAFISICASIMPLES` - Pontos de venda (física)
- ✅ `VCLIENTE` - View de clientes

---

### 2. ✅ Métodos Atualizados

#### `get_products()` ✅
- Query atualizada para usar tabela `ITEM`
- Busca preço mais recente de `ITEMPRECO`
- Converte preço de centavos para reais
- Filtra produtos ativos corretamente

#### `get_product_by_code()` ✅
- Busca por `REFERENCIA` (código do produto)
- Retorna dados completos com preço

#### `get_customer_by_phone()` ✅
- Query completa com `PESSOA` + `PESSOAFISICA` + `PESSOAJURIDICA` + `ENDERECO` + `FONE`
- Busca por `NUMEROPURO` (telefone limpo)
- Retorna CPF/CNPJ, endereço completo, limite de crédito

#### `get_customer_by_id()` ✅
- Busca por `PESSOA_ID`
- Retorna dados completos do cliente

#### `get_sales_points()` ✅ **NOVO**
- Busca pontos de venda de `VPESSOAJURIDICA` e `VPESSOAFISICASIMPLES`
- Retorna lista completa de pontos de venda

#### `get_sales_point_by_id()` ✅ **NOVO**
- Busca ponto de venda específico por ID

---

### 3. ✅ Correções Aplicadas

1. **Preços em centavos**: Todos os métodos agora convertem corretamente
2. **Endereços**: Busca endereço principal (`ISCOBRANCA='S'`)
3. **Telefones**: Usa `NUMEROPURO` para busca precisa
4. **CPF/CNPJ**: Busca de tabelas corretas (`PESSOAFISICA` / `PESSOAJURIDICA`)
5. **Limite de crédito**: Converte de centavos para reais

---

## 📋 Estrutura de Dados Retornados

### Produto
```python
{
    "firebird_id": 1,
    "code": "P-13",
    "name": "GLP ENVAZADO EM BOTIJÃO P13 KG",
    "name_short": "GLP 13 Kg",
    "price": 110.00,  # Já convertido de centavos
    "weight_kg": 13.0,
    "weight_bruto_kg": 27.9,
    "is_active": True,
    "classification": "GAS",
    "price_date": "2026-01-14"
}
```

### Cliente
```python
{
    "firebird_id": 101,
    "firebird_cliente_id": 50,
    "name": "AMIZADE PRODUTOS PARA MOVÉIS LTDA-EPP",
    "name_short": "AMIZADE",
    "phone": "4133460102",
    "phone_clean": "4133460102",
    "email": "amizade@compensadosamizade.com.br",
    "fisjur": "J",  # 'F' ou 'J'
    "cpf": None,
    "cnpj": "80557523000172",
    "cpf_cnpj": "80557523000172",
    "credit_limit": 1000.00,  # Já convertido de centavos
    "address": {
        "street": "Hermenegildo Bonat",
        "number": "664",
        "complement": None,
        "bairro": "XAXIM",
        "city": "Curitiba",
        "state": "PR",
        "cep": "81810280"
    }
}
```

### Ponto de Venda
```python
{
    "firebird_id": 11,
    "name": "J.S.MENDONÇA E CIA LTDA",
    "name_short": "MENDONCA GAS",
    "cnpj": "06114833000160",
    "insc_estadual": "9030151280",
    "activity": "Pontos de Venda",
    "type": "juridica",  # ou "fisica"
    "created_at": "2013-12-12"
}
```

---

## 🚀 Próximos Passos

1. **Configurar `.env`** com credenciais do Firebird
2. **Reconstruir container** para instalar `fdb`
3. **Testar conexão** e busca de dados
4. **Criar script de sincronização inicial** para importar produtos

---

## 📝 Comandos de Teste

```bash
# Testar conexão
docker exec gas_backend python -c "
from app.integrations.firebird import firebird_client
print('Disponível:', firebird_client.is_available)
print('Conexão:', firebird_client.test_connection())
"

# Testar produtos
docker exec gas_backend python -c "
from app.integrations.firebird import firebird_client
products = firebird_client.get_products()
print(f'Produtos: {len(products)}')
for p in products[:3]:
    print(f'  {p[\"code\"]}: {p[\"name\"]} - R\$ {p[\"price\"]:.2f}')
"

# Testar cliente por telefone
docker exec gas_backend python -c "
from app.integrations.firebird import firebird_client
customer = firebird_client.get_customer_by_phone('4133460102')
if customer:
    print(f'Cliente: {customer[\"name\"]}')
    print(f'  CNPJ: {customer.get(\"cnpj\")}')
    print(f'  Endereço: {customer[\"address\"].get(\"street\")}')
"

# Testar pontos de venda
docker exec gas_backend python -c "
from app.integrations.firebird import firebird_client
points = firebird_client.get_sales_points()
print(f'Pontos de venda: {len(points)}')
for p in points[:5]:
    print(f'  {p[\"name\"]} ({p[\"type\"]})')
"
```

---

## ✅ Status

- [x] Schema mapeado completamente
- [x] Queries atualizadas com tabelas reais
- [x] Métodos de produtos corrigidos
- [x] Métodos de clientes corrigidos
- [x] Métodos de pontos de venda adicionados
- [x] Conversão de centavos implementada
- [x] Busca de endereços implementada
- [x] Documentação completa criada

**Aguardando:** Suas descobertas adicionais do banco para ajustes finais! 🚀
