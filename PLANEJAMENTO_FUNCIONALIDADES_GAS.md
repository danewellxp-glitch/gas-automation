# Planejamento: Funcionalidades Específicas para Distribuidora de Gás

## Resumo Executivo

Este documento detalha as funcionalidades críticas que estão **faltando** no sistema para atender adequadamente uma distribuidora de gás. A análise foi baseada na comparação entre as tabelas do Firebird (sistema legado) e o sistema atual.

---

## 1. VASILHAMES / COMODATO (CRÍTICO)

### Problema Atual
O sistema não possui controle de vasilhames (botijões/cascos). Na distribuidora de gás:
- Botijões são **emprestados** ao cliente (comodato)
- Cliente paga **caução** pelo vasilhame
- Na próxima compra, cliente **devolve** o vazio e leva o cheio (TROCA)
- Se cliente devolver vasilhame, recebe caução de volta

### Tabelas Firebird Relacionadas
```
VASILHAMES (cadastro de tipos de vasilhame)
├── VASILHAME_ID (PK)
├── DESCRICAO ("P13", "P45", etc.)
├── CAPACIDADE_KG
└── VALOR_CAUCAO

CLIENTE_VASILHAMES (vasilhames em posse do cliente)
├── CLIENTE_ID (FK)
├── VASILHAME_ID (FK)
├── QUANTIDADE
├── DATA_EMPRESTIMO
└── VALOR_CAUCAO_PAGO
```

### Solução Proposta

#### 1.1 Backend - Novos Models (PostgreSQL)

```python
# models/vasilhame.py
class Vasilhame(Base):
    __tablename__ = "vasilhames"

    id = Column(UUID, primary_key=True, default=uuid4)
    codigo = Column(String(10), unique=True)  # "P13", "P45"
    descricao = Column(String(100))
    capacidade_kg = Column(Numeric(10, 2))
    valor_caucao = Column(Numeric(10, 2))
    ativo = Column(Boolean, default=True)

    # Sincronização Firebird
    firebird_id = Column(Integer, nullable=True)

class ClienteVasilhame(Base):
    __tablename__ = "cliente_vasilhames"

    id = Column(UUID, primary_key=True, default=uuid4)
    cliente_id = Column(UUID, ForeignKey("customers.id"))
    vasilhame_id = Column(UUID, ForeignKey("vasilhames.id"))
    quantidade = Column(Integer, default=0)
    data_emprestimo = Column(DateTime)
    valor_caucao_pago = Column(Numeric(10, 2))

    # Relacionamentos
    cliente = relationship("Customer")
    vasilhame = relationship("Vasilhame")
```

#### 1.2 Backend - Endpoints

```
GET    /api/vasilhames                    # Listar tipos de vasilhame
POST   /api/vasilhames                    # Criar tipo (admin)
GET    /api/customers/{id}/vasilhames     # Vasilhames do cliente
POST   /api/customers/{id}/vasilhames     # Emprestar vasilhame
DELETE /api/customers/{id}/vasilhames/{v} # Devolver vasilhame
```

#### 1.3 Frontend - Componentes

- **VasilhamesBadge**: Exibir quantidade de vasilhames do cliente no perfil
- **VasilhamesModal**: Modal para gerenciar vasilhames do cliente
- **VasilhameSelector**: No pedido, selecionar se é TROCA ou VENDA

#### 1.4 Regras de Negócio

1. Se cliente **não tem** vasilhame → só pode comprar (VENDA) → paga produto + caução
2. Se cliente **tem** vasilhame → pode trocar (TROCA) → paga só produto
3. Se cliente **devolve** vasilhame → recebe caução de volta
4. Controle de estoque de vasilhames vazios vs cheios

---

## 2. TIPOS DE OPERAÇÃO (CRÍTICO)

### Problema Atual
Todos os pedidos são tratados iguais. Na distribuidora existem operações diferentes:
- **VENDA**: Cliente compra produto + vasilhame (paga caução)
- **TROCA**: Cliente troca vazio por cheio (só paga produto)
- **RETIRA**: Cliente vai buscar na loja (sem entrega)
- **RECARGA**: Apenas para P45 industrial

