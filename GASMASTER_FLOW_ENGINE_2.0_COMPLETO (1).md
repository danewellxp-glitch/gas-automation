# 🔧 GasMaster Flow Engine 2.0
## Plano Técnico Completo de Refatoração

**Versão:** 2.0.0  
**Data:** 13 de Fevereiro de 2026  
**Autor:** Fabiano Lopes  
**Status:** 📋 PROPOSTA TÉCNICA

---

# ÍNDICE GERAL

| Parte | Conteúdo | Arquivo |
|-------|----------|---------|
| 1 | Resumo Executivo e Análise do Sistema Atual | `01_RESUMO_E_ANALISE.md` |
| 2 | Nova Arquitetura e Máquina de Estados | `02_ARQUITETURA_E_ESTADOS.md` |
| 3 | Catálogo de Produtos e Configurações | `03_CATALOGO_E_CONFIGS.md` |
| 4 | Fluxos de Usuário Detalhados | `04_FLUXOS_USUARIO.md` |
| 5 | Engine NLU e Contexto Inteligente | `05_NLU_E_CONTEXTO.md` |
| 6 | Handlers, APIs e Implementação | `06_HANDLERS_E_APIS.md` |
| 7 | Migração, Métricas e Cronograma | `07_MIGRACAO_E_CRONOGRAMA.md` |

---

# PARTE 1: RESUMO EXECUTIVO E ANÁLISE

## 1.1 Visão do Projeto

O **GasMaster Flow Engine 2.0** representa uma evolução completa do sistema de atendimento automatizado via WhatsApp para distribuidoras de gás GLP. O objetivo é transformar a experiência do cliente de um **fluxo rígido baseado em menus** para uma **conversa natural e inteligente** que entende o contexto, reconhece clientes e oferece a melhor experiência possível.

### Transformação Principal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ANTES (v1.0)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Cliente: "oi"                                                             │
│   Bot: "Escolha uma opção: [1] Fazer pedido [2] Rastrear [3] Atendente"    │
│   Cliente: "1"                                                              │
│   Bot: "Você é [1] Pessoa Física [2] Pessoa Jurídica?"                     │
│   Cliente: "1"                                                              │
│   Bot: "Qual seu nome completo?"                                            │
│   ... (continua rigidamente)                                                │
│                                                                             │
│   Tempo: 3-5 minutos | Taxa de abandono: ~60%                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

                                    │
                                    │ TRANSFORMAÇÃO
                                    ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│                              DEPOIS (v2.0)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Cliente: "quero 2 P13 troca, Rua das Flores 123, cartão"                 │
│   Bot: "👋 Olá! Entendi seu pedido:                                        │
│         • 2x P13 (troca) = R$ 220                                          │
│         • Rua das Flores, 123 - Boqueirão                                  │
│         • Cartão de Crédito                                                │
│         Confirma?"                                                          │
│   Cliente: "sim"                                                            │
│   Bot: "🎉 Pedido #1234 confirmado! Previsão: 30 min"                      │
│                                                                             │
│   Tempo: 15-30 segundos | Taxa de abandono: <15%                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 1.2 Objetivos e Métricas

### KPIs Principais

| Métrica | Atual (v1.0) | Meta (v2.0) | Melhoria |
|---------|--------------|-------------|----------|
| Taxa de conclusão de pedidos | ~40% | > 85% | +112% |
| Tempo médio - cliente novo | 3-5 min | < 90 seg | -70% |
| Tempo médio - cliente conhecido | 2-3 min | < 30 seg | -83% |
| Taxa de abandono | ~60% | < 15% | -75% |
| NPS do atendimento | Não medido | > 4.5/5 | N/A |
| Tempo de resposta do bot | 3-5 seg | < 1 seg | -80% |
| Pedidos via "repetir" | 0% | > 40% | N/A |

### Objetivos de Negócio

1. **Aumentar conversão:** Mais clientes completando pedidos
2. **Reduzir tempo:** Experiência mais rápida e fluida
3. **Aumentar recorrência:** Clientes voltando com frequência
4. **Reduzir carga operacional:** Menos intervenção humana
5. **Melhorar satisfação:** Clientes recomendando o serviço

## 1.3 Princípios de Design

### 1. Conversa Natural
```
❌ ANTES: "Digite 1 para Pessoa Física ou 2 para Pessoa Jurídica"
✅ DEPOIS: "Você é pessoa física ou tem empresa?" + botões interativos
```

### 2. Zero Fricção
```
❌ ANTES: 8 etapas obrigatórias para completar pedido
✅ DEPOIS: Mínimo necessário, máximo inferido do contexto
```

### 3. Memória Persistente
```
❌ ANTES: "Qual seu nome?" (toda vez)
✅ DEPOIS: "Olá João! Repetir o pedido de 2x P13?"
```

### 4. Recuperação Inteligente
```
❌ ANTES: "Não entendi. Digite uma opção válida."
✅ DEPOIS: "Não encontrei esse bairro. Você quis dizer Boqueirão?" + sugestões
```

### 5. Humanização
```
❌ ANTES: [silêncio de 5 segundos] "Sua resposta..."
✅ DEPOIS: [✓✓ azul] [digitando...] "Olá! 😊"
```

---

## 2. ANÁLISE DO SISTEMA ATUAL (v1.0)

## 2.1 Arquitetura Existente

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ARQUITETURA ATUAL (v1.0)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│   │  WhatsApp   │────▶│    WAHA     │────▶│   Webhook   │                  │
│   │   Client    │     │   Server    │     │  (FastAPI)  │                  │
│   └─────────────┘     └─────────────┘     └──────┬──────┘                  │
│                                                  │                          │
│                                                  ▼                          │
│                                          ┌─────────────┐                    │
│                                          │Redis Stream │                    │
│                                          │(stream:msgs)│                    │
│                                          └──────┬──────┘                    │
│                                                  │                          │
│                                                  ▼                          │
│                                          ┌─────────────┐                    │
│                                          │  Consumer   │                    │
│                                          │  (Worker)   │                    │
│                                          └──────┬──────┘                    │
│                                                  │                          │
│                              ┌───────────────────┼───────────────────┐      │
│                              │                   │                   │      │
│                              ▼                   ▼                   ▼      │
│                       ┌─────────────┐    ┌─────────────┐    ┌───────────┐  │
│                       │State Machine│    │ NLP Engine  │    │  Context  │  │
│                       │(13 estados) │    │(Ollama/qwen)│    │  Manager  │  │
│                       └─────────────┘    └─────────────┘    └───────────┘  │
│                                                                             │
│                              ┌───────────────────┼───────────────────┐      │
│                              │                   │                   │      │
│                              ▼                   ▼                   ▼      │
│                       ┌─────────────┐    ┌─────────────┐    ┌───────────┐  │
│                       │ PostgreSQL  │    │    Redis    │    │ Firebird  │  │
│                       │  (Orders)   │    │  (Context)  │    │ (Legado)  │  │
│                       └─────────────┘    └─────────────┘    └───────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Estados Atuais (13 estados)

```python
class ConversationState(Enum):
    """Estados atuais do sistema v1.0"""
    
    START = "start"                           # Estado inicial
    ASKING_CUSTOMER_TYPE = "asking_customer_type"  # PF ou PJ
    COLLECTING_NAME = "collecting_name"        # Nome do cliente
    COLLECTING_DOCUMENT = "collecting_document" # CPF/CNPJ
    AWAITING_PRODUCT = "awaiting_product"      # Seleção de produto
    AWAITING_QUANTITY = "awaiting_quantity"    # Quantidade
    AWAITING_ADDRESS = "awaiting_address"      # Endereço
    CONFIRMING_ADDRESS = "confirming_address"  # Confirmar endereço
    AWAITING_PAYMENT = "awaiting_payment"      # Método pagamento
    AWAITING_PIX = "awaiting_pix"              # Pagamento PIX
    CONFIRMING_ORDER = "confirming_order"      # Confirmar pedido
    ORDER_CONFIRMED = "order_confirmed"        # Pedido confirmado
    TRACKING_ORDER = "tracking_order"          # Rastrear pedido
    TALKING_TO_HUMAN = "talking_to_human"      # Atendente humano
```

### Problema: Fluxo Linear Obrigatório

