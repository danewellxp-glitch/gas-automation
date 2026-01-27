# 🔥 Guia de Integração Firebird - Gasmaster

## ✅ Status Atual

**Integração COMPLETA e FUNCIONAL!**

Conexão configurada e testada:
```sql
CONNECT '192.168.10.156:/var/firebird/Gas.fdb'
USER 'SYSDBA'
PASSWORD 'masterkey';
```

## 📊 Schema Mapeado

O schema do Firebird Gasmaster foi completamente mapeado:

| Tabela | Descrição |
|--------|-----------|
| `ITEM` | Produtos (código, nome, peso) |
| `ITEMPRECO` | Preços dos produtos (TIPOPRECO_ID=1 = padrão) |
| `ITEMSALDO` | Saldos de estoque por local/período |
| `PESSOA` | Clientes/Pessoas |
| `PESSOAFISICA` | Dados de pessoa física (CPF) |
| `PESSOAJURIDICA` | Dados de pessoa jurídica (CNPJ) |
| `ENDERECO` | Endereços (ISCOBRANCA='S' = principal) |
| `FONE` | Telefones |

## 📋 Funcionalidades Implementadas

### 1. **Busca de Produtos** ✅
- Consulta tabela `ITEM` + `ITEMPRECO`
- Retorna código, nome, preço, peso
- Filtra produtos ativos (IS_BLOQUEARVENDA = 'N')

### 2. **Busca de Clientes por Telefone** ✅
- Consulta `PESSOA` + `FONE` + `ENDERECO`
- Matching pelos últimos 8 dígitos do telefone
- Retorna dados completos (nome, CPF/CNPJ, endereço)

### 3. **Busca de Clientes por Endereço** ✅
- Consulta `PESSOA` + `ENDERECO`
- Busca por CEP + Número
- Usado quando telefone não encontra cliente

### 4. **Níveis de Estoque** ✅
- Consulta tabela `ITEMSALDO`
- Retorna saldo por local e período

### 5. **Integração com Bot WhatsApp** ✅
- Bot busca cliente automaticamente no Firebird
- Se encontrar, importa dados para PostgreSQL
- Mantém `firebird_id` para referência

---

## ⚙️ Configuração

### Variáveis de Ambiente (backend/.env e .env raiz)

```bash
# Firebird (Sistema Legado Gasmaster)
FIREBIRD_HOST=192.168.10.156
FIREBIRD_DATABASE=/var/firebird/Gas.fdb
FIREBIRD_USER=SYSDBA
FIREBIRD_PASSWORD=masterkey
FIREBIRD_CHARSET=ISO8859_1
FIREBIRD_EXPORT_ON_DELIVERED=true
```

### Dependência Python
A biblioteca `fdb==2.0.2` já está no `requirements.txt`

---

## 📁 Arquivos Principais

| Arquivo | Descrição |
|---------|-----------|
| `backend/app/integrations/firebird.py` | Cliente principal Firebird (consultas, export) |
| `backend/services/sync-service/app/sync/firebird_client.py` | Cliente do serviço de sincronização |
| `backend/app/core/handlers.py` | Integração com bot (get_or_create_customer) |

---

## ✅ Checklist de Integração

- [x] Conectar ao Firebird
- [x] Mapear schema (ITEM, PESSOA, FONE, ENDERECO, ITEMSALDO)
- [x] Configurar variáveis de ambiente
- [x] Instalar dependência fdb
- [x] Ajustar queries de produtos
- [x] Ajustar queries de clientes
- [x] Testar conexão
- [x] Testar busca de produtos
- [x] Testar busca de clientes
- [x] Implementar busca por telefone (últimos 8 dígitos)
- [x] Implementar busca por endereço (CEP + número)
- [x] Integrar bot WhatsApp com Firebird
- [ ] Configurar sincronização automática (opcional)

---

## 🧪 Testar Conexão

```bash
# Via Python no container
docker exec -it gas_backend python -c "
from app.integrations.firebird import firebird_client
print('Disponível:', firebird_client.is_available)
print('Teste:', firebird_client.test_connection())
"

# Testar busca de produtos
docker exec -it gas_backend python -c "
from app.integrations.firebird import firebird_client
produtos = firebird_client.get_products()
print(f'Produtos: {len(produtos)}')
for p in produtos[:3]:
    print(f'  - {p[\"code\"]}: {p[\"name\"]} - R\$ {p[\"price\"]}')
"
```

---

## 📞 Suporte

Se encontrar problemas:
- Verifique os logs: `docker logs gas_backend | grep -i firebird`
- Verifique se `FIREBIRD_HOST` está configurado no `.env`
- Verifique firewall/rede entre containers e servidor Firebird (porta 3050)