### Tabela Firebird
```
VENDAS.TIPO_OPERACAO = 'V' (Venda) | 'T' (Troca) | 'R' (Retira)
```

### Solução Proposta

#### 2.1 Backend - Alteração no Model Order

```python
# Adicionar ao model Order
class TipoOperacao(str, Enum):
    VENDA = "venda"      # Compra com vasilhame novo
    TROCA = "troca"      # Troca de vasilhame
    RETIRA = "retira"    # Cliente busca na loja
    RECARGA = "recarga"  # Recarga P45

class Order(Base):
    # ... campos existentes ...

    tipo_operacao = Column(
        Enum(TipoOperacao),
        default=TipoOperacao.TROCA
    )
    inclui_vasilhame = Column(Boolean, default=False)
    valor_caucao = Column(Numeric(10, 2), default=0)
```

#### 2.2 Impacto no Cálculo de Preço

```python
def calcular_total_pedido(order):
    total = 0

    for item in order.items:
        total += item.quantidade * item.preco_unitario

    # Se VENDA, adicionar caução do vasilhame
    if order.tipo_operacao == TipoOperacao.VENDA:
        total += order.valor_caucao

    # Se RETIRA, pode ter desconto (sem frete)
    if order.tipo_operacao == TipoOperacao.RETIRA:
        total -= order.desconto_retira or 0

    return total
```

#### 2.3 Frontend - Seletor de Operação

No formulário de pedido:
```jsx
<div className="mb-4">
  <label>Tipo de Operação</label>
  <select value={tipoOperacao} onChange={...}>
    <option value="troca">TROCA (cliente tem vasilhame)</option>
    <option value="venda">VENDA (cliente sem vasilhame)</option>
    <option value="retira">RETIRA (busca na loja)</option>
  </select>
</div>
```

---

## 3. EXPORTAÇÃO DE PEDIDOS PARA FIREBIRD (CRÍTICO)

### Problema Atual
Pedidos ficam apenas no PostgreSQL. O sistema legado (Firebird) precisa receber os pedidos para:
- Emitir NF-e
- Controle fiscal
- Relatórios contábeis
- Integração com outros sistemas

### Solução Proposta

#### 3.1 Serviço de Sincronização

```python
# services/firebird_sync.py

class FirebirdSyncService:

    async def exportar_pedido(self, order: Order) -> int:
        """
        Exporta pedido do PostgreSQL para Firebird.
        Retorna o VENDA_ID gerado no Firebird.
        """

        # 1. Mapear cliente
        cliente_fb = await self._get_or_create_cliente_firebird(
            order.customer
        )

        # 2. Inserir VENDAS
        venda_id = await self._inserir_venda(
            cliente_id=cliente_fb,
            data=order.created_at,
            tipo_operacao=self._map_tipo_operacao(order.tipo_operacao),
            total=order.total,
            forma_pagamento=self._map_forma_pagamento(order.payment_method)
        )

        # 3. Inserir VENDA_ITENS
        for item in order.items:
            produto_fb = await self._get_produto_firebird(item.product_id)
            await self._inserir_venda_item(
                venda_id=venda_id,
                produto_id=produto_fb,
                quantidade=item.quantity,
                preco_unitario=item.unit_price,
                tipopreco_id=self._get_tipo_preco(order)
            )

        # 4. Atualizar order com referência Firebird
        order.firebird_venda_id = venda_id
        await self.db.commit()

        return venda_id
```

#### 3.2 Mapeamento de Campos

**PostgreSQL (Order) → Firebird (VENDAS):**
- `id` → não exporta (UUID interno)
- `order_number` → NUMERO_PEDIDO
- `customer_id` → CLIENTE_ID (mapeado via firebird_id)
- `total` → VALOR_TOTAL
- `tipo_operacao` → TIPO_OPERACAO
- `payment_method` → FORMAPAGTO_ID
- `created_at` → DATA_VENDA
- `status='delivered'` → trigger que dispara a exportação

#### 3.3 Trigger de Exportação

