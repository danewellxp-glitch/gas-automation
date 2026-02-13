# Fluxo Ideal do Bot de WhatsApp - Gas Automation

**📅 Última Atualização:** 13 de Fevereiro de 2026  
**📊 Status Geral:** ✅ Core Funcionando | ⚠️ Melhorias de UX Pendentes

---

## 🚀 RESUMO EXECUTIVO

### O Que Está Funcionando ✅
- **Pipeline completo:** Webhook → Redis Stream → Consumer → Flow Engine → WAHA → WebSocket
- **Deduplicação:** Mensagens duplicadas são ignoradas corretamente
- **State Machine:** Fluxo conversacional completo implementado
- **Contexto persistido:** Redis (rápido) + PostgreSQL (backup)
- **Tracing:** Rastreamento completo com trace_id único
- **Atendente humano:** Integração funcionando com nome do atendente nas mensagens

### O Que Falta Implementar ❌
- **Feedback imediato:** "digitando..." e marcar como lida (prioridade ALTA)
- **Reconhecimento Firebird:** Integração completa para buscar clientes existentes
- **Repetir pedido:** Funcionalidade para clientes conhecidos
- **UX pedido abandonado:** Perguntar se quer continuar de onde parou

### Próximos Passos 📋
1. **Prioridade ALTA:** Implementar feedback imediato (typing + marcar como lida)
2. **Prioridade MÉDIA:** Integração Firebird + repetir pedido
3. **Prioridade BAIXA:** Melhorias de UX (perguntas fora contexto, agregação)

---

## 📋 STATUS DE IMPLEMENTAÇÃO

### ✅ Implementado e Funcionando
- ✅ **Deduplicação de mensagens** - Redis SET com TTL 1h
- ✅ **Processamento assíncrono** - Redis Stream + Consumer Groups
- ✅ **State Machine (FSM)** - Flow Engine completo
- ✅ **Contexto persistido** - Redis (30min) + PostgreSQL snapshot (24h)
- ✅ **Tracing completo** - Trace ID único em todo o pipeline
- ✅ **Integração atendente** - Nome do atendente nas mensagens

### ⚠️ Parcialmente Implementado
- ⚠️ **Reconhecimento cliente** - Busca PostgreSQL OK, falta integração Firebird
- ⚠️ **Continuar pedido abandonado** - Funciona, falta UX (perguntar se quer continuar)

### ❌ Ainda Não Implementado
- ❌ **Feedback imediato** - "digitando..." e marcar como lida
- ❌ **Repetir último pedido** - Para clientes conhecidos
- ❌ **Perguntas fora contexto** - NLU para responder e voltar ao fluxo
- ❌ **Agregação mensagens** - Combinar mensagens rápidas

---

## 1. Visão Geral do Problema

### Problemas Identificados e Status
| # | Problema | Impacto no Cliente | Status |
|---|----------|-------------------|--------|
| 1 | Mensagens duplicadas processadas | Cliente recebe respostas duplicadas, pedidos duplicados | ✅ **RESOLVIDO** |
| 2 | Estado perdido entre mensagens | Cliente precisa recomeçar do zero | ✅ **RESOLVIDO** (Redis + PostgreSQL) |
| 3 | Cliente não reconhecido | Pede dados que já temos | ⚠️ **PARCIAL** (falta Firebird) |
| 4 | Ordem das mensagens incorreta | Confusão, experiência ruim | ✅ **RESOLVIDO** (Lock distribuído) |
| 5 | Sem feedback de "digitando..." | Cliente acha que bot travou | ❌ **PENDENTE** |

---

