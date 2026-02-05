# Fluxo Ideal do Bot de WhatsApp - Gas Automation

## 1. Visão Geral do Problema

### Problemas Atuais Identificados
| # | Problema | Impacto no Cliente |
|---|----------|-------------------|
| 1 | Mensagens duplicadas processadas | Cliente recebe respostas duplicadas, pedidos duplicados |
| 2 | Estado perdido entre mensagens | Cliente precisa recomeçar do zero |
| 3 | Cliente não reconhecido | Pede dados que já temos |
| 4 | Ordem das mensagens incorreta | Confusão, experiência ruim |
| 5 | Sem feedback de "digitando..." | Cliente acha que bot travou |

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
│  │ - Endereço      │            └────────┬────────┘                        │
│  │ - Último pedido │                     │                                  │
│  │ - Preferências  │                     ▼                                  │
│  └─────────────────┘            ┌─────────────────┐                        │
│                                 │ Encontrou?      │                        │
│                                 └────────┬────────┘                        │
│                                    SIM   │   NÃO                           │
│                                    ▼     │    ▼                            │
│                         ┌──────────────┐ │ ┌──────────────┐                │
│                         │Migrar dados  │ │ │Criar cliente │                │
│                         │do Firebird   │ │ │novo          │                │
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
│  │                                                   │          │         │
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
│  └─────────────────┘    │ (texto/botões)  │    └─────────────────────┘     │
│                         └─────────────────┘                                 │
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
│  └─────────────────────────────────────┘                        │
│                     │                                            │
│         ┌──────────┴──────────┐                                 │
│         │                     │                                  │
│         ▼ NÃO                 ▼ SIM                             │
│  ┌─────────────┐      ┌─────────────────┐                       │
│  │ Processar   │      │ IGNORAR         │                       │
│  │ mensagem    │      │ Log: "Duplicada"│                       │
│  └──────┬──────┘      └─────────────────┘                       │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────┐                        │
│  │ Redis: SET msg_processed:ABC123     │                        │
│  │        EX 3600 (1 hora TTL)         │                        │
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
- Salvar último estado no PostgreSQL (não apenas Redis)
- Mesmo se TTL expirar, recuperar do banco
- Perguntar se quer continuar de onde parou
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
┌────┬────────────────────────────────────┬───────────┬──────────┐
│ #  │ Item                               │ Impacto   │ Esforço  │
├────┼────────────────────────────────────┼───────────┼──────────┤
│ 1  │ Deduplicação de mensagens          │ 🔴 ALTO   │ 2h       │
│ 2  │ Mostrar "digitando..." ao cliente  │ 🔴 ALTO   │ 1h       │
│ 3  │ Marcar como lida IMEDIATAMENTE     │ 🔴 ALTO   │ 30min    │
│ 4  │ Sincronizar estado context/new     │ 🟠 MÉDIO  │ Feito ✓  │
└────┴────────────────────────────────────┴───────────┴──────────┘
```

### Fase 2: Melhoria de UX (3-5 dias)
```
┌────┬────────────────────────────────────┬───────────┬──────────┐
│ #  │ Item                               │ Impacto   │ Esforço  │
├────┼────────────────────────────────────┼───────────┼──────────┤
│ 5  │ Reconhecer cliente do Firebird     │ 🟠 MÉDIO  │ 4h       │
│ 6  │ "Repetir último pedido" p/ conhec. │ 🟠 MÉDIO  │ 4h       │
│ 7  │ Continuar pedido abandonado        │ 🟠 MÉDIO  │ 3h       │
│ 8  │ Responder perguntas fora contexto  │ 🟡 BAIXO  │ 8h       │
└────┴────────────────────────────────────┴───────────┴──────────┘
```

### Fase 3: Robustez (1 semana)
```
┌────┬────────────────────────────────────┬───────────┬──────────┐
│ #  │ Item                               │ Impacto   │ Esforço  │
├────┼────────────────────────────────────┼───────────┼──────────┤
│ 9  │ Agregação de mensagens rápidas     │ 🟡 BAIXO  │ 6h       │
│ 10 │ Rate limiting por telefone         │ 🟡 BAIXO  │ 2h       │
│ 11 │ Timeout em background tasks        │ 🟡 BAIXO  │ 2h       │
│ 12 │ Métricas de tempo de resposta      │ 🟡 BAIXO  │ 4h       │
└────┴────────────────────────────────────┴───────────┴──────────┘
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
- [ ] Implementar deduplicação de mensagens por message_id
- [ ] Adicionar "typing" indicator antes de processar
- [ ] Marcar mensagem como lida imediatamente no webhook
- [ ] Corrigir dessincronização de estados (FEITO ✓)

### Curto Prazo (Fase 2)
- [ ] Integrar busca de cliente no Firebird
- [ ] Implementar "repetir último pedido"
- [ ] Salvar contexto no PostgreSQL (backup do Redis)
- [ ] Recuperar pedido abandonado

### Médio Prazo (Fase 3)
- [ ] Agregação de mensagens rápidas
- [ ] NLU para perguntas fora de contexto
- [ ] Dashboard de métricas de conversão
- [ ] A/B testing de mensagens