```
START → CUSTOMER_TYPE → NAME → DOCUMENT → PRODUCT → QUANTITY → ADDRESS → ...

┌────────────────────────────────────────────────────────────────────────────┐
│ PROBLEMA: Cliente deve passar por TODAS as etapas, mesmo se desnecessário │
│                                                                            │
│ Exemplo: Cliente conhecido que só quer repetir pedido                     │
│                                                                            │
│ Atual:  START → CUSTOMER_TYPE → NAME → DOCUMENT → PRODUCT → ...          │
│         (8+ etapas obrigatórias)                                          │
│                                                                            │
│ Ideal:  START → CONFIRM_REPEAT → PAYMENT → DONE                           │
│         (3 etapas apenas)                                                  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

## 2.3 Problemas Identificados

### 🔴 CRÍTICOS (Impacto Alto)

| # | Problema | Impacto | Causa Raiz |
|---|----------|---------|------------|
| 1 | **Fluxo rígido e linear** | 60% abandono | Estados sequenciais obrigatórios |
| 2 | **Não reconhece cliente existente** | Pede dados desnecessários | Falta integração Firebird completa |
| 3 | **Sem "repetir último pedido"** | Cliente demora muito | Não usa histórico |
| 4 | **Perguntas fora de contexto ignoradas** | Frustração | NLP limitado |
| 5 | **Sem validação de horário** | Pedido fora de expediente | Falta regra de negócio |

### 🟠 MÉDIOS (Impacto Moderado)

| # | Problema | Impacto | Causa Raiz |
|---|----------|---------|------------|
| 6 | **Mensagens agregadas** | Processamento incorreto | Falta debounce |
| 7 | **Sem validação de área** | Entrega impossível | Validação tardia |
| 8 | **Fast-track impossível** | Demora mesmo com dados completos | Design de estados |
| 9 | **Sem sugestões inteligentes** | Experiência genérica | Falta análise de preferências |

### 🟡 MENORES (Impacto Baixo)

| # | Problema | Impacto | Causa Raiz |
|---|----------|---------|------------|
| 10 | **Mensagens longas do bot** | Difícil leitura | Sem limite de caracteres |
| 11 | **Falta emojis e humanização** | Experiência fria | Templates fixos |
| 12 | **Sem confirmação visual** | Incerteza | Falta resumos formatados |

## 2.4 O Que Está Funcionando Bem ✅

### Pipeline de Mensagens
- ✅ **Redis Streams + Consumer Groups:** Processamento distribuído robusto
- ✅ **Deduplicação:** Mensagens duplicadas corretamente ignoradas
- ✅ **Lock distribuído:** Sem race conditions por telefone
- ✅ **DLQ:** Dead Letter Queue para falhas

### Tracing e Observabilidade
- ✅ **trace_id:** Rastreamento completo em todo pipeline
- ✅ **Logs estruturados:** Fácil debug e análise
- ✅ **Métricas Prometheus:** Monitoramento em tempo real

### Experiência do Usuário (Recente)
- ✅ **✓✓ azul imediato:** Mensagem marcada como lida
- ✅ **"Digitando...":** Feedback visual de processamento
- ✅ **Atendente humano:** Transferência funcionando

### Integrações
- ✅ **WAHA:** Envio/recebimento de mensagens
- ✅ **WebSocket:** Eventos em tempo real para painel
- ✅ **PostgreSQL:** Persistência de pedidos

---

## 3. RESUMO DA PROPOSTA

### 3.1 Principais Mudanças

| Área | Atual (v1.0) | Proposto (v2.0) |
|------|--------------|-----------------|
| **Estados** | 13 lineares | 25+ organizados em fases |
| **NLU** | Ollama apenas | Híbrido (Rule+Pattern+LLM) |
| **Contexto** | Redis simples | 3 camadas (Customer/Conversation/Order) |
| **Fluxo** | Sequencial obrigatório | Flexível com atalhos |
| **Cliente conhecido** | Tratado como novo | Fast-track com preferências |
| **Pedido abandonado** | Perdido | Detectado e recuperável |
| **Perguntas FAQ** | Ignora ou falha | Responde e retoma fluxo |

### 3.2 Arquitetura Proposta (Visão Geral)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLOW ENGINE 2.0 - VISÃO GERAL                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      CAMADA DE ENTRADA                                │  │
│  │  Message Normalizer → Media Processor → Interactive Handler          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    INTENT RECOGNITION (HÍBRIDO)                       │  │
│  │  Keyword Matcher (10ms) → Pattern Recognizer (20ms) → LLM (300ms)   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                       CONTEXT MANAGER                                 │  │
│  │  CustomerContext (quem) + ConversationContext (onde) + OrderContext  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    STATE MACHINE 2.0 (FASES)                         │  │
│  │  GREETING → IDENTIFY → ORDERING → CHECKOUT → COMPLETE                │  │
│  │                     + SUPPORT STATES (paralelos)                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     RESPONSE GENERATOR                                │  │
│  │  Template Engine + Personalization + Interactive Elements            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Benefícios Esperados

1. **Para o Cliente:**
   - Pedido em 15 segundos (cliente conhecido)
   - Conversa natural, não menus
   - Preferências lembradas
   - Recuperação de pedidos abandonados

2. **Para a Operação:**
   - Menos intervenção humana
   - Menos abandonos = mais vendas
   - Dados de preferências dos clientes
   - Métricas detalhadas de conversão

3. **Para o Desenvolvimento:**
   - Código mais organizado (handlers por estado)
   - Fácil adicionar novos estados
   - Testes unitários por componente
   - Configuração externalizada

---

*Continua em: `02_ARQUITETURA_E_ESTADOS.md`*
# PARTE 2: NOVA ARQUITETURA E MÁQUINA DE ESTADOS

## 4. ARQUITETURA FLOW ENGINE 2.0

### 4.1 Diagrama de Arquitetura Completo

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FLOW ENGINE 2.0                                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐ │
│  │                           CAMADA 1: ENTRADA                                        │ │
│  │ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────────┐ │ │
│  │ │ Message         │  │ Media           │  │ Interactive Handler                 │ │ │
│  │ │ Normalizer      │  │ Processor       │  │ (Buttons/Lists/Location)            │ │ │
│  │ │                 │  │                 │  │                                     │ │ │
│  │ │ • Limpa texto   │  │ • Imagens       │  │ • Button clicks                     │ │ │
│  │ │ • Remove acentos│  │ • Áudio → Texto │  │ • List selections                   │ │ │
│  │ │ • Lowercase     │  │ • Documentos    │  │ • Location sharing                  │ │ │
│  │ └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────────────┘ │ │
│  │          └────────────────────┴──────────────────────────┘                         │ │
│  │                                      │                                             │ │
│  │                                      ▼                                             │ │
│  │                         ┌───────────────────────┐                                  │ │
│  │                         │   NormalizedMessage   │                                  │ │
│  │                         │   {text, type, meta}  │                                  │ │
│  │                         └───────────────────────┘                                  │ │
│  └───────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                              │
│                                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐ │
│  │                      CAMADA 2: INTENT RECOGNITION (HÍBRIDO)                        │ │
│  │                                                                                    │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │                        PRIORIDADE DE PROCESSAMENTO                          │   │ │
│  │  │                                                                            │   │ │
│  │  │   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     │   │ │
│  │  │   │ 1. KEYWORD      │     │ 2. PATTERN      │     │ 3. LLM          │     │   │ │
│  │  │   │    MATCHER      │────▶│    RECOGNIZER   │────▶│    CLASSIFIER   │     │   │ │
│  │  │   │                 │     │                 │     │                 │     │   │ │
│  │  │   │ Tempo: < 10ms   │     │ Tempo: < 20ms   │     │ Tempo: 100-300ms│     │   │ │
│  │  │   │ Confiança: 95%+ │     │ Confiança: 85%+ │     │ Confiança: 70%+ │     │   │ │
│  │  │   │                 │     │                 │     │                 │     │   │ │
│  │  │   │ Ex: "menu"      │     │ Ex: "2 p13"     │     │ Ex: mensagens   │     │   │ │
│  │  │   │     "rastrear"  │     │     "cpf 123"   │     │     complexas   │     │   │ │
│  │  │   └─────────────────┘     └─────────────────┘     └─────────────────┘     │   │ │
│  │  │                                                                            │   │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘   │ │
│  │                                                                                    │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │                        ENTITY EXTRACTOR (SEMPRE)                            │   │ │
│  │  │   Produtos | Quantidades | CPF/CNPJ | Endereços | Pagamento | Valores      │   │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                              │
│                                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐ │
│  │                         CAMADA 3: CONTEXT MANAGER                                  │ │
│  │                                                                                    │ │
│  │  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐         │ │
│  │  │  CustomerContext    │ │ ConversationContext │ │   OrderContext      │         │ │
│  │  │  (PERSISTENTE)      │ │ (SESSÃO - 30min)    │ │  (PEDIDO - 2h)      │         │ │
│  │  │                     │ │                     │ │                     │         │ │
│  │  │  • customer_id      │ │ • session_id        │ │ • items[]           │         │ │
│  │  │  • name             │ │ • current_state     │ │ • subtotal          │         │ │
│  │  │  • document         │ │ • state_history     │ │ • delivery_fee      │         │ │
│  │  │  • addresses[]      │ │ • collected_data    │ │ • total             │         │ │
│  │  │  • last_order       │ │ • flow_step         │ │ • address           │         │ │
│  │  │  • preferences      │ │ • is_returning      │ │ • payment_method    │         │ │
│  │  │  • order_count      │ │ • needs_human       │ │ • operation_type    │         │ │
│  │  │  • is_vip           │ │ • return_state      │ │ • validation_errors │         │ │
│  │  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘         │ │
│  │                                                                                    │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │                        STORAGE LAYERS                                       │   │ │
│  │  │   Redis (cache rápido) ←→ PostgreSQL (backup) ←→ Firebird (legado)        │   │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                              │
│                                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐ │
│  │                         CAMADA 4: STATE MACHINE 2.0                                │ │
│  │                                                                                    │ │
│  │     ┌──────────────────────────────────────────────────────────────────────────┐  │ │
│  │     │                         FLUXO PRINCIPAL                                   │  │ │
│  │     │                                                                          │  │ │
│  │     │  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐ │  │ │
│  │     │  │GREETING │──▶│ IDENTIFY │──▶│ ORDERING │──▶│ CHECKOUT │──▶│COMPLETE│ │  │ │
│  │     │  │  PHASE  │   │  PHASE   │   │  PHASE   │   │  PHASE   │   │ PHASE  │ │  │ │
│  │     │  │ (2 est.)│   │ (5 est.) │   │ (8 est.) │   │ (3 est.) │   │(2 est.)│ │  │ │
│  │     │  └─────────┘   └──────────┘   └──────────┘   └──────────┘   └────────┘ │  │ │
│  │     │       │              │              │              │              │      │  │ │
│  │     │       └──────────────┴──────────────┴──────────────┴──────────────┘      │  │ │
│  │     │                                ATALHOS                                    │  │ │
│  │     │                (cliente conhecido pode pular fases)                      │  │ │
│  │     └──────────────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                                    │ │
│  │     ┌──────────────────────────────────────────────────────────────────────────┐  │ │
│  │     │                    ESTADOS DE SUPORTE (PARALELOS)                        │  │ │
│  │     │  Acessíveis de QUALQUER estado do fluxo principal                        │  │ │
│  │     │                                                                          │  │ │
│  │     │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐     │  │ │
│  │     │  │  SUPPORT   │  │  TRACKING  │  │   HUMAN    │  │     FAQ        │     │  │ │
│  │     │  │   MENU     │  │   STATUS   │  │  HANDOFF   │  │   INLINE       │     │  │ │
│  │     │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘     │  │ │
│  │     └──────────────────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                              │
│                                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        CAMADA 5: RESPONSE GENERATOR                                │ │
│  │                                                                                    │ │
│  │  ┌────────────────┐  ┌────────────────────┐  ┌──────────────────────────────┐    │ │
│  │  │ Template       │  │ Personalization    │  │ Interactive Elements          │    │ │
│  │  │ Engine         │  │ Engine             │  │ Builder                       │    │ │
│  │  │                │  │                    │  │                               │    │ │
│  │  │ • Jinja2       │  │ • Nome do cliente  │  │ • Buttons (até 3)            │    │ │
│  │  │ • Variáveis    │  │ • Preferências     │  │ • Lists (até 10 itens)       │    │ │
│  │  │ • Condicionais │  │ • Histórico        │  │ • Location request           │    │ │
│  │  │ • Formatação   │  │ • Contexto         │  │ • Reply buttons              │    │ │
│  │  └────────────────┘  └────────────────────┘  └──────────────────────────────┘    │ │
│  └───────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Componentes Principais

#### Message Normalizer
```python
@dataclass
class NormalizedMessage:
    """Mensagem normalizada para processamento uniforme"""
    
    # Conteúdo
    raw_text: str                    # Texto original
    normalized_text: str             # Texto limpo, lowercase, sem acentos
    
    # Tipo
    message_type: MessageType        # TEXT, BUTTON, LIST_REPLY, LOCATION, etc.
    
    # Metadados
    message_id: str
    timestamp: datetime
    
    # Dados específicos por tipo
    interactive_payload: Optional[dict]  # Dados de botão/lista clicada
    location: Optional[Location]         # Coordenadas se enviou localização
    media_url: Optional[str]             # URL de mídia se houver