## 2. Fluxo Ideal - Diagrama Principal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENTE ENVIA MENSAGEM                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 1: RECEPÇÃO (< 100ms)                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐        │
│  │   Webhook   │───▶│  Deduplicação    │───▶│  Responder HTTP 200 │        │
│  │   Recebe    │    │  (message_id)    │    │  imediatamente      │        │
│  └─────────────┘    └──────────────────┘    └─────────────────────┘        │
│                            │                                                │
│                            ▼                                                │
│                     ┌──────────────────┐                                    │
│                     │  Já processada?  │──── SIM ──▶ IGNORAR (return)      │
│                     └──────────────────┘                                    │
│                            │ NÃO                                            │
│                            ▼                                                │
│                     ┌──────────────────┐                                    │
│                     │ Adicionar à fila │                                    │
│                     │  (background)    │                                    │
│                     │ ✅ Redis Stream  │                                    │
│                     └──────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 2: FEEDBACK IMEDIATO (< 500ms)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐     │
│  │ Mostrar "typing"│    │ Notificar painel│    │  Marcar como lida   │     │
│  │ para o cliente  │    │ (WebSocket)     │    │  (✓✓ azul)          │     │
│  │ ❌ PENDENTE     │    │ ✅ IMPLEMENTADO │    │  ❌ PENDENTE         │     │
│  └─────────────────┘    └─────────────────┘    └─────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 3: IDENTIFICAÇÃO DO CLIENTE (< 200ms)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Buscar contexto │                                                        │
│  │ Redis + Fallback│                                                        │
│  │ ✅ IMPLEMENTADO │                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    CLIENTE CONHECIDO?                            │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│           │                              │                                  │
│           ▼ SIM                          ▼ NÃO                             │
│  ┌─────────────────┐            ┌─────────────────┐                        │
│  │ Carregar dados: │            │ Buscar Firebird │                        │
│  │ - Nome          │            │ pelo telefone   │                        │
│  │ - Endereço      │            │ ⚠️ PARCIAL      │                        │
│  │ - Último pedido │            └────────┬────────┘                        │
│  │ - Preferências  │                     │                                  │
│  │ ✅ PostgreSQL   │                     ▼                                  │
│  └─────────────────┘            ┌─────────────────┐                        │
│                                 │ Encontrou?      │                        │
│                                 └────────┬────────┘                        │
│                                    SIM   │   NÃO                           │
│                                    ▼     │    ▼                            │
│                         ┌──────────────┐ │ ┌──────────────┐                │
│                         │Migrar dados  │ │ │Criar cliente │                │
│                         │do Firebird   │ │ │novo          │                │
│                         │ ❌ PENDENTE  │ │ │✅ IMPLEMENTADO│                │
│                         └──────────────┘ │ └──────────────┘                │
│                                          │                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 4: PROCESSAMENTO DA MENSAGEM                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    TIPO DE MENSAGEM                              │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│        │              │              │              │                       │
│        ▼              ▼              ▼              ▼                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐               │
│  │ Comando  │  │  Botão   │  │  Texto   │  │  Localização │               │
│  │ Global   │  │ Clicado  │  │  Livre   │  │  Compartilhada│               │
│  │(menu,etc)│  │          │  │          │  │               │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘               │
│       │             │             │               │                        │
│       ▼             ▼             ▼               ▼                        │
│  ┌──────────────────────────────────────────────────────────────┐         │
│  │                   STATE MACHINE                               │         │
│  │  ┌───────┐   ┌─────────┐   ┌──────────┐   ┌─────────────┐   │         │
│  │  │ START │──▶│PRODUTO  │──▶│QUANTIDADE│──▶│  ENDEREÇO   │   │         │
│  │  └───────┘   └─────────┘   └──────────┘   └──────┬──────┘   │         │
│  │  ✅ IMPLEMENTADO                                  │          │         │
│  │                                                   ▼          │         │
│  │  ┌──────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐   │         │
│  │  │CONFIRMADO│◀──│PAGAMENTO│◀──│CONFIRMAR │◀──│ENDEREÇO │   │         │
│  │  └──────────┘   └─────────┘   │  PEDIDO  │   │CONFIRMADO│   │         │
│  │                               └──────────┘   └─────────┘   │         │
│  └──────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 5: RESPOSTA AO CLIENTE                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐     │
│  │ Parar "typing"  │───▶│ Enviar resposta │───▶│ Salvar no EventLog  │     │
│  │ ❌ PENDENTE     │    │ ✅ IMPLEMENTADO │    │ ✅ IMPLEMENTADO      │     │
│  └─────────────────┘    └─────────────────┘    └─────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Fluxo de Conversa Ideal (UX)

### 3.1 Cliente Novo - Primeira Compra

