# Relatório de Implementação - Integração Firebird e RPA

**Data:** 2026-01-28
**Projeto:** Gas Automation
**Versão:** 1.0.0

---

## Sumário Executivo

Este documento descreve as implementações realizadas para integração com o banco de dados Firebird (sistema legado Gasmaster) e automação RPA para entrada de dados.

### Contexto

O sistema Gasmaster utiliza banco Firebird com **acesso somente leitura**. Para contornar essa limitação, foram implementadas duas soluções:

1. **Exportação para Arquivos** - Gera CSV/XML/TXT para importação manual
2. **Robô RPA** - Automatiza entrada de dados na interface do Gasmaster

---

## 1. Arquivos Criados

### 1.1 Serviços (Backend)

| Arquivo | Descrição | Linhas |
|---------|-----------|--------|
| `app/services/file_export_service.py` | Exportação de pedidos para CSV/XML/TXT | ~450 |
| `app/services/rpa_gasmaster_service.py` | Robô RPA para automação do Gasmaster | ~500 |

### 1.2 APIs (Endpoints)

| Arquivo | Descrição | Endpoints |
|---------|-----------|-----------|
| `app/api/exports.py` | API de exportação de arquivos | 6 |
| `app/api/firebird_schema.py` | API de exploração do schema Firebird | 12 |
| `app/api/rpa.py` | API de controle do robô RPA | 9 |

### 1.3 Scripts Utilitários

| Arquivo | Descrição |
|---------|-----------|
| `scripts/calibrar_gasmaster.py` | Calibração interativa de coordenadas |
| `scripts/test_all.py` | Testes automatizados de todas as funcionalidades |

### 1.4 Migrações

| Arquivo | Descrição |
|---------|-----------|
| `alembic/versions/20260128_add_file_export_fields.py` | Adiciona campos de exportação de arquivo ao modelo Order |

---

## 2. Funcionalidades Implementadas

### 2.1 Exportação para Arquivos

#### Formatos Suportados

| Formato | Extensão | Descrição |
|---------|----------|-----------|
| CSV | `.csv` | Separado por ponto-e-vírgula, compatível com Excel |
| XML | `.xml` | Estruturado para importação em ERPs |
| Gasmaster TXT | `.txt` | Formato posicional específico do Gasmaster |

#### Estrutura do CSV

```csv
PEDIDO_NUM;DATA_PEDIDO;DATA_ENTREGA;CLIENTE_ID_FIREBIRD;CLIENTE_NOME;...
1001;2026-01-28 10:00:00;2026-01-28 12:00:00;123;Joao Silva;...
```

#### Estrutura do XML

```xml
<?xml version='1.0' encoding='utf-8'?>
<pedidos gerado_em="2026-01-28T12:00:00" total_pedidos="1">
  <pedido numero="1001">
    <data_pedido>2026-01-28T10:00:00</data_pedido>
    <cliente>
      <id_firebird>123</id_firebird>
      <nome>Joao Silva</nome>
    </cliente>
    <itens>
      <item sequencia="1">
        <codigo>P13</codigo>
        <quantidade>2</quantidade>
        <preco_unitario>75.00</preco_unitario>
      </item>
    </itens>
  </pedido>
</pedidos>
```

#### Estrutura do Gasmaster TXT

```
H00000010012026-01-280000000123Joao Silva                    41999999999    Centro     TROCA     pix  00000015000
I0000001001001P13       Gas P13                              0000020000000750000000015000
```

- Linha `H` = Header (pedido)
- Linha `I` = Item

### 2.2 Leitura do Firebird

#### Métodos do Cliente Firebird

| Método | Descrição |
|--------|-----------|
| `get_all_tables()` | Lista todas as 364 tabelas |
| `get_table_columns(table)` | Lista colunas de uma tabela |
| `get_table_primary_key(table)` | Retorna PK da tabela |
| `get_table_foreign_keys(table)` | Retorna FKs da tabela |
| `get_full_schema()` | Schema completo do banco |
| `describe_table(table)` | Descrição completa de uma tabela |
| `search_tables(pattern)` | Busca tabelas por padrão |
| `execute_raw_query(sql)` | Executa SELECT customizado |
| `get_products()` | Lista produtos |
| `get_stock_levels()` | Níveis de estoque |
| `get_routes()` | Rotas de entrega |
| `get_vehicles()` | Veículos |
| `get_customer_by_phone(phone)` | Busca cliente por telefone |
| `get_customer_by_address(cep, num)` | Busca cliente por endereço |

### 2.3 Robô RPA

#### Funcionalidades

| Funcionalidade | Descrição |
|----------------|-----------|
| Detecção de janela | Encontra janela do Gasmaster |
| Foco de janela | Traz Gasmaster para frente |
| Clique em coordenadas | Clica em posição X,Y |
| Digitação de texto | Digita texto em campos |
| Navegação por TAB | Navega entre campos |
| Screenshot | Captura tela para debug |
| Exportação completa | Fluxo automatizado de venda |