class MessageType(Enum):
    TEXT = "text"                    # Mensagem de texto livre
    BUTTON_REPLY = "button_reply"    # Clicou em botão
    LIST_REPLY = "list_reply"        # Selecionou item de lista
    LOCATION = "location"            # Compartilhou localização
    IMAGE = "image"                  # Enviou imagem
    AUDIO = "audio"                  # Enviou áudio
    DOCUMENT = "document"            # Enviou documento
```

---

## 5. MÁQUINA DE ESTADOS 2.0

### 5.1 Filosofia de Design

A nova máquina de estados é organizada em **FASES** ao invés de estados lineares:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ORGANIZAÇÃO POR FASES vs ESTADOS LINEARES                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ANTES (v1.0): Estados Lineares                                            │
│  ─────────────────────────────────                                         │
│  START → TYPE → NAME → DOC → PRODUCT → QTY → ADDR → CONFIRM → PAYMENT → END│
│    │       │      │     │       │       │      │        │         │        │
│    └───────┴──────┴─────┴───────┴───────┴──────┴────────┴─────────┘        │
│              Cada etapa é OBRIGATÓRIA, sem atalhos                         │
│                                                                             │
│  DEPOIS (v2.0): Fases com Atalhos                                          │
│  ────────────────────────────────                                          │
│                                                                             │
│  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐   │
│  │GREETING │   │ IDENTIFY │   │ ORDERING │   │ CHECKOUT │   │COMPLETE│   │
│  │  PHASE  │   │  PHASE   │   │  PHASE   │   │  PHASE   │   │ PHASE  │   │
│  │         │   │          │   │          │   │          │   │        │   │
│  │ initial │   │ type     │   │ product  │   │ payment  │   │ confirm│   │
│  │ return  │   │ name_pf  │   │ quantity │   │ change   │   │ follow │   │
│  │         │   │ name_pj  │   │ operation│   │ summary  │   │        │   │
│  │         │   │ cpf      │   │ more     │   │          │   │        │   │
│  │         │   │ cnpj     │   │ address  │   │          │   │        │   │
│  │         │   │          │   │ confirm  │   │          │   │        │   │
│  │         │   │          │   │ complement│  │          │   │        │   │
│  └────┬────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────────┘   │
│       │             │              │              │                        │
│       └─────────────┴──────────────┴──────────────┘                        │
│                        ATALHOS POSSÍVEIS:                                   │
│       • Cliente conhecido: GREETING → ORDERING (pula IDENTIFY)             │
│       • Repetir pedido: GREETING → CHECKOUT (pula ORDERING)                │
│       • Fast-track: GREETING → CHECKOUT (com todos dados na msg)           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Lista Completa de Estados (25 estados)

```python
class ConversationState(Enum):
    """
    Estados organizados em fases lógicas.
    Nomenclatura: FASE_ACAO
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 1: GREETING (Boas-vindas) - 2 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    GREETING_INITIAL = "greeting_initial"
    """
    Estado inicial - primeira mensagem do cliente.
    
    TRANSIÇÕES:
    → Cliente conhecido → GREETING_RETURNING
    → Cliente novo → IDENTIFY_TYPE
    → Intenção clara com dados → ORDERING_PRODUCT (fast-track)
    → "falar com atendente" → SUPPORT_HUMAN
    → "rastrear pedido" → TRACKING_STATUS
    """
    
    GREETING_RETURNING = "greeting_returning"
    """
    Cliente conhecido retornando.
    
    TRANSIÇÕES:
    → Repetir pedido → ORDERING_CONFIRM_REPEAT
    → Novo pedido → ORDERING_PRODUCT
    → Continuar abandonado → Estado onde parou
    → Tem pedido em andamento → TRACKING_STATUS
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 2: IDENTIFY (Identificação) - 5 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    IDENTIFY_TYPE = "identify_type"
    """
    Pergunta se é PF ou PJ.
    
    TRANSIÇÕES:
    → Pessoa Física → IDENTIFY_NAME_PF
    → Pessoa Jurídica → IDENTIFY_NAME_PJ
    """
    
    IDENTIFY_NAME_PF = "identify_name_pf"
    """Coleta nome completo (PF). → IDENTIFY_DOCUMENT_CPF"""
    
    IDENTIFY_NAME_PJ = "identify_name_pj"
    """Coleta razão social (PJ). → IDENTIFY_DOCUMENT_CNPJ"""
    
    IDENTIFY_DOCUMENT_CPF = "identify_document_cpf"
    """Coleta e valida CPF. → ORDERING_PRODUCT"""
    
    IDENTIFY_DOCUMENT_CNPJ = "identify_document_cnpj"
    """Coleta e valida CNPJ. → ORDERING_PRODUCT"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 3: ORDERING (Pedido) - 8 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    ORDERING_PRODUCT = "ordering_product"
    """
    Seleção de produto(s).
    
    TRANSIÇÕES:
    → Produto selecionado → ORDERING_QUANTITY
    → Múltiplos produtos → Processa todos e vai para ORDERING_OPERATION
    """
    
    ORDERING_QUANTITY = "ordering_quantity"
    """Define quantidade. → ORDERING_OPERATION"""
    
    ORDERING_OPERATION = "ordering_operation"
    """
    Tipo de operação: Troca / Venda / Retira.
    
    TRANSIÇÕES:
    → Troca ou Venda → ORDERING_MORE_ITEMS
    → Retira → ORDERING_MORE_ITEMS (sem delivery)
    """
    
    ORDERING_MORE_ITEMS = "ordering_more_items"
    """
    Pergunta se quer adicionar mais.
    
    TRANSIÇÕES:
    → Sim → ORDERING_PRODUCT
    → Não + Retira → CHECKOUT_PAYMENT
    → Não + Entrega → ORDERING_ADDRESS
    """
    
    ORDERING_ADDRESS = "ordering_address"
    """
    Coleta endereço de entrega.
    
    TRANSIÇÕES:
    → Endereço válido → ORDERING_ADDRESS_CONFIRM
    → Cliente tem endereços → Oferece seleção
    → Fora da área → Informa e pede outro
    """
    
    ORDERING_ADDRESS_CONFIRM = "ordering_address_confirm"
    """Confirma endereço formatado. → ORDERING_COMPLEMENT"""
    
    ORDERING_COMPLEMENT = "ordering_complement"
    """Coleta complemento/referência. → CHECKOUT_PAYMENT"""
    
    ORDERING_CONFIRM_REPEAT = "ordering_confirm_repeat"
    """
    Confirma repetição do último pedido.
    
    TRANSIÇÕES:
    → Confirmar → CHECKOUT_PAYMENT
    → Alterar → ORDERING_PRODUCT
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 4: CHECKOUT (Finalização) - 3 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    CHECKOUT_PAYMENT = "checkout_payment"
    """
    Seleção de pagamento.
    
    TRANSIÇÕES:
    → Dinheiro → CHECKOUT_CHANGE
    → Outros → CHECKOUT_SUMMARY
    """
    
    CHECKOUT_CHANGE = "checkout_change"
    """Pergunta troco para quanto. → CHECKOUT_SUMMARY"""
    
    CHECKOUT_SUMMARY = "checkout_summary"
    """
    Mostra resumo e pede confirmação.
    
    TRANSIÇÕES:
    → Confirmar → COMPLETE_CONFIRMED
    → Alterar produto → ORDERING_PRODUCT
    → Alterar endereço → ORDERING_ADDRESS
    → Alterar pagamento → CHECKOUT_PAYMENT
    → Cancelar → GREETING_INITIAL
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # FASE 5: COMPLETE (Conclusão) - 2 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    COMPLETE_CONFIRMED = "complete_confirmed"
    """Pedido confirmado com sucesso. → COMPLETE_FOLLOWUP"""
    
    COMPLETE_FOLLOWUP = "complete_followup"
    """
    Pós-venda e acompanhamento.
    
    TRANSIÇÕES:
    → Rastrear → TRACKING_STATUS
    → Novo pedido → ORDERING_PRODUCT
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # ESTADOS DE SUPORTE (Paralelos) - 5 estados
    # ═══════════════════════════════════════════════════════════════════════
    
    SUPPORT_HUMAN = "support_human"
    """
    Atendimento humano.
    Acessível de qualquer estado via "falar com atendente".
    Retorna ao estado anterior quando liberado.
    """
    
    SUPPORT_FAQ = "support_faq"
    """
    Respondendo pergunta frequente inline.
    Responde e retorna ao estado anterior automaticamente.
    """
    
    TRACKING_STATUS = "tracking_status"
    """Mostrando status do pedido. → TRACKING_OPTIONS"""
    
    TRACKING_OPTIONS = "tracking_options"
    """
    Opções após ver status.
    
    TRANSIÇÕES:
    → Atualizar → TRACKING_STATUS
    → Problema → SUPPORT_HUMAN
    → Novo pedido → ORDERING_PRODUCT
    """
    
    ERROR_RECOVERY = "error_recovery"
    """Estado de recuperação após erro crítico."""