```
┌─────────────────────────────────────────────────────────────────┐
│ CLIENTE (novo)                        │ BOT                     │
├───────────────────────────────────────┼─────────────────────────┤
│                                       │                         │
│ "Oi"                                  │                         │
│                                       │ ✓✓ (marca como lida)    │
│                                       │ ... (digitando)         │
│                                       │                         │
│                                       │ "👋 Olá! Bem-vindo à    │
│                                       │ Distribuidora de Gás!   │
│                                       │                         │
│                                       │ Qual produto você       │
│                                       │ deseja?"                │
│                                       │                         │
│                                       │ [P13 - R$110]           │
│                                       │ [P20 - R$150]           │
│                                       │ [P45 - R$280]           │
│                                       │                         │
│ *clica no botão P13*                  │                         │
│                                       │ ✓✓ ... (digitando)      │
│                                       │                         │
│                                       │ "✅ P13 selecionado!    │
│                                       │ Quantos botijões?"      │
│                                       │                         │
│                                       │ [1] [2] [3]             │
│                                       │                         │
│ *clica em 2*                          │                         │
│                                       │ ✓✓ ... (digitando)      │
│                                       │                         │
│                                       │ "📦 2x P13 = R$220      │
│                                       │                         │
│                                       │ 📍 Qual seu endereço    │
│                                       │ de entrega?"            │
│                                       │                         │
│ "Rua das Flores 123, Boqueirão"       │                         │
│                                       │ ✓✓ ... (digitando)      │
│                                       │                         │
│                                       │ "📍 Endereço:           │
│                                       │ Rua das Flores 123      │
│                                       │ Boqueirão - Curitiba    │
│                                       │                         │
│                                       │ Está correto?"          │
│                                       │ [✅ Sim] [✏️ Alterar]   │
│                                       │                         │
│ *clica em Sim*                        │                         │
│                                       │ ✓✓ ... (digitando)      │
│                                       │                         │
│                                       │ "💰 Total: R$220        │
│                                       │                         │
│                                       │ Como deseja pagar?"     │
│                                       │ [💵 Dinheiro]           │
│                                       │ [💳 Cartão]             │
│                                       │                         │
│ *clica em Dinheiro*                   │                         │
│                                       │ ✓✓ ... (digitando)      │
│                                       │                         │
│                                       │ "✅ PEDIDO CONFIRMADO!  │
│                                       │                         │
│                                       │ 📦 Pedido #1234         │
│                                       │ 2x Botijão P13          │
│                                       │ Total: R$220            │
│                                       │ Pagamento: Dinheiro     │
│                                       │                         │
│                                       │ 📍 Rua das Flores 123   │
│                                       │ ⏱️ Previsão: 40 min     │
│                                       │                         │
│                                       │ Obrigado! 🔥"           │
│                                       │                         │
└───────────────────────────────────────┴─────────────────────────┘
```

### 3.2 Cliente Conhecido - Compra Rápida

```
┌─────────────────────────────────────────────────────────────────┐
│ CLIENTE (conhecido - João)            │ BOT                     │
├───────────────────────────────────────┼─────────────────────────┤
│                                       │                         │
│ "quero gas"                           │                         │
│                                       │ ✓✓ ... (digitando)      │
│                                       │                         │
│                                       │ "👋 Olá, João!          │
│                                       │ Que bom ter você de     │
│                                       │ volta!                  │
│                                       │                         │
│                                       │ 🔄 Repetir último       │
│                                       │ pedido?                 │
│                                       │ • 2x P13 - R$220        │
│                                       │ • Rua das Flores 123    │
│                                       │                         │
│                                       │ [✅ Sim, repetir]       │
│                                       │ [🔄 Novo pedido]        │
│                                       │                         │
│ *clica em Sim, repetir*               │                         │
│                                       │ ✓✓ ... (digitando)      │
│                                       │                         │
│                                       │ "💰 Total: R$220        │
│                                       │                         │
│                                       │ Como deseja pagar?"     │
│                                       │ [💵 Dinheiro]           │
│                                       │ [💳 Cartão]             │
│                                       │                         │
│ *clica em Dinheiro*                   │                         │
│                                       │ ✓✓ ... (digitando)      │
│                                       │                         │
│                                       │ "✅ PEDIDO #1235        │
│                                       │ CONFIRMADO!             │
│                                       │                         │
│                                       │ ⏱️ Previsão: 40 min     │
│                                       │ Obrigado, João! 🔥"     │
│                                       │                         │
└───────────────────────────────────────┴─────────────────────────┘

⏱️ TEMPO TOTAL: ~15 segundos (vs 2+ minutos no fluxo atual)
```

