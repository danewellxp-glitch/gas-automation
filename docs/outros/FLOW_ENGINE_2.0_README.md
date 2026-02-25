# 🔧 GasMaster Flow Engine 2.0

## Visão Geral

O **Flow Engine 2.0** é uma refatoração completa do sistema de atendimento automatizado via WhatsApp, transformando a experiência de um fluxo rígido baseado em menus para uma conversa natural e inteligente.

**Versão:** 2.0.0  
**Data:** 13 de Fevereiro de 2026  
**Status:** 🚧 EM IMPLEMENTAÇÃO

---

## 📊 Melhorias Esperadas

| Métrica | Atual (v1.0) | Meta (v2.0) | Melhoria |
|---------|--------------|-------------|----------|
| Taxa de conclusão | ~40% | > 85% | +112% |
| Tempo médio (novo) | 3-5 min | < 90 seg | -70% |
| Tempo médio (conhecido) | 2-3 min | < 30 seg | -83% |
| Taxa de abandono | ~60% | < 15% | -75% |
| Tempo de resposta | 3-5 seg | < 1 seg | -80% |

---

## 🏗️ Arquitetura

### Componentes Principais

```
┌─────────────────────────────────────────────────────────────┐
│                    FLOW ENGINE 2.0                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Message Normalizer → Processa entrada                  │
│  2. NLU Engine (Híbrido) → Detecta intenção                │
│  3. Context Manager → Gerencia 3 camadas                   │
│  4. State Machine 2.0 → 25 estados em fases                │
│  5. Response Generator → Gera respostas personalizadas     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Arquivos Criados

```
backend/app/core/
├── state_machine_v2.py          # 25 estados organizados em fases
├── nlu_engine_v2.py              # NLU híbrido (Keyword→Pattern→LLM)
├── product_catalog.py            # Catálogo de produtos e configurações
├── message_templates.py          # Templates de mensagens personalizadas
└── flow_config.py                # Configurações centralizadas
```

---

## 🔄 Estados (25 estados em 5 fases)

### FASE 1: GREETING (Boas-vindas) - 2 estados
- `GREETING_INITIAL` - Estado inicial
- `GREETING_RETURNING` - Cliente conhecido retornando

### FASE 2: IDENTIFY (Identificação) - 5 estados
- `IDENTIFY_TYPE` - PF ou PJ
- `IDENTIFY_NAME_PF` - Nome completo (PF)
- `IDENTIFY_NAME_PJ` - Razão social (PJ)
- `IDENTIFY_DOCUMENT_CPF` - CPF
- `IDENTIFY_DOCUMENT_CNPJ` - CNPJ

### FASE 3: ORDERING (Pedido) - 8 estados
- `ORDERING_PRODUCT` - Seleção de produto
- `ORDERING_QUANTITY` - Quantidade
- `ORDERING_OPERATION` - Tipo (Troca/Venda/Retira)
- `ORDERING_MORE_ITEMS` - Adicionar mais?
- `ORDERING_ADDRESS` - Endereço de entrega
- `ORDERING_ADDRESS_CONFIRM` - Confirmar endereço
- `ORDERING_COMPLEMENT` - Complemento
- `ORDERING_CONFIRM_REPEAT` - Repetir último pedido

### FASE 4: CHECKOUT (Finalização) - 3 estados
- `CHECKOUT_PAYMENT` - Método de pagamento
- `CHECKOUT_CHANGE` - Troco (se dinheiro)
- `CHECKOUT_SUMMARY` - Resumo e confirmação

### FASE 5: COMPLETE (Conclusão) - 2 estados
- `COMPLETE_CONFIRMED` - Pedido confirmado
- `COMPLETE_FOLLOWUP` - Pós-venda

### ESTADOS DE SUPORTE (Paralelos) - 5 estados
- `SUPPORT_HUMAN` - Atendimento humano
- `SUPPORT_FAQ` - FAQ inline
- `TRACKING_STATUS` - Status do pedido
- `TRACKING_OPTIONS` - Opções após ver status
- `ERROR_RECOVERY` - Recuperação de erro

---

## 🧠 NLU Engine (Híbrido)

### Pipeline em 3 Camadas

```
Mensagem → [1. Keyword] → [2. Pattern] → [3. LLM] → Intenção
              < 10ms         < 20ms        100-300ms
              95%+ conf      85%+ conf     70%+ conf