```

### 5.3 Diagrama de Transições Completo

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           DIAGRAMA DE TRANSIÇÕES COMPLETO                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│                              ┌──────────────────────────┐                               │
│                              │      SUPPORT_HUMAN       │◀─── "atendente" (qualquer)   │
│                              │   (estado paralelo)      │                               │
│                              └──────────────────────────┘                               │
│                                                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                 FLUXO PRINCIPAL                                   │  │
│  │                                                                                   │  │
│  │         ┌─────────────────┐                                                      │  │
│  │         │    MENSAGEM     │                                                      │  │
│  │         │    RECEBIDA     │                                                      │  │
│  │         └────────┬────────┘                                                      │  │
│  │                  │                                                               │  │
│  │                  ▼                                                               │  │
│  │         ┌─────────────────┐                                                      │  │
│  │         │    GREETING     │                                                      │  │
│  │         │    INITIAL      │                                                      │  │
│  │         └────────┬────────┘                                                      │  │
│  │                  │                                                               │  │
│  │        ┌─────────┴─────────┐                                                     │  │
│  │        │                   │                                                     │  │
│  │        ▼                   ▼                                                     │  │
│  │  Cliente NOVO        Cliente CONHECIDO                                           │  │
│  │        │                   │                                                     │  │
│  │        ▼                   ▼                                                     │  │
│  │  ┌───────────┐      ┌────────────────┐                                          │  │
│  │  │ IDENTIFY  │      │   GREETING     │                                          │  │
│  │  │   TYPE    │      │   RETURNING    │                                          │  │
│  │  └─────┬─────┘      └───────┬────────┘                                          │  │
│  │        │                    │                                                    │  │
│  │   ┌────┴────┐         ┌────┴────┬──────────┐                                    │  │
│  │   │         │         │         │          │                                    │  │
│  │   ▼         ▼         ▼         ▼          ▼                                    │  │
│  │  PF        PJ      Repetir   Novo     Continuar                                 │  │
│  │   │         │      pedido   pedido   abandonado                                 │  │
│  │   ▼         ▼         │         │          │                                    │  │
│  │ NAME_PF  NAME_PJ      │         │          │                                    │  │
│  │   │         │         │         │          │                                    │  │
│  │   ▼         ▼         │         │          │                                    │  │
│  │  CPF      CNPJ        │         │          │                                    │  │
│  │   │         │         │         │          │                                    │  │
│  │   └────┬────┘         │         │          │                                    │  │
│  │        │              │         │          │                                    │  │
│  │        └──────────────┼─────────┴──────────┘                                    │  │
│  │                       │                                                         │  │
│  │                       ▼                                                         │  │
│  │              ┌────────────────┐                                                 │  │
│  │              │   ORDERING     │◀────────────────────────────────┐               │  │
│  │              │    PRODUCT     │                                 │               │  │
│  │              └───────┬────────┘                                 │               │  │
│  │                      │                                          │               │  │
│  │                      ▼                                          │               │  │
│  │              ┌────────────────┐                                 │               │  │
│  │              │   ORDERING     │                                 │               │  │
│  │              │   QUANTITY     │                                 │               │  │
│  │              └───────┬────────┘                                 │               │  │
│  │                      │                                          │               │  │
│  │                      ▼                                          │               │  │
│  │              ┌────────────────┐                                 │               │  │
│  │              │   ORDERING     │                                 │               │  │
│  │              │   OPERATION    │  (Troca / Venda / Retira)       │               │  │
│  │              └───────┬────────┘                                 │               │  │
│  │                      │                                          │               │  │
│  │                      ▼                                          │               │  │
│  │              ┌────────────────┐          SIM                    │               │  │
│  │              │   ORDERING     │─────────────────────────────────┘               │  │
│  │              │  MORE_ITEMS    │     "Adicionar mais"                            │  │
│  │              └───────┬────────┘                                                 │  │
│  │                      │ NÃO                                                      │  │
│  │                      │                                                          │  │
│  │        ┌─────────────┴─────────────┐                                           │  │
│  │        │                           │                                            │  │
│  │   Se ENTREGA                  Se RETIRA                                         │  │
│  │        │                           │                                            │  │
│  │        ▼                           │                                            │  │
│  │  ┌───────────────┐                 │                                            │  │
│  │  │   ORDERING    │                 │                                            │  │
│  │  │   ADDRESS     │                 │                                            │  │
│  │  └───────┬───────┘                 │                                            │  │
│  │          │                         │                                            │  │
│  │          ▼                         │                                            │  │
│  │  ┌───────────────┐                 │                                            │  │
│  │  │   ORDERING    │                 │                                            │  │
│  │  │ADDR_CONFIRM   │                 │                                            │  │
│  │  └───────┬───────┘                 │                                            │  │
│  │          │                         │                                            │  │
│  │          ▼                         │                                            │  │
│  │  ┌───────────────┐                 │                                            │  │
│  │  │   ORDERING    │                 │                                            │  │
│  │  │  COMPLEMENT   │                 │                                            │  │
│  │  └───────┬───────┘                 │                                            │  │
│  │          │                         │                                            │  │
│  │          └─────────────┬───────────┘                                            │  │
│  │                        │                                                        │  │
│  │                        ▼                                                        │  │
│  │              ┌────────────────┐                                                 │  │
│  │              │   CHECKOUT     │                                                 │  │
│  │              │   PAYMENT      │                                                 │  │
│  │              └───────┬────────┘                                                 │  │
│  │                      │                                                          │  │
│  │        ┌─────────────┴─────────────┐                                           │  │
│  │        │                           │                                            │  │
│  │   Se DINHEIRO                  OUTROS                                           │  │
│  │        │                           │                                            │  │
│  │        ▼                           │                                            │  │
│  │  ┌───────────────┐                 │                                            │  │
│  │  │   CHECKOUT    │                 │                                            │  │
│  │  │    CHANGE     │                 │                                            │  │
│  │  └───────┬───────┘                 │                                            │  │
│  │          │                         │                                            │  │
│  │          └─────────────┬───────────┘                                            │  │
│  │                        │                                                        │  │
│  │                        ▼                                                        │  │
│  │              ┌────────────────┐                                                 │  │
│  │              │   CHECKOUT     │                                                 │  │
│  │              │   SUMMARY      │                                                 │  │
│  │              └───────┬────────┘                                                 │  │
│  │                      │                                                          │  │
│  │                      │ CONFIRMAR                                                │  │
│  │                      ▼                                                          │  │
│  │              ┌────────────────┐                                                 │  │
│  │              │   COMPLETE     │                                                 │  │
│  │              │   CONFIRMED    │                                                 │  │
│  │              └───────┬────────┘                                                 │  │
│  │                      │                                                          │  │
│  │                      ▼                                                          │  │
│  │              ┌────────────────┐                                                 │  │
│  │              │   COMPLETE     │                                                 │  │
│  │              │   FOLLOWUP     │                                                 │  │
│  │              └────────────────┘                                                 │  │
│  │                                                                                   │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Atalhos Especiais

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ATALHOS ESPECIAIS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. FAST-TRACK (Cliente fornece tudo na primeira mensagem)                 │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                             │
│     Mensagem: "quero 2 P13 troca, Rua das Flores 123, cartão"              │
│                                                                             │
│     GREETING_INITIAL ──────────────────────▶ CHECKOUT_SUMMARY              │
│     (pula IDENTIFY, ORDERING inteiros)                                      │
│                                                                             │
│  2. REPETIR PEDIDO (Cliente conhecido)                                      │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                             │
│     Mensagem: "quero repetir o pedido"                                     │
│                                                                             │
│     GREETING_RETURNING ──────────────────────▶ ORDERING_CONFIRM_REPEAT     │
│     (pula todo ORDERING, só confirma)                                       │
│                                                                             │
│  3. CLIENTE CONHECIDO + MESMO ENDEREÇO                                      │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                             │
│     ORDERING_MORE_ITEMS ──────────────────────▶ CHECKOUT_PAYMENT           │
│     (pula ADDRESS se cliente confirma usar mesmo)                           │
│                                                                             │
│  4. FAQ INLINE (Pergunta durante pedido)                                    │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                             │
│     ORDERING_PRODUCT ──▶ SUPPORT_FAQ ──▶ ORDERING_PRODUCT                  │
│     (responde e volta ao estado anterior)                                   │
│                                                                             │
│  5. ATENDENTE HUMANO (De qualquer lugar)                                    │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                             │
│     QUALQUER_ESTADO ──▶ SUPPORT_HUMAN ──▶ ESTADO_ANTERIOR                  │
│     (salva estado, transfere, depois volta)                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*Continua em: `03_CATALOGO_E_CONFIGS.md`*
# PARTE 3: CATÁLOGO DE PRODUTOS E CONFIGURAÇÕES

## 6. PRODUTOS GLP

### 6.1 Estrutura de Produto

```python
@dataclass
class Product:
    """Produto GLP disponível para venda"""
    
    # Identificação
    code: str              # Código interno (ex: "P13")
    name: str              # Nome para exibição
    description: str       # Descrição curta
    
    # Especificações
    weight_kg: float       # Peso em kg
    
    # Preços
    price_exchange: Decimal  # Preço na TROCA (com vasilhame vazio)
    price_sale: Decimal      # Preço na VENDA (sem vasilhame)
    deposit_value: Decimal   # Valor do vasilhame (caução)
    
    # Controle de estoque
    stock: int             # Quantidade em estoque
    min_quantity: int      # Quantidade mínima por pedido
    max_quantity: int      # Quantidade máxima por pedido
    
    # Flags
    is_active: bool        # Se está disponível para venda
    is_commercial: bool    # Se é produto comercial (PJ)
    
    # Exibição
    emoji: str             # Emoji para WhatsApp
    sort_order: int        # Ordem de exibição
