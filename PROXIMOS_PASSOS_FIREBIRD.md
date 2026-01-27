# 🚀 Próximos Passos - Integração Firebird Gasmaster

## ✅ O que já foi feito

1. ✅ Conexão testada com sucesso via `isql`
2. ✅ Código de integração já existe no sistema
3. ✅ Script de mapeamento criado
4. ✅ Guia completo criado

## 🎯 Ações Imediatas (Próximas 2 horas)

### 1. **Mapear o Schema** (15 min) ⭐ PRIORITÁRIO

Execute o script para descobrir as tabelas reais:

```bash
cd /home/daniel/gas-automation/backend
python scripts/map_firebird_schema.py
```

**O que você vai descobrir:**
- Nome real da tabela de produtos
- Nome real da tabela de clientes  
- Estrutura das colunas
- Dados de exemplo

**Salve o resultado:**
```bash
python scripts/map_firebird_schema.py > ../firebird_schema_map.txt
```

---

### 2. **Configurar Variáveis de Ambiente** (5 min)

Adicione ao arquivo `.env` na raiz do projeto:

```bash
# Firebird Gasmaster
FIREBIRD_HOST=192.168.10.156
FIREBIRD_DATABASE=/var/firebird/Gas.fdb
FIREBIRD_USER=SYSDBA
FIREBIRD_PASSWORD=masterkey
FIREBIRD_CHARSET=UTF8
```

---

### 3. **Instalar Dependência fdb** (10 min)

A biblioteca já foi adicionada ao `requirements.txt`. Reconstrua o container:

```bash
docker-compose build backend
docker-compose restart backend
```

Verifique se instalou:
```bash
docker exec gas_backend pip list | grep fdb
```

---

### 4. **Ajustar Queries no Código** (30 min)

Após mapear o schema, ajuste as queries em:

**Arquivo:** `backend/app/integrations/firebird.py`

**O que ajustar:**
- Linha ~150: Query de produtos (`get_products`)
- Linha ~220: Query de clientes (`get_customer_by_phone`)

**Exemplo do que precisa descobrir:**
```python
# ANTES (genérico):
FROM PRODUTOS
WHERE TIPO = 'GAS'

# DEPOIS (ajustado para schema real):
FROM PRODUTO_GAS  # ou o nome real que você descobrir
WHERE ATIVO = 'S'  # ou o campo real
```

---

### 5. **Testar Conexão** (5 min)

```bash
# Teste via Python
docker exec -it gas_backend python -c "
from app.integrations.firebird import firebird_client
print('✅ Disponível:', firebird_client.is_available)
print('✅ Teste conexão:', firebird_client.test_connection())
"
```

---

### 6. **Testar Busca de Produtos** (10 min)

```bash
docker exec -it gas_backend python -c "
from app.integrations.firebird import firebird_client
products = firebird_client.get_products()
print(f'📦 Produtos encontrados: {len(products)}')
for p in products[:3]:
    print(f'  - {p}')
"
```

---

## 📋 Checklist Rápido

- [ ] Executar script de mapeamento
- [ ] Analisar resultado e identificar tabelas
- [ ] Adicionar variáveis ao `.env`
- [ ] Reconstruir container backend
- [ ] Ajustar queries de produtos
- [ ] Ajustar queries de clientes
- [ ] Testar conexão
- [ ] Testar busca de produtos
- [ ] Testar busca de clientes

---

## 🔍 O que o Script de Mapeamento Vai Mostrar

1. **Tabelas importantes encontradas:**
   - PRODUTOS / PRODUTO / PROD
   - CLIENTES / CLIENTE / CLI
   - PEDIDOS / PEDIDO / PED
   - ESTOQUE / STOCK

2. **Estrutura de cada tabela:**
   - Nome das colunas
   - Tipos de dados
   - Se aceita NULL
   - Valores padrão

3. **Dados de exemplo:**
   - 2 registros de cada tabela para entender o formato

---

## ⚠️ Pontos de Atenção

1. **Nomes de tabelas/colunas podem estar em maiúsculas/minúsculas**
   - Firebird é case-sensitive em alguns casos
   - Use aspas duplas se necessário: `"PRODUTOS"`

2. **Encoding/Charset**
   - Já configurado como UTF8
   - Se houver problemas com acentos, verificar charset do banco

3. **Conexão de rede**
   - Container precisa acessar `192.168.10.156:3050`
   - Verificar se há firewall bloqueando

4. **Formato de dados**
   - Datas podem estar em formato diferente
   - Decimais podem precisar de conversão

---

## 📞 Próxima Sessão

Após executar o script de mapeamento, compartilhe:
1. Nome real da tabela de produtos
2. Nome real da tabela de clientes
3. Estrutura das colunas principais

Com isso, ajusto as queries no código automaticamente! 🚀