```python
# Quando pedido muda para 'delivered'
@router.patch("/orders/{order_id}/status")
async def update_status(order_id: UUID, new_status: str):
    order = await get_order(order_id)
    order.status = new_status

    # Exportar para Firebird quando entregue
    if new_status == "delivered" and not order.firebird_venda_id:
        firebird_sync = FirebirdSyncService()
        await firebird_sync.exportar_pedido(order)

    await db.commit()
```

---

## 4. CONTROLE DE CARGA DO VEÍCULO

### Problema Atual
Não existe controle de:
- Quantos produtos o entregador levou
- Quantos vazios retornou
- Acerto de carga no final do dia

### Tabelas Firebird
```
CARGA_VEICULO
├── CARGA_ID
├── VEICULO_ID
├── MOTORISTA_ID
├── DATA_SAIDA
├── DATA_RETORNO
└── STATUS

CARGA_ITENS
├── CARGA_ID
├── PRODUTO_ID
├── QTD_SAIDA (cheios)
├── QTD_RETORNO_CHEIO
├── QTD_RETORNO_VAZIO
└── QTD_VENDIDA
```

### Solução Proposta

#### 4.1 Novos Models

```python
class CargaVeiculo(Base):
    __tablename__ = "cargas_veiculo"

    id = Column(UUID, primary_key=True)
    driver_id = Column(UUID, ForeignKey("drivers.id"))
    data_saida = Column(DateTime)
    data_retorno = Column(DateTime, nullable=True)
    status = Column(String(20))  # 'em_rota', 'finalizada'

    itens = relationship("CargaItem")
    driver = relationship("Driver")

class CargaItem(Base):
    __tablename__ = "carga_itens"

    id = Column(UUID, primary_key=True)
    carga_id = Column(UUID, ForeignKey("cargas_veiculo.id"))
    produto_id = Column(UUID, ForeignKey("products.id"))
    qtd_saida = Column(Integer)        # Saiu com X cheios
    qtd_retorno_cheio = Column(Integer, default=0)
    qtd_retorno_vazio = Column(Integer, default=0)
    qtd_vendida = Column(Integer, default=0)
```

#### 4.2 Endpoints

```
POST   /api/cargas                    # Criar carga do dia
GET    /api/cargas/{id}               # Detalhes da carga
POST   /api/cargas/{id}/saida         # Registrar saída
POST   /api/cargas/{id}/acerto        # Acerto final
GET    /api/drivers/{id}/carga-atual  # Carga atual do motorista
```

#### 4.3 Fluxo no App do Motorista

1. **Início do Dia**: Operador cria carga e aloca para motorista
2. **Saída**: Motorista confirma produtos que está levando
3. **Durante Entregas**: Sistema desconta automaticamente
4. **Fim do Dia**: Motorista faz acerto (vazios retornados, sobras)

#### 4.4 Tela de Acerto (Frontend Driver)

```jsx
// pages/driver/AcertoCarga.jsx
function AcertoCarga() {
  return (
    <div>
      <h1>Acerto de Carga</h1>

      {itens.map(item => (
        <div key={item.id} className="border p-4 mb-2">
          <p><strong>{item.produto_nome}</strong></p>
          <p>Saiu com: {item.qtd_saida} cheios</p>
          <p>Vendeu: {item.qtd_vendida}</p>

          <label>Retornou cheios:</label>
          <input type="number" value={item.qtd_retorno_cheio} />

          <label>Retornou vazios:</label>
          <input type="number" value={item.qtd_retorno_vazio} />
        </div>
      ))}

      <button onClick={finalizarAcerto}>
        Finalizar Acerto
      </button>
    </div>
  )
}
```

---

## 5. PREÇOS POR MODALIDADE

### Problema Atual
O sistema usa `TIPOPRECO_ID = 1` hardcoded. No Firebird existem múltiplos tipos:

```
TIPOSPRECO
├── 1 = "Varejo"
├── 2 = "Atacado"
├── 3 = "Funcionário"
├── 4 = "Revenda"
└── 5 = "Promocional"
```

### Solução Proposta

#### 5.1 Novo Model