```

### 6.2 Catálogo de Produtos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CATÁLOGO DE PRODUTOS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        🔵 BOTIJÃO P13 (13kg)                           │ │
│  │                           Uso Residencial                              │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                       │ │
│  │  Preço TROCA:     R$ 110,00   (cliente entrega vasilhame vazio)      │ │
│  │  Preço VENDA:     R$ 210,00   (inclui caução do vasilhame)           │ │
│  │  Valor Caução:    R$ 100,00   (devolvido se retornar vasilhame)      │ │
│  │                                                                       │ │
│  │  Quantidade:      Mín: 1 | Máx: 10 por pedido                        │ │
│  │  Disponível:      ✅ Ativo                                            │ │
│  │  Tipo:            Residencial (PF e PJ)                               │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        🟢 BOTIJÃO P20 (20kg)                           │ │
│  │                              Uso Misto                                 │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                       │ │
│  │  Preço TROCA:     R$ 150,00                                          │ │
│  │  Preço VENDA:     R$ 280,00                                          │ │
│  │  Valor Caução:    R$ 130,00                                          │ │
│  │                                                                       │ │
│  │  Quantidade:      Mín: 1 | Máx: 5 por pedido                         │ │
│  │  Disponível:      ✅ Ativo                                            │ │
│  │  Tipo:            Misto (PF e PJ)                                     │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        🟠 BOTIJÃO P45 (45kg)                           │ │
│  │                            Uso Comercial                               │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                       │ │
│  │  Preço TROCA:     R$ 280,00                                          │ │
│  │  Preço VENDA:     R$ 480,00                                          │ │
│  │  Valor Caução:    R$ 200,00                                          │ │
│  │                                                                       │ │
│  │  Quantidade:      Mín: 1 | Máx: 3 por pedido                         │ │
│  │  Disponível:      ✅ Ativo                                            │ │
│  │  Tipo:            Comercial (PF e PJ)                                 │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Configuração Python

```python
PRODUCTS_CATALOG = {
    "P13": Product(
        code="P13",
        name="Botijão P13",
        description="Botijão residencial 13kg",
        weight_kg=13.0,
        price_exchange=Decimal("110.00"),
        price_sale=Decimal("110.00"),   # Gás de cozinha (site)
        deposit_value=Decimal("100.00"),
        stock=100,
        min_quantity=1,
        max_quantity=10,
        is_active=True,
        is_commercial=False,
        emoji="🔵",
        sort_order=1
    ),
    "P20": Product(
        code="P20",
        name="Botijão P20",
        description="Botijão médio 20kg",
        weight_kg=20.0,
        price_exchange=Decimal("210.00"),
        price_sale=Decimal("210.00"),   # Industrial empilhadeiras (site)
        deposit_value=Decimal("130.00"),
        stock=50,
        min_quantity=1,
        max_quantity=5,
        is_active=True,
        is_commercial=False,
        emoji="🟢",
        sort_order=2
    ),
    "P45": Product(
        code="P45",
        name="Botijão P45",
        description="Botijão comercial 45kg",
        weight_kg=45.0,
        price_exchange=Decimal("430.00"),
        price_sale=Decimal("430.00"),   # Doméstico/industrial (site)
        deposit_value=Decimal("200.00"),
        stock=30,
        min_quantity=1,
        max_quantity=3,
        is_active=True,
        is_commercial=True,
        emoji="🟠",
        sort_order=3
    ),
}
```

---

## 7. TIPOS DE OPERAÇÃO

### 7.1 Definição

```python
class OperationType(Enum):
    """Tipos de operação disponíveis"""
    
    EXCHANGE = "exchange"    # TROCA
    SALE = "sale"            # VENDA
    PICKUP = "pickup"        # RETIRA