---

## 4. Tratamento de Variações

### 4.1 Mensagem Duplicada (WAHA Retry)

```
┌──────────────────────────────────────────────────────────────────┐
│                    DEDUPLICAÇÃO DE MENSAGENS                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Mensagem chega com message_id = "ABC123"                        │
│                     │                                            │
│                     ▼                                            │
│  ┌─────────────────────────────────────┐                        │
│  │ Redis: EXISTS msg_processed:ABC123  │                        │
│  │ ✅ IMPLEMENTADO                     │                        │
│  └─────────────────────────────────────┘                        │
│                     │                                            │
│         ┌──────────┴──────────┐                                 │
│         │                     │                                  │
│         ▼ NÃO                 ▼ SIM                             │
│  ┌─────────────┐      ┌─────────────────┐                       │
│  │ Processar   │      │ IGNORAR         │                       │
│  │ mensagem    │      │ Log: "Duplicada"│                       │
│  │ ✅ Stream   │      │ ✅ Funcionando  │                       │
│  └──────┬──────┘      └─────────────────┘                       │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────┐                        │
│  │ Redis: SET msg_processed:ABC123     │                        │
│  │        EX 3600 (1 hora TTL)         │                        │
│  │ ✅ IMPLEMENTADO                     │                        │
│  └─────────────────────────────────────┘                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Cliente Desiste no Meio

```
┌──────────────────────────────────────────────────────────────────┐
│ CLIENTE                               │ BOT                      │
├───────────────────────────────────────┼──────────────────────────┤
│                                       │                          │
│ "oi" (estado: START)                  │ "Qual produto?"          │
│                                       │ [P13] [P20] [P45]        │
│                                       │                          │
│ *clica P13* (estado: AWAITING_QTY)    │ "Quantos?"               │
│                                       │ [1] [2] [3]              │
│                                       │                          │
│ ... (30 minutos depois) ...           │                          │
│                                       │                          │
│ "oi" (contexto expirou)               │ "👋 Olá de novo!         │
│                                       │                          │
│                                       │ Vi que você estava       │
│                                       │ escolhendo P13.          │
│                                       │ Deseja continuar?"       │
│                                       │                          │
│                                       │ [✅ Continuar]           │
│                                       │ [🔄 Recomeçar]           │
│                                       │                          │
└───────────────────────────────────────┴──────────────────────────┘

LÓGICA:
- ✅ Salvar último estado no PostgreSQL (não apenas Redis) - **IMPLEMENTADO**
- ✅ Mesmo se TTL expirar, recuperar do banco - **IMPLEMENTADO**
- ❌ Perguntar se quer continuar de onde parou - **PENDENTE** (falta UX)
```

### 4.3 Mensagem Fora de Contexto

```
┌──────────────────────────────────────────────────────────────────┐
│ CLIENTE (estado: AWAITING_QUANTITY)   │ BOT                      │
├───────────────────────────────────────┼──────────────────────────┤
│                                       │                          │
│ "qual o horário de vocês?"            │ "⏰ Funcionamos de 8h    │
│                                       │ às 20h, todos os dias!  │
│                                       │                          │
│                                       │ 📦 Voltando ao pedido:   │
│                                       │ Você estava escolhendo   │
│                                       │ a quantidade do P13.     │
│                                       │                          │
│                                       │ Quantos botijões?"       │
│                                       │ [1] [2] [3]              │
│                                       │                          │
└───────────────────────────────────────┴──────────────────────────┘