```python
class TipoPreco(Base):
    __tablename__ = "tipos_preco"

    id = Column(UUID, primary_key=True)
    codigo = Column(String(20), unique=True)
    descricao = Column(String(100))
    percentual_desconto = Column(Numeric(5, 2), default=0)
    ativo = Column(Boolean, default=True)
    firebird_id = Column(Integer)  # Mapeamento

class ProdutoPreco(Base):
    __tablename__ = "produto_precos"

    id = Column(UUID, primary_key=True)
    produto_id = Column(UUID, ForeignKey("products.id"))
    tipo_preco_id = Column(UUID, ForeignKey("tipos_preco.id"))
    preco = Column(Numeric(10, 2))
    vigencia_inicio = Column(Date)
    vigencia_fim = Column(Date, nullable=True)
```

#### 5.2 Lógica de Preço no Pedido

```python
def get_preco_produto(produto_id: UUID, cliente: Customer) -> Decimal:
    """
    Retorna preço do produto baseado no tipo de cliente.
    """

    # Determinar tipo de preço do cliente
    if cliente.is_revenda:
        tipo_preco = "revenda"
    elif cliente.is_funcionario:
        tipo_preco = "funcionario"
    else:
        tipo_preco = "varejo"

    # Buscar preço específico
    preco = db.query(ProdutoPreco).filter(
        ProdutoPreco.produto_id == produto_id,
        ProdutoPreco.tipo_preco.codigo == tipo_preco,
        ProdutoPreco.vigencia_inicio <= date.today(),
        or_(
            ProdutoPreco.vigencia_fim.is_(None),
            ProdutoPreco.vigencia_fim >= date.today()
        )
    ).first()

    return preco.preco if preco else produto.preco_padrao
```

---

## 6. CRONOGRAMA DE IMPLEMENTAÇÃO

### Fase 1 - Fundação (1-2 semanas)
- [ ] Criar migrations para novos models
- [ ] Implementar CRUD de Vasilhames
- [ ] Adicionar tipo_operacao ao Order

### Fase 2 - Vasilhames (1 semana)
- [ ] Endpoint cliente_vasilhames
- [ ] Componentes frontend vasilhames
- [ ] Integração no fluxo de pedido

### Fase 3 - Exportação Firebird (2 semanas)
- [ ] Serviço de sincronização
- [ ] Mapeamento de campos
- [ ] Trigger de exportação automática
- [ ] Logs de sincronização

### Fase 4 - Carga Veículo (1 semana)
- [ ] Models e endpoints carga
- [ ] Tela de acerto no app driver
- [ ] Relatório de acerto

### Fase 5 - Preços (1 semana)
- [ ] Model tipos_preco e produto_precos
- [ ] Sincronização com Firebird
- [ ] Lógica de seleção de preço

---

## 7. CONSIDERAÇÕES TÉCNICAS

### 7.1 Ordem de Implementação Recomendada

1. **Tipos de Operação** - Menor impacto, prepara base
2. **Vasilhames** - Crítico para o negócio
3. **Preços** - Melhora precisão financeira
4. **Carga Veículo** - Controle operacional
5. **Exportação Firebird** - Integração final

### 7.2 Riscos

**Quebra de pedidos existentes**
- Impacto: Alto
- Mitigação: Criar migrations com valores default para campos novos

**Erro na sincronização Firebird**
- Impacto: Alto
- Mitigação: Implementar logs detalhados, retry automático e alertas para falhas

**Performance com muitas cargas**
- Impacto: Médio
- Mitigação: Criar índices apropriados e implementar paginação nas listagens

### 7.3 Testes Necessários

- [ ] Teste unitário: cálculo de preço por tipo
- [ ] Teste integração: criar pedido com vasilhame
- [ ] Teste E2E: fluxo completo TROCA
- [ ] Teste E2E: exportação para Firebird
- [ ] Teste de carga: múltiplas sincronizações

---

## 8. PRÓXIMOS PASSOS

1. **Revisar** este documento com stakeholders
2. **Priorizar** funcionalidades por urgência do negócio
3. **Criar** branch `feature/gas-funcionalidades`
4. **Implementar** em sprints de 1 semana cada
5. **Testar** cada fase antes de prosseguir

---

*Documento criado em: 22/01/2026*
*Autor: Claude Code*
*Versão: 1.0*