```

### 7.2 Detalhamento

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TIPOS DE OPERAÇÃO                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                          🔄 TROCA (Exchange)                           │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                       │ │
│  │  Descrição:   Cliente entrega vasilhame VAZIO e recebe CHEIO         │ │
│  │                                                                       │ │
│  │  Preço:       Preço de troca (mais barato)                           │ │
│  │               Ex: P13 = R$ 110,00                                     │ │
│  │                                                                       │ │
│  │  Requisitos:  - Vasilhame em bom estado                              │ │
│  │               - Mesma marca/tipo (ideal)                             │ │
│  │               - Entregador verifica no local                         │ │
│  │                                                                       │ │
│  │  Observação:  Se vasilhame estiver danificado, pode cobrar diferença │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                          🆕 VENDA (Sale)                               │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                       │ │
│  │  Descrição:   Cliente compra gás + vasilhame (primeira compra)       │ │
│  │                                                                       │ │
│  │  Preço:       Preço de venda = Preço troca + Caução                  │ │
│  │               Ex: P13 = R$ 110,00 + R$ 100,00 = R$ 210,00            │ │
│  │                                                                       │ │
│  │  Requisitos:  Nenhum vasilhame necessário                            │ │
│  │                                                                       │ │
│  │  Observação:  - Cliente recebe recibo do vasilhame                   │ │
│  │               - Caução pode ser devolvida se entregar vasilhame      │ │
│  │               - Próximas compras podem ser TROCA                     │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                          🏪 RETIRA (Pickup)                            │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                       │ │
│  │  Descrição:   Cliente busca na loja (sem entrega)                    │ │
│  │                                                                       │ │
│  │  Preço:       Mesmo preço (troca ou venda)                           │ │
│  │               SEM taxa de entrega                                     │ │
│  │                                                                       │ │
│  │  Requisitos:  - Disponibilidade em estoque                           │ │
│  │               - Horário de funcionamento                             │ │
│  │                                                                       │ │
│  │  Horários:    Seg-Sex: 8h-18h | Sáb: 8h-12h                         │ │
│  │                                                                       │ │
│  │  Endereço:    Rua Principal, 1000 - Boqueirão                        │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. MÉTODOS DE PAGAMENTO

### 8.1 Estrutura

```python
@dataclass
class PaymentMethod:
    """Configuração de método de pagamento"""
    
    code: str                    # Código interno
    name: str                    # Nome para exibição
    description: str             # Descrição
    emoji: str                   # Emoji para WhatsApp
    
    # Disponibilidade
    is_active: bool
    available_for: List[str]     # ["pf", "pj"] ou ambos
    
    # Configuração
    requires_confirmation: bool   # Se precisa confirmar recebimento
    requires_change: bool         # Se precisa perguntar troco
    
    # Limites
    min_value: Optional[Decimal]
    max_value: Optional[Decimal]
```

### 8.2 Métodos Disponíveis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MÉTODOS DE PAGAMENTO                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  💵 DINHEIRO                                                         │   │
│  │                                                                      │   │
│  │  • Paga ao entregador na entrega                                    │   │
│  │  • Pode precisar de troco (perguntar "troco para quanto?")          │   │
│  │  • Limite: até R$ 500,00 por pedido (segurança)                     │   │
│  │  • Disponível: PF e PJ                                              │   │
│  │  • Status: ✅ Ativo                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  💳 CARTÃO DE CRÉDITO                                                │   │
│  │                                                                      │   │
│  │  • Máquina do entregador                                            │   │
│  │  • Parcelamento disponível (2x a 6x sem juros)                      │   │
│  │  • Bandeiras: Visa, Mastercard, Elo, Amex                           │   │
│  │  • Disponível: PF e PJ                                              │   │
│  │  • Status: ✅ Ativo                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  💳 CARTÃO DE DÉBITO                                                 │   │
│  │                                                                      │   │
│  │  • Máquina do entregador                                            │   │
│  │  • Apenas à vista                                                   │   │
│  │  • Bandeiras: Visa, Mastercard, Elo                                 │   │
│  │  • Disponível: PF e PJ                                              │   │
│  │  • Status: ✅ Ativo                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📱 PIX                                                              │   │
│  │                                                                      │   │
│  │  • Pagamento instantâneo                                            │   │
│  │  • Chave: (41) 99999-9999 ou CNPJ                                   │   │
│  │  • Pode pagar antes ou na entrega                                   │   │
│  │  • Enviar comprovante para agilizar                                 │   │
│  │  • Disponível: PF e PJ                                              │   │
│  │  • Status: ✅ Ativo                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📄 BOLETO / FATURADO                                                │   │
│  │                                                                      │   │
│  │  • Apenas para Pessoa Jurídica com cadastro                         │   │
│  │  • Faturamento mensal (se convênio ativo)                           │   │
│  │  • Valor mínimo: R$ 200,00                                          │   │
│  │  • Prazo: 15/30 dias (conforme contrato)                           │   │
│  │  • Disponível: Apenas PJ                                            │   │
│  │  • Status: ✅ Ativo                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. ÁREA DE COBERTURA

### 9.1 Bairros Atendidos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ÁREA DE COBERTURA - CURITIBA/PR                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  BAIRRO            │ TAXA │ TEMPO      │ PEDIDO MÍN │ STATUS         │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  Alto Boqueirão    │ R$ 0 │ 30-60 min  │ -          │ ✅ Ativo       │ │
│  │  Boqueirão         │ R$ 0 │ 25-45 min  │ -          │ ✅ Ativo       │ │
│  │  Ganchinho         │ R$ 5 │ 40-70 min  │ R$ 100     │ ✅ Ativo       │ │
│  │  Hauer             │ R$ 0 │ 20-40 min  │ -          │ ✅ Ativo       │ │
│  │  Sítio Cercado     │ R$ 5 │ 35-60 min  │ R$ 80      │ ✅ Ativo       │ │
│  │  Umbará            │ R$ 8 │ 45-90 min  │ R$ 100     │ ✅ Ativo       │ │
│  │  Xaxim             │ R$ 0 │ 20-40 min  │ -          │ ✅ Ativo       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  LEGENDA:                                                                   │
│  • TAXA: Taxa de entrega adicional                                         │
│  • TEMPO: Previsão de entrega após confirmação                             │
│  • PEDIDO MÍN: Valor mínimo para entrega no bairro                         │
│                                                                             │
│  ⚠️  BAIRROS NÃO ATENDIDOS:                                                │
│  Centro, Água Verde, Batel, Bigorrilho, Portão, Santa Felicidade,          │
│  Pinheirinho, CIC, Tatuquara e demais não listados.                        │
│                                                                             │
│  💡 Clientes de bairros não atendidos podem usar opção RETIRA NA LOJA      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Mapa Visual

```
                    MAPA DE COBERTURA (Curitiba - Região Sul/Sudeste)
                    
                                        N
                                        │
                              ┌─────────┴─────────┐
                              │                   │
                              │      HAUER        │
                              │    ⏱️ 20-40min    │
                              │                   │
                    ┌─────────┴─────────┬─────────┴─────────┐
                    │                   │                   │
                    │      XAXIM        │    BOQUEIRÃO      │
                    │    ⏱️ 20-40min    │    ⏱️ 25-45min    │
                    │                   │                   │
          ┌─────────┴─────────┐         │         ┌────────┴────────┐
          │                   │         │         │                 │
          │  SÍTIO CERCADO    │         │         │ ALTO BOQUEIRÃO  │
          │   ⏱️ 35-60min     │         │         │  ⏱️ 30-60min    │
          │   💰 +R$5         │         │         │                 │
          │                   │         │         │                 │
          └─────────┬─────────┘         │         └────────┬────────┘
                    │                   │                   │
                    │         ┌─────────┴─────────┐         │
                    │         │                   │         │
                    │         │    GANCHINHO      │         │
                    │         │   ⏱️ 40-70min     │         │
                    │         │   💰 +R$5         │         │
                    │         │                   │         │
                    │         └─────────┬─────────┘         │
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        │
                              ┌─────────┴─────────┐
                              │                   │
                              │      UMBARÁ       │
                              │    ⏱️ 45-90min    │
                              │    💰 +R$8        │
                              │                   │
                              └───────────────────┘
                                        │
                                        S
                                        
          🏪 LOJA: Rua Principal, 1000 - Boqueirão (centro do mapa)