LÓGICA:
- Detectar intenção da mensagem (NLU)
- Responder a pergunta
- Retornar ao fluxo atual automaticamente
```

### 4.4 Várias Mensagens Rápidas

```
┌──────────────────────────────────────────────────────────────────┐
│                    AGREGAÇÃO DE MENSAGENS                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Cliente envia rapidamente:                                      │
│    [10:00:00.100] "oi"                                          │
│    [10:00:00.300] "quero gas"                                   │
│    [10:00:00.500] "p13"                                         │
│                                                                  │
│  Em vez de processar 3x separadamente:                          │
│                                                                  │
│  ┌─────────────────────────────────────┐                        │
│  │ Agregar mensagens em janela de 1s   │                        │
│  │ "oi quero gas p13"                  │                        │
│  └─────────────────────────────────────┘                        │
│                     │                                            │
│                     ▼                                            │
│  ┌─────────────────────────────────────┐                        │
│  │ Processar como uma única intenção:  │                        │
│  │ - Detecta: quer P13                 │                        │
│  │ - Pula direto para quantidade       │                        │
│  └─────────────────────────────────────┘                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Prioridades de Implementação

### Fase 1: Correções Críticas (1-2 dias)
```
┌────┬────────────────────────────────────┬───────────┬──────────┬──────────────┐
│ #  │ Item                               │ Impacto   │ Esforço  │ Status      │
├────┼────────────────────────────────────┼───────────┼──────────┼──────────────┤
│ 1  │ Deduplicação de mensagens          │ 🔴 ALTO   │ 2h       │ ✅ FEITO    │
│ 2  │ Mostrar "digitando..." ao cliente  │ 🔴 ALTO   │ 1h       │ ❌ PENDENTE │
│ 3  │ Marcar como lida IMEDIATAMENTE     │ 🔴 ALTO   │ 30min    │ ❌ PENDENTE │
│ 4  │ Sincronizar estado context/new     │ 🟠 MÉDIO  │ -        │ ✅ FEITO    │
└────┴────────────────────────────────────┴───────────┴──────────┴──────────────┘
```

### Fase 2: Melhoria de UX (3-5 dias)
```
┌────┬────────────────────────────────────┬───────────┬──────────┬──────────────┐
│ #  │ Item                               │ Impacto   │ Esforço  │ Status      │
├────┼────────────────────────────────────┼───────────┼──────────┼──────────────┤
│ 5  │ Reconhecer cliente do Firebird     │ 🟠 MÉDIO  │ 4h       │ ⚠️ PARCIAL  │
│ 6  │ "Repetir último pedido" p/ conhec. │ 🟠 MÉDIO  │ 4h       │ ❌ PENDENTE │
│ 7  │ Continuar pedido abandonado        │ 🟠 MÉDIO  │ 3h       │ ⚠️ PARCIAL  │
│ 8  │ Responder perguntas fora contexto  │ 🟡 BAIXO  │ 8h       │ ❌ PENDENTE │
└────┴────────────────────────────────────┴───────────┴──────────┴──────────────┘
```

### Fase 3: Robustez (1 semana)
```
┌────┬────────────────────────────────────┬───────────┬──────────┬──────────────┐
│ #  │ Item                               │ Impacto   │ Esforço  │ Status      │
├────┼────────────────────────────────────┼───────────┼──────────┼──────────────┤
│ 9  │ Agregação de mensagens rápidas     │ 🟡 BAIXO  │ 6h       │ ❌ PENDENTE │
│ 10 │ Rate limiting por telefone         │ 🟡 BAIXO  │ 2h       │ ❌ PENDENTE │
│ 11 │ Timeout em background tasks        │ 🟡 BAIXO  │ 2h       │ ✅ FEITO*   │
│ 12 │ Métricas de tempo de resposta      │ 🟡 BAIXO  │ 4h       │ ⚠️ PARCIAL  │
└────┴────────────────────────────────────┴───────────┴──────────┴──────────────┘

* Timeout implementado via Redis Stream retry/DLQ
```

---

## 6. Métricas de Sucesso

### KPIs a Monitorar
| Métrica | Atual (estimado) | Meta |
|---------|------------------|------|
| Tempo médio de resposta | ~3-5s | < 1s |
| Taxa de pedidos completos | ~40% | > 80% |
| Taxa de abandono | ~60% | < 20% |
| Mensagens duplicadas | Desconhecido | 0% |
| Pedidos duplicados | Acontece | 0 |
| Satisfação do cliente | Não medida | > 4.5/5 |