#### Fluxo de Automação

```
1. Encontrar janela Gasmaster
2. Focar na janela
3. Navegar para tela de vendas
4. Preencher código do cliente
5. Adicionar itens (produto, qtd, preço)
6. Finalizar venda
7. Marcar pedido como exportado
```

---

## 3. APIs Implementadas

### 3.1 API de Exportação (`/api/exports`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/formats` | Lista formatos disponíveis |
| GET | `/files` | Lista arquivos exportados |
| GET | `/order/{id}` | Exporta pedido individual |
| POST | `/batch` | Exporta lote de pedidos |
| POST | `/delivered` | Exporta pedidos entregues |
| GET | `/preview/{id}` | Preview da exportação |

### 3.2 API Firebird (`/api/firebird`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/status` | Status da conexão |
| GET | `/tables` | Lista todas as tabelas |
| GET | `/tables/search` | Busca tabelas por padrão |
| GET | `/tables/{name}` | Detalhes de uma tabela |
| GET | `/tables/{name}/data` | Preview de dados |
| GET | `/schema/full` | Schema completo |
| POST | `/query` | Executa SELECT |
| GET | `/data/products` | Lista produtos |
| GET | `/data/stock` | Lista estoque |
| GET | `/data/routes` | Lista rotas |
| GET | `/data/vehicles` | Lista veículos |
| GET | `/data/customer/{phone}` | Busca cliente |

### 3.3 API RPA (`/api/rpa`)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/status` | Status do RPA |
| POST | `/check-gasmaster` | Verifica se Gasmaster está aberto |
| POST | `/focus` | Foca na janela |
| POST | `/screenshot` | Tira screenshot |
| POST | `/export-order` | Exporta pedido via RPA |
| GET | `/config` | Configuração atual |
| PUT | `/config` | Atualiza configuração |
| POST | `/test-click` | Testa clique |
| POST | `/test-type` | Testa digitação |

---

## 4. Modelo de Dados

### 4.1 Campos Adicionados ao Order

```python
# Exportação para Firebird (existente)
firebird_trade_id: Optional[int]
firebird_export_status: Optional[str]  # exported, failed, pending
firebird_exported_at: Optional[datetime]
firebird_export_attempts: int
firebird_export_error: Optional[str]

# Exportação para Arquivos (novo)
file_export_status: Optional[str]  # exported, pending, failed
file_exported_at: Optional[datetime]
```

---

## 5. Configuração

### 5.1 Variáveis de Ambiente (.env)

```env
# Firebird (Sistema Legado)
FIREBIRD_HOST=192.168.10.156
FIREBIRD_DATABASE=/var/firebird/Gas.fdb
FIREBIRD_USER=SYSDBA
FIREBIRD_PASSWORD=masterkey
FIREBIRD_CHARSET=ISO8859_1
```

### 5.2 Dependências Adicionadas

```txt
# RPA
pyautogui==0.9.54
pywinauto==0.6.9
keyboard==0.13.5
pillow>=10.0.0
```

---

## 6. Banco Firebird - Informações

### 6.1 Conexão

| Parâmetro | Valor |
|-----------|-------|
| Host | 192.168.10.156 |
| Porta | 3050 |
| Database | /var/firebird/Gas.fdb |
| Usuário | SYSDBA |
| Charset | ISO8859_1 |

### 6.2 Estatísticas

| Métrica | Valor |
|---------|-------|
| Total de Tabelas | 267 |
| Total de Views | 97 |
| Total de Objetos | 364 |
| Produtos Cadastrados | 42 |
| Clientes Cadastrados | 131.899 |
| Vendas Registradas | 728.242 |

### 6.3 Tabelas Principais

| Tabela | Registros | Descrição |
|--------|-----------|-----------|
| PESSOA | 131.899 | Cadastro de pessoas |
| CLIENTE | 131.892 | Dados de clientes |
| ITEM | 61 | Produtos |
| ITEMPRECO | 72 | Preços |
| TRADE | 728.242 | Vendas |
| TRADEITEM | 915.324 | Itens de vendas |
| ENDERECO | 131.825 | Endereços |
| FONE | 132.358 | Telefones |
| ROTA | - | Rotas de entrega |
| VEICULO | - | Veículos |

---

## 7. Fluxo de Uso

### 7.1 Exportação para Arquivos

```bash
# Exportar pedidos entregues em CSV
curl -X POST "http://localhost:8000/api/exports/delivered?format=csv" \
  -H "Authorization: Bearer TOKEN" \
  --output pedidos.csv

# Exportar em XML
curl -X POST "http://localhost:8000/api/exports/delivered?format=xml" \
  -H "Authorization: Bearer TOKEN" \
  --output pedidos.xml

# Exportar formato Gasmaster
curl -X POST "http://localhost:8000/api/exports/delivered?format=gasmaster_txt" \
  -H "Authorization: Bearer TOKEN" \
  --output gasmaster.txt
```