```

---

## 10. HORÁRIO DE FUNCIONAMENTO

### 10.1 Tabela de Horários

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HORÁRIO DE FUNCIONAMENTO                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  DIA           │ ATENDIMENTO   │ ENTREGAS      │ STATUS              │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  Segunda       │ 08:00 - 18:00 │ 08:30 - 17:30 │ 🟢 Aberto           │ │
│  │  Terça         │ 08:00 - 18:00 │ 08:30 - 17:30 │ 🟢 Aberto           │ │
│  │  Quarta        │ 08:00 - 18:00 │ 08:30 - 17:30 │ 🟢 Aberto           │ │
│  │  Quinta        │ 08:00 - 18:00 │ 08:30 - 17:30 │ 🟢 Aberto           │ │
│  │  Sexta         │ 08:00 - 18:00 │ 08:30 - 17:30 │ 🟢 Aberto           │ │
│  │  Sábado        │ 08:00 - 12:00 │ 08:30 - 11:30 │ 🟡 Meio período     │ │
│  │  Domingo       │ FECHADO       │ FECHADO       │ 🔴 Fechado          │ │
│  │  Feriados      │ FECHADO       │ FECHADO       │ 🔴 Fechado          │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  OBSERVAÇÕES:                                                               │
│                                                                             │
│  • Pedidos feitos após horário de entrega: processados no próximo dia útil │
│  • Última entrega do dia: 17:30 (seg-sex) ou 11:30 (sábado)               │
│  • Bot aceita pedidos 24h, mas informa previsão realista                   │
│  • Emergências: opção de falar com atendente de plantão                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Comportamento do Bot por Horário

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPORTAMENTO DO BOT POR HORÁRIO                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📍 DENTRO DO HORÁRIO (Seg-Sex 8h-18h, Sáb 8h-12h)                         │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                             │
│     Bot: "👋 Olá! Bem-vindo à Distribuidora de Gás!                        │
│           Estamos funcionando agora.                                       │
│           Como posso ajudar?"                                              │
│                                                                             │
│     → Fluxo normal de pedido                                               │
│     → Previsão de entrega: conforme tabela do bairro                       │
│                                                                             │
│  📍 FORA DO HORÁRIO (Noite/Domingo/Feriado)                                │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                             │
│     Bot: "👋 Olá! Bem-vindo à Distribuidora de Gás!                        │
│                                                                             │
│           ⏰ Nosso horário de funcionamento:                               │
│           Seg-Sex: 8h às 18h                                               │
│           Sábado: 8h às 12h                                                │
│                                                                             │
│           Você pode deixar seu pedido agora e processaremos               │
│           assim que abrirmos!"                                             │
│                                                                             │
│           [📝 Fazer pedido agora]                                          │
│           [🔔 Me avise quando abrir]                                       │
│                                                                             │
│     → Aceita pedido, mas informa previsão para próximo dia útil           │
│     → Pode notificar cliente quando abrir (opcional)                       │
│                                                                             │
│  📍 PRÓXIMO AO FECHAMENTO (última hora)                                    │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                             │
│     Bot: "⚠️ Atenção: Fechamos em [X] minutos!                             │
│                                                                             │
│           Seu pedido será entregue ainda hoje se confirmado               │
│           nos próximos [Y] minutos.                                        │
│                                                                             │
│           Caso contrário, será entregue amanhã às [hora]."                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*Continua em: `04_FLUXOS_USUARIO.md`*
# PARTE 4: FLUXOS DE USUÁRIO DETALHADOS

## 11. FLUXOS DE CONVERSA PRINCIPAIS

### 11.1 Cliente Novo - Primeira Compra (60-90 seg)

```
CLIENTE                                    BOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"oi"                                       
                                           [✓✓] [digitando...]
                                           
                                           "👋 Olá! Bem-vindo(a)!
                                           Você é:"
                                           [🧑 Pessoa Física]
                                           [🏢 Pessoa Jurídica]

*clica PF*                                 → IDENTIFY_TYPE
                                           "📝 Qual seu nome completo?"

"João da Silva"                            → IDENTIFY_NAME_PF
                                           "📋 Agora o CPF:"

"12345678900"                              → IDENTIFY_DOCUMENT_CPF
                                           "🛒 Qual produto?"
                                           [P13] [P20] [P45]

*seleciona P13*                            → ORDERING_PRODUCT
                                           "Quantos?"
                                           [1] [2] [3] [4] [5+]

*clica 2*                                  → ORDERING_QUANTITY
                                           "🔄 Você vai:"
                                           [Trocar] → R$220
                                           [Comprar novo] → R$420

*clica Trocar*                             → ORDERING_OPERATION
                                           "Adicionar mais?"
                                           [Sim] [Finalizar]

*clica Finalizar*                          → ORDERING_MORE_ITEMS
                                           "📍 Endereço de entrega?"

"Rua das Flores 123, Boqueirão"            → ORDERING_ADDRESS
                                           "📍 Confirma endereço?
                                           Rua das Flores, 123 - Boqueirão"
                                           [✅ Sim] [✏️ Corrigir]

*clica Sim*                                → ORDERING_ADDRESS_CONFIRM
                                           "Complemento/referência?"

"Casa branca"                              → ORDERING_COMPLEMENT
                                           "💰 Como pagar?"
                                           [Dinheiro] [Cartão] [PIX]

*clica Dinheiro*                           → CHECKOUT_PAYMENT
                                           "Troco para quanto?"
                                           [Não precisa] [R$250] [R$300]

*clica R$300*                              → CHECKOUT_CHANGE
                                           "📋 RESUMO:
                                           2x P13 = R$220
                                           Rua das Flores, 123
                                           Dinheiro (troco R$300)
                                           Confirma?"
                                           [✅ CONFIRMAR] [✏️ Alterar]

*clica CONFIRMAR*                          → CHECKOUT_SUMMARY
                                           "🎉 PEDIDO #1234 CONFIRMADO!
                                           ⏱️ 25-45 min"

                                           → COMPLETE_CONFIRMED
```

### 11.2 Cliente Conhecido - Repetir Pedido (15-30 seg)

```
CLIENTE                                    BOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"quero gas"                                
                                           "👋 Olá, João!
                                           Último pedido: 2x P13, R$220
                                           Deseja repetir?"
                                           [🔄 Repetir] [🛒 Novo]

*clica Repetir*                            → GREETING_RETURNING
                                           "💰 Mesmo pagamento?"
                                           [💵 Dinheiro] [📱 PIX]

*clica PIX*                                → CHECKOUT_PAYMENT
                                           "Confirma?
                                           2x P13 = R$220 via PIX"
                                           [✅ Confirmar]

*clica Confirmar*                          → CHECKOUT_SUMMARY
                                           "🎉 PEDIDO #1235 CONFIRMADO!
                                           PIX: (41) 99999-9999"

                                           → COMPLETE_CONFIRMED

⏱️ TEMPO: ~15 segundos!
```

### 11.3 Fast-Track (10-15 seg)

```
CLIENTE                                    BOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"quero 2 P13 troca,                        
Rua das Flores 123,                        
pago cartão"
                                           "👋 Olá, João!
                                           
                                           📋 Entendi seu pedido:
                                           🛒 2x P13 (troca) = R$220
                                           📍 Rua das Flores, 123
                                           💳 Cartão
                                           
                                           Confirma?"
                                           [✅ Confirmar] [✏️ Alterar]

*clica Confirmar*                          → CHECKOUT_SUMMARY (direto!)
                                           "🎉 PEDIDO #1236 CONFIRMADO!"

⏱️ TEMPO: ~10 segundos! 🚀
```

### 11.4 FAQ Inline (Pergunta Durante Pedido)

```
CLIENTE                                    BOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(No meio do pedido, ORDERING_PRODUCT)

"vocês entregam no pinheirinho?"           
                                           "📍 Sobre área de entrega:
                                           
                                           Infelizmente o Pinheirinho
                                           não está na nossa área 😔
                                           
                                           Entregamos em:
                                           • Boqueirão, Hauer, Xaxim...
                                           
                                           ─────────────────────
                                           
                                           Voltando ao seu pedido...
                                           🛒 Qual produto?"
                                           [P13] [P20] [P45]

                                           → Retorna para ORDERING_PRODUCT
```

### 11.5 Rastrear Pedido

```
CLIENTE                                    BOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"cadê meu pedido"                          
                                           "📦 PEDIDO #1234
                                           
                                           ✅ Recebido - 14:30
                                           ✅ Preparando - 14:35
                                           ✅ Saiu - 14:50
                                           🔄 A caminho...
                                           
                                           🛵 Entregador: Carlos
                                           ⏱️ ~10 min"
                                           
                                           [🔄 Atualizar]
                                           [📞 Ligar entregador]
                                           [❓ Problema]
```

---

## 12. TRATAMENTO DE ERROS

### 12.1 Mensagem Não Compreendida

```
Bot: "Hmm, não entendi 🤔

     Você pode escolher da lista ou digitar:
     • P13, P20 ou P45"
     
     [📋 Ver opções] [📞 Atendente]
```

### 12.2 CPF Inválido

```
Bot: "❌ CPF inválido

     Verifique e digite novamente.
     💡 Pode ser só os números."
```

### 12.3 Bairro Fora da Área

```
Bot: "📍 Infelizmente não entregamos
     no {bairro} ainda 😔
     
     💡 Você pode retirar na loja:
     Rua Principal, 1000 - Boqueirão"
     
     [🏪 Retirar na loja] [📍 Outro endereço]