---

## 7. Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ARQUITETURA IDEAL                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐   │
│  │   WhatsApp  │────▶│    WAHA     │────▶│        WEBHOOK              │   │
│  │   Cliente   │◀────│   (Docker)  │◀────│   (FastAPI + Background)    │   │
│  └─────────────┘     └─────────────┘     └──────────────┬──────────────┘   │
│                                                          │                  │
│                                          ┌───────────────┴───────────────┐  │
│                                          │                               │  │
│                                          ▼                               ▼  │
│  ┌─────────────────────────────────────────────┐   ┌──────────────────┐   │
│  │              MESSAGE QUEUE                   │   │   DEDUPLICATOR   │   │
│  │         (Redis Stream ou Celery)             │   │   (Redis SET)    │   │
│  └──────────────────────┬──────────────────────┘   └──────────────────┘   │
│                         │                                                   │
│                         ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        FLOW ENGINE                                   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ State Machine│  │   Handlers   │  │  NLU Engine  │              │   │
│  │  │   (FSM)      │  │   (Async)    │  │  (Intenções) │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                         │                                                   │
│           ┌─────────────┼─────────────┐                                    │
│           ▼             ▼             ▼                                    │
│  ┌─────────────┐  ┌───────────┐  ┌───────────┐                            │
│  │    Redis    │  │ PostgreSQL│  │  Firebird │                            │
│  │  (Contexto  │  │ (Pedidos, │  │  (Legado) │                            │
│  │   rápido)   │  │ Clientes) │  │           │                            │
│  └─────────────┘  └───────────┘  └───────────┘                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Checklist de Implementação

### Imediato (Fase 1)
- [x] ✅ Implementar deduplicação de mensagens por message_id - **FEITO**
- [ ] ❌ Adicionar "typing" indicator antes de processar - **PENDENTE**
- [ ] ❌ Marcar mensagem como lida imediatamente no webhook - **PENDENTE**
- [x] ✅ Corrigir dessincronização de estados - **FEITO**

### Curto Prazo (Fase 2)
- [ ] ⚠️ Integrar busca de cliente no Firebird - **PARCIAL** (PostgreSQL OK, falta Firebird)
- [ ] ❌ Implementar "repetir último pedido" - **PENDENTE**
- [x] ✅ Salvar contexto no PostgreSQL (backup do Redis) - **FEITO**
- [x] ⚠️ Recuperar pedido abandonado - **FEITO** (falta UX de perguntar se quer continuar)

### Médio Prazo (Fase 3)
- [ ] ❌ Agregação de mensagens rápidas - **PENDENTE**
- [ ] ❌ NLU para perguntas fora de contexto - **PENDENTE**
- [ ] ⚠️ Dashboard de métricas de conversão - **PARCIAL** (logs estruturados existem)
- [ ] ❌ A/B testing de mensagens - **PENDENTE**

---

## 🎉 MELHORIAS ADICIONAIS IMPLEMENTADAS

### ✅ Tracing Completo
- Trace ID único por mensagem
- Logs estruturados em todo o pipeline
- Rastreamento de ponta a ponta (Webhook → Stream → Consumer → Flow → WAHA → WebSocket)

### ✅ Nome do Atendente nas Mensagens
- Quando atendente assume conversa, nome aparece nas mensagens
- Formato: `"Nome do Atendente: mensagem"`
- Implementado em todos os endpoints de envio

### ✅ Pipeline Robusto
- Redis Stream para processamento assíncrono
- Consumer Groups com retry automático
- DLQ para mensagens com falha
- Lock distribuído por telefone

---

## 📊 RESUMO DO STATUS

**✅ Core Funcionando:** Pipeline completo, deduplicação, state machine, contexto persistido  
**⚠️ UX Melhorável:** Feedback imediato, reconhecimento Firebird, repetir pedido  
**📋 Roadmap:** Este documento serve como guia para próximas melhorias

**Última atualização:** 13/02/2026