```

### Intenções Detectáveis

- `GREETING` - Saudação
- `BUY` - Comprar gás
- `REPEAT_ORDER` - Repetir pedido
- `TRACK` - Rastrear pedido
- `CONFIRM` - Confirmar
- `DENY` - Negar
- `CANCEL` - Cancelar
- `HUMAN` - Falar com atendente
- `HELP` - Ajuda
- `MENU` - Voltar ao menu
- `INFO` - Informação
- `EDIT` - Alterar
- `EMERGENCY` - Emergência
- `UNKNOWN` - Não identificado

---

## 📦 Catálogo de Produtos

### Produtos Disponíveis

| Código | Nome | Peso | Troca | Venda | Caução |
|--------|------|------|-------|-------|--------|
| P13 | Botijão P13 | 13kg | R$ 110 | R$ 210 | R$ 100 |
| P20 | Botijão P20 | 20kg | R$ 150 | R$ 280 | R$ 130 |
| P45 | Botijão P45 | 45kg | R$ 280 | R$ 480 | R$ 200 |

### Tipos de Operação

- **🔄 TROCA** - Cliente entrega vasilhame vazio (preço mais barato)
- **🆕 VENDA** - Cliente compra gás + vasilhame (primeira compra)
- **🏪 RETIRA** - Cliente busca na loja (sem taxa de entrega)

### Métodos de Pagamento

- 💵 **Dinheiro** - Na entrega (limite R$ 500)
- 💳 **Cartão de Crédito/Débito** - Máquina do entregador
- 📱 **PIX** - Pagamento instantâneo
- 📄 **Faturado** - Apenas PJ com cadastro (mín. R$ 200)

---

## 📍 Área de Cobertura

### Bairros Atendidos (Curitiba/PR)

| Bairro | Taxa | Tempo | Pedido Mín |
|--------|------|-------|------------|
| Alto Boqueirão | R$ 0 | 30-60 min | - |
| Boqueirão | R$ 0 | 25-45 min | - |
| Ganchinho | R$ 5 | 40-70 min | R$ 100 |
| Hauer | R$ 0 | 20-40 min | - |
| Sítio Cercado | R$ 5 | 35-60 min | R$ 80 |
| Umbará | R$ 8 | 45-90 min | R$ 100 |
| Xaxim | R$ 0 | 20-40 min | - |

---

## ⏰ Horário de Funcionamento

| Dia | Atendimento | Entregas | Status |
|-----|-------------|----------|--------|
| Segunda-Sexta | 08:00 - 18:00 | 08:30 - 17:30 | 🟢 Aberto |
| Sábado | 08:00 - 12:00 | 08:30 - 11:30 | 🟡 Meio período |
| Domingo | FECHADO | FECHADO | 🔴 Fechado |

---

## 🚀 Atalhos Especiais

### 1. Fast-Track (10-15 seg)

Cliente fornece tudo na primeira mensagem:

```
Cliente: "quero 2 P13 troca, Rua das Flores 123, cartão"

Bot: "👋 Olá, João!
      
      📋 Entendi seu pedido:
      🛒 2x P13 (troca) = R$220
      📍 Rua das Flores, 123
      💳 Cartão
      
      Confirma?"
```

### 2. Repetir Pedido (15-30 seg)

Cliente conhecido pode repetir último pedido:

```
Cliente: "quero gas"

Bot: "👋 Olá, João!
      Último pedido: 2x P13, R$220
      Deseja repetir?"
```

### 3. FAQ Inline

Responde perguntas sem sair do fluxo:

```
(Durante pedido)
Cliente: "vocês entregam no pinheirinho?"

Bot: "📍 Infelizmente o Pinheirinho não está na nossa área 😔
      
      Entregamos em: Boqueirão, Hauer, Xaxim...
      
      ─────────────────────
      
      Voltando ao seu pedido...
      🛒 Qual produto?"
```

---

## 🔧 Configuração

### Feature Flags

```python
FEATURE_FLAGS = {
    "flow_engine_v2_enabled": False,  # Master switch
    "fast_track_enabled": True,
    "repeat_order_enabled": True,
    "abandoned_order_recovery": True,
    "faq_inline_enabled": True,
    "llm_classification_enabled": True,
}
```

### Rollout Gradual

```python
# Percentual de tráfego no v2.0 (0-100)
ROLLOUT_PERCENTAGE = 0  # Começar com 0%

# Aumentar gradualmente:
# Dia 1: 10%
# Dia 2: 25%
# Dia 3: 50%
# Dia 4: 100%
```

---

## 📈 Métricas

### KPIs Monitorados

- Taxa de conclusão de pedidos
- Tempo médio de atendimento
- Taxa de abandono
- NPS do atendimento
- Tempo de resposta do bot
- Uso de "repetir pedido"

### Prometheus Metrics

```python
# Contadores
flow_state_transitions_total
orders_created_total
abandoned_orders_total

# Histogramas
order_completion_seconds
nlu_processing_seconds

# Gauges
active_conversations
```

---

## 🧪 Testes

### Testes Unitários

```bash
pytest backend/tests/core/test_state_machine_v2.py
pytest backend/tests/core/test_nlu_engine_v2.py
pytest backend/tests/core/test_product_catalog.py
```

### Testes E2E

```bash
pytest backend/tests/e2e/test_flow_engine_v2.py
```

---

## 📝 Migração v1.0 → v2.0

### Compatibilidade

O sistema mantém compatibilidade com v1.0 através de:

1. **Mapeamento de Estados**: Estados v1.0 são automaticamente convertidos para v2.0
2. **Feature Flags**: v2.0 pode ser habilitado gradualmente
3. **Rollback Automático**: Sistema volta para v1.0 se detectar problemas

### Critérios de Rollback

- Taxa de erro > 5%
- Tempo de resposta p95 > 3s
- Taxa de conclusão < 30%

---

## 🐛 Troubleshooting

### Bot não responde

1. Verificar se WAHA está rodando
2. Verificar logs: `docker logs gasmaster-backend`
3. Verificar Redis: `docker exec -it gasmaster-redis redis-cli`

### Pedidos não sendo criados

1. Verificar PostgreSQL
2. Verificar logs de handlers
3. Verificar contexto no Redis

### NLU não detectando intenção

1. Verificar logs do NLU Engine
2. Testar keywords manualmente
3. Verificar se Ollama está disponível

---

## 📚 Documentação Completa

- [Documento Técnico Completo](./GASMASTER_FLOW_ENGINE_2.0_COMPLETO%20(1).md)
- [Arquitetura Detalhada](./docs/arquitetura/)
- [Guia de Desenvolvimento](./docs/guias/)

---

## 👥 Equipe

**Autor:** Fabiano Lopes  
**Data:** 13 de Fevereiro de 2026  
**Versão:** 2.0.0

---

## 📄 Licença

Propriedade de GasMaster © 2026