```

---

*Continua em: `05_NLU_E_CONTEXTO.md`*
# PARTE 5: ENGINE NLU E SISTEMA DE CONTEXTO

## 13. ENGINE DE LINGUAGEM NATURAL (NLU)

### 13.1 Arquitetura Híbrida

O NLU do GasMaster 2.0 usa uma abordagem **híbrida em 3 níveis**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PIPELINE NLU HÍBRIDO                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   MENSAGEM ──▶ KEYWORD (10ms) ──▶ PATTERN (20ms) ──▶ LLM (300ms)           │
│                    │                   │                   │                │
│                    │ 95%+ conf         │ 85%+ conf         │ fallback       │
│                    ▼                   ▼                   ▼                │
│               RETORNA             RETORNA              RETORNA              │
│                                                                             │
│   + ENTITY EXTRACTOR (executa sempre em paralelo)                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.2 Mapeamento de Keywords (Exemplos)

| Intenção | Keywords |
|----------|----------|
| GREETING | oi, olá, bom dia, boa tarde, eae |
| MAKE_ORDER | quero, preciso, pedir, comprar, gas |
| REPEAT_ORDER | mesmo, repetir, de novo, igual |
| TRACK_ORDER | rastrear, cadê, status, meu pedido |
| CONFIRM | sim, ok, certo, confirmo, beleza |
| DENY | não, errado, negativo |
| TALK_TO_HUMAN | atendente, humano, pessoa |

### 13.3 Patterns para Reconhecimento

| Tipo | Pattern Exemplo | Extração |
|------|-----------------|----------|
| Produto | `\d+ p13\|p20\|p45` | quantity, product |
| CPF | `\d{3}\.?\d{3}\.?\d{3}-?\d{2}` | cpf |
| CNPJ | `\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}` | cnpj |
| Endereço | `rua .+ \d+` | street, number |
| Pagamento | `dinheiro\|cartão\|pix` | payment_method |

---

## 14. SISTEMA DE CONTEXTO

### 14.1 Três Camadas

```
┌──────────────────────────────────────────────────────────────────┐
│  CUSTOMER CONTEXT (Persistente)                                  │
│  "QUEM É" - name, phone, document, addresses, last_order, etc   │
│  Storage: Redis → PostgreSQL → Firebird                          │
├──────────────────────────────────────────────────────────────────┤
│  CONVERSATION CONTEXT (Sessão - 30min)                           │
│  "ONDE ESTÁ" - current_state, collected_data, history            │
│  Storage: Redis                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ORDER CONTEXT (Pedido - 2h)                                     │
│  "O QUE QUER" - items, total, address, payment                   │
│  Storage: Redis                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 14.2 Fluxo de Carregamento

1. Redis: `GET customer:{phone}` → cache
2. Se não: PostgreSQL → carrega e cacheia
3. Se não: Firebird → migra para PostgreSQL
4. Se não: Cliente novo

### 14.3 Detecção de Pedido Abandonado

- Última interação > 2 horas
- Estado era ordering/checkout
- Dados ainda válidos (estoque OK)
- → Oferece continuar de onde parou

---

*Continua em: `06_HANDLERS_E_APIS.md`*
# PARTE 6: HANDLERS, APIS E IMPLEMENTAÇÃO

## 15. ESTRUTURA DOS HANDLERS

### 15.1 Base Handler

```python
class BaseStateHandler(ABC):
    @abstractmethod
    async def handle(self, message, intent, context) -> HandlerResult:
        pass

@dataclass
class HandlerResult:
    next_state: ConversationState
    responses: List[Response]
    context_updates: Dict[str, Any]
```

### 15.2 Registry de Handlers

```python
HANDLER_REGISTRY = {
    # GREETING (2)
    GREETING_INITIAL: GreetingInitialHandler(),
    GREETING_RETURNING: GreetingReturningHandler(),
    
    # IDENTIFY (5)
    IDENTIFY_TYPE: IdentifyTypeHandler(),
    IDENTIFY_NAME_PF: IdentifyNamePFHandler(),
    IDENTIFY_NAME_PJ: IdentifyNamePJHandler(),
    IDENTIFY_DOCUMENT_CPF: IdentifyCPFHandler(),
    IDENTIFY_DOCUMENT_CNPJ: IdentifyCNPJHandler(),
    
    # ORDERING (8)
    ORDERING_PRODUCT: OrderingProductHandler(),
    ORDERING_QUANTITY: OrderingQuantityHandler(),
    ORDERING_OPERATION: OrderingOperationHandler(),
    ORDERING_MORE_ITEMS: OrderingMoreItemsHandler(),
    ORDERING_ADDRESS: OrderingAddressHandler(),
    ORDERING_ADDRESS_CONFIRM: OrderingAddressConfirmHandler(),
    ORDERING_COMPLEMENT: OrderingComplementHandler(),
    ORDERING_CONFIRM_REPEAT: OrderingConfirmRepeatHandler(),
    
    # CHECKOUT (3)
    CHECKOUT_PAYMENT: CheckoutPaymentHandler(),
    CHECKOUT_CHANGE: CheckoutChangeHandler(),
    CHECKOUT_SUMMARY: CheckoutSummaryHandler(),
    
    # COMPLETE (2)
    COMPLETE_CONFIRMED: CompleteConfirmedHandler(),
    COMPLETE_FOLLOWUP: CompleteFollowupHandler(),
    
    # SUPPORT (5)
    SUPPORT_HUMAN: SupportHumanHandler(),
    SUPPORT_FAQ: SupportFAQHandler(),
    TRACKING_STATUS: TrackingStatusHandler(),
    TRACKING_OPTIONS: TrackingOptionsHandler(),
    ERROR_RECOVERY: ErrorRecoveryHandler(),
}
```

---

## 16. TEMPLATES DE MENSAGENS

```python
TEMPLATES = {
    "greeting_new": "👋 Olá! Bem-vindo(a)! Você é:",
    
    "greeting_returning": "👋 Olá, {name}! Último pedido: {summary}. Repetir?",
    
    "order_summary": """📋 RESUMO
═══════════════════
👤 {name}
📍 {address}
🛒 {items}
💰 Total: R$ {total}
⏱️ {estimate}
═══════════════════""",
    
    "order_confirmed": """🎉 PEDIDO #{number} CONFIRMADO!
⏱️ Previsão: {estimate}
Obrigado! 🔥""",
}
```

---

## 17. INTEGRAÇÕES

### 17.1 WAHA (WhatsApp)

| Método | Descrição |
|--------|-----------|
| `send_text()` | Envia texto |
| `send_buttons()` | Envia com botões (máx 3) |
| `send_list()` | Envia lista (máx 10) |
| `mark_as_read()` | ✓✓ azul |
| `start_typing()` | Indica digitação |
| `stop_typing()` | Para digitação |

### 17.2 Firebird (Legado)

| Método | Descrição |
|--------|-----------|
| `search_customer_by_phone()` | Busca cliente |
| `get_customer_orders()` | Histórico |
| `sync_order()` | Sincroniza pedido |

---

## 18. MÉTRICAS

### 18.1 Prometheus

```python
# Contadores
flow_state_transitions_total     # Transições de estado
orders_created_total             # Pedidos criados
abandoned_orders_total           # Pedidos abandonados

# Histogramas  
order_completion_seconds         # Tempo para completar
nlu_processing_seconds          # Tempo de NLU

# Gauges
active_conversations            # Conversas ativas
```

### 18.2 KPIs a Monitorar

| Métrica | Meta |
|---------|------|
| Taxa de conclusão | > 85% |
| Tempo médio (novo) | < 90s |
| Tempo médio (conhecido) | < 30s |
| Taxa abandono | < 15% |

---

*Continua em: `07_MIGRACAO_E_CRONOGRAMA.md`*
# PARTE 7: MIGRAÇÃO, MÉTRICAS E CRONOGRAMA

## 19. PLANO DE MIGRAÇÃO

### 19.1 Estratégia: Migração Gradual com Feature Flag

```
FASE 1 (Semana 8, dias 1-2): 10% do tráfego no v2.0
FASE 2 (Semana 8, dias 3-4): 25% do tráfego
FASE 3 (Semana 8, dias 5-6): 50% do tráfego
FASE 4 (Semana 8, dia 7):    100% do tráfego
```

### 19.2 Critérios de Rollback Automático

- Taxa de erro > 5%
- Tempo de resposta > 3s (p95)
- Taxa de conversão < 30%

---

## 20. CRONOGRAMA (8 SEMANAS)

| Semana | Foco | Entregáveis |
|--------|------|-------------|
| **1-2** | Fundação | Estados, Contexto, BaseHandler |
| **3-4** | NLU + Handlers Core | Keyword/Pattern matcher, GREETING, IDENTIFY, ORDERING |
| **5-6** | Checkout + Features | CHECKOUT, COMPLETE, SUPPORT, Abandono, FAQ |
| **7** | Testes | Unit, E2E, Carga, Integração |
| **8** | Deploy | Feature flag, Migração gradual, Go-live |

---

## 21. CHECKLIST FINAL

### Arquitetura
- [ ] 25 estados em ConversationState
- [ ] 3 camadas de contexto
- [ ] Handler registry completo

### NLU  
- [ ] KeywordMatcher
- [ ] PatternRecognizer
- [ ] EntityExtractor
- [ ] LLM fallback

### Features Especiais
- [ ] Fast-track
- [ ] Repetir pedido
- [ ] Pedido abandonado
- [ ] FAQ inline
- [ ] Preferências aprendidas

### Integrações
- [ ] Firebird (busca cliente)
- [ ] Migração contexto v1→v2
- [ ] Métricas Prometheus

---

## 22. MÉTRICAS DE SUCESSO

| Métrica | Atual | Meta | 
|---------|-------|------|
| Taxa conclusão | 40% | >85% |
| Tempo (novo) | 3-5min | <90s |
| Tempo (conhecido) | 2-3min | <30s |
| Abandono | 60% | <15% |

---

**Documento:** GasMaster Flow Engine 2.0  
**Data:** 13/02/2026  
**Autor:** Fabiano Lopes