### 7.2 Explorar Firebird

```bash
# Ver status
curl http://localhost:8000/api/firebird/status

# Listar tabelas
curl http://localhost:8000/api/firebird/tables

# Descrever tabela
curl http://localhost:8000/api/firebird/tables/ITEM

# Ver produtos
curl http://localhost:8000/api/firebird/data/products

# Buscar cliente
curl http://localhost:8000/api/firebird/data/customer/41999999999
```

### 7.3 Usar RPA

```bash
# 1. Verificar status
curl http://localhost:8000/api/rpa/status

# 2. Verificar se Gasmaster está aberto
curl -X POST http://localhost:8000/api/rpa/check-gasmaster

# 3. Calibrar (script interativo)
python scripts/calibrar_gasmaster.py

# 4. Exportar pedido
curl -X POST "http://localhost:8000/api/rpa/export-order" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "uuid",
    "order_number": 1001,
    "customer_firebird_id": 123,
    "customer_name": "Joao",
    "total_amount": 150.00,
    "items": [{"product_code": "P13", "quantity": 2, "unit_price": 75.00}]
  }'
```

---

## 8. Testes

### 8.1 Executar Testes

```bash
cd backend
python scripts/test_all.py
```

### 8.2 Resultados dos Testes

| # | Teste | Status |
|---|-------|--------|
| 1 | Serviço de Exportação de Arquivos | PASSOU |
| 2 | API de Exports | PASSOU |
| 3 | Cliente Firebird - Métodos | PASSOU |
| 4 | Conexão Real com Firebird | PASSOU |
| 5 | API Firebird Schema | PASSOU |
| 6 | Serviço RPA | PASSOU |
| 7 | API RPA | PASSOU |
| 8 | Screenshot RPA | PASSOU |
| 9 | Posição do Mouse | PASSOU |
| 10 | Modelo Order - Campos | PASSOU |

**Taxa de Sucesso: 100%**

---

## 9. Arquitetura

### 9.1 Diagrama de Fluxo

```
                                    ┌─────────────────┐
                                    │    Firebird     │
                                    │   (Gasmaster)   │
                                    │   192.168.10.156│
                                    └────────┬────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                              ▼              ▼              ▼
                         ┌────────┐    ┌──────────┐   ┌──────────┐
                         │ Leitura│    │   RPA    │   │  Arquivo │
                         │ Direta │    │  (Mouse) │   │ CSV/XML  │
                         └────┬───┘    └────┬─────┘   └────┬─────┘
                              │              │              │
                              ▼              ▼              ▼
┌─────────────┐         ┌─────────────────────────────────────────┐
│  PostgreSQL │◄────────│              FastAPI Backend            │
│   (Local)   │         │                                         │
└─────────────┘         │  /api/firebird  /api/rpa  /api/exports  │
                        └─────────────────────────────────────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │    Frontend     │
                                    │   React/Vite    │
                                    └─────────────────┘
```

### 9.2 Opções de Exportação

```
┌──────────────┐
│   Pedido     │
│   Entregue   │
└──────┬───────┘
       │
       ├─────────────────────────────────────────────────┐
       │                                                 │
       ▼                                                 ▼
┌──────────────┐                                ┌──────────────┐
│   Opção 1    │                                │   Opção 2    │
│  Arquivo     │                                │    RPA       │
│  CSV/XML/TXT │                                │  Automático  │
└──────┬───────┘                                └──────┬───────┘
       │                                               │
       ▼                                               ▼
┌──────────────┐                                ┌──────────────┐
│   Operador   │                                │   Gasmaster  │
│   Importa    │                                │   (Windows)  │
│   Manual     │                                │              │
└──────┬───────┘                                └──────┬───────┘
       │                                               │
       └───────────────────┬───────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Firebird   │
                    │   (Dados)    │
                    └──────────────┘
```

---

## 10. Próximos Passos

### 10.1 Para Usar Exportação de Arquivos

1. Rodar migração: `alembic upgrade head`
2. Testar endpoint: `POST /api/exports/delivered`
3. Baixar arquivo e importar no Gasmaster

### 10.2 Para Usar RPA

1. Conseguir acesso à tela de vendas do Gasmaster
2. Executar calibração: `python scripts/calibrar_gasmaster.py`
3. Configurar coordenadas via API ou arquivo
4. Testar com pedido de teste
5. Ativar automação em produção

### 10.3 Melhorias Futuras

- [ ] Webhook para notificar quando arquivo é gerado
- [ ] Fila de exportação RPA (Redis)
- [ ] Retry automático em caso de falha
- [ ] Dashboard de status de exportações
- [ ] Log de auditoria detalhado

---

## 11. Contato e Suporte

Para dúvidas ou problemas:
- Verificar logs: `backend/logs/`
- Executar testes: `python scripts/test_all.py`
- Consultar documentação: `docs/`

---

**Documento gerado em:** 2026-01-28
**Autor:** Claude (Assistente IA)
