# GASMASTER - Fluxo Conversacional Completo

## 1. VISÃO GERAL DO FLUXO

### 1.1 Princípios Fundamentais

- **Detecção de intenção** em vez de navegação por menu rígido
- **Extração de entidades inline** - capturar produto, quantidade, endereço na mesma mensagem
- **Atalhos inteligentes** - cliente pode pular etapas se fornecer dados completos
- **Tolerância a erros** - normalização de texto e dicionário de sinônimos
- **Recuperação graciosa** - nunca travar, sempre oferecer alternativas
- **Confirmação única no final** - evitar múltiplas confirmações intermediárias

### 1.2 Hierarquia de Intenções

| Prioridade | Intenção | Gatilhos |
|------------|----------|----------|
| 1 (Máxima) | EMERGÊNCIA | vazamento, cheiro de gás, perigo, fogo |
| 2 | COMPRAR | quero gás, preciso, acabou, manda, pedir |
| 3 | RASTREAR | cadê, onde está, status, meu pedido |
| 4 | ATENDENTE | falar com alguém, humano, atendente |
| 5 | INFORMAÇÃO | preço, quanto custa, horário, entregam |
| 6 | SAUDAÇÃO | oi, olá, bom dia, tudo bem |
| 7 | CANCELAR | cancelar, desistir, não quero mais |
| 8 | CONFIRMAR | sim, correto, confirma, beleza (contextual) |
| 9 | NEGAR | não, errado, outro, alterar (contextual) |

---

## 2. FLUXO DE IDENTIFICAÇÃO DO CLIENTE

```
┌─────────────────────────────────────────────────────────────────┐
│                    MENSAGEM RECEBIDA                            │
│                         │                                       │
│                         ▼                                       │
│            ┌────────────────────────┐                          │
│            │  Extrair TELEFONE      │                          │
│            │  do payload WAHA       │                          │
│            └───────────┬────────────┘                          │
│                        │                                       │
│                        ▼                                       │
│         ┌──────────────────────────────┐                       │
│         │ Buscar telefone no PostgreSQL │                       │
│         └──────────────┬───────────────┘                       │
│                        │                                       │
│          ┌─────────────┴─────────────┐                         │
│          │                           │                         │
│          ▼                           ▼                         │
│   ┌─────────────┐           ┌─────────────────┐               │
│   │ ENCONTROU   │           │ NÃO ENCONTROU   │               │
│   │ Cliente     │           │                 │               │
│   │ conhecido   │           └────────┬────────┘               │
│   └──────┬──────┘                    │                         │
│          │                           ▼                         │
│          │              ┌─────────────────────────┐            │
│          │              │ Buscar telefone         │            │
│          │              │ no FIREBIRD (ERP)       │            │
│          │              └───────────┬─────────────┘            │
│          │                          │                          │
│          │           ┌──────────────┴──────────────┐          │
│          │           │                             │          │
│          │           ▼                             ▼          │
│          │    ┌─────────────┐            ┌─────────────┐      │
│          │    │ ENCONTROU   │            │ NÃO ENCONTROU│      │
│          │    │ no Firebird │            │ CLIENTE NOVO │      │
│          │    └──────┬──────┘            └──────┬──────┘      │
│          │           │                          │             │
│          │           ▼                          ▼             │
│          │    ┌─────────────────┐      ┌─────────────────┐   │
│          │    │ Sincronizar     │      │ Criar cliente   │   │
│          │    │ dados p/ PG     │      │ só com telefone │   │
│          │    │ (nome,end,cpf)  │      │                 │   │
│          │    └────────┬────────┘      └────────┬────────┘   │
│          │             │                        │            │
│          └─────────────┴────────────────────────┘            │
│                        │                                      │
│                        ▼                                      │
│         ┌──────────────────────────────┐                     │
│         │  CLIENTE IDENTIFICADO        │                     │
│         │  - customer_id               │                     │
│         │  - is_new (bool)             │                     │
│         │  - has_complete_data (bool)  │                     │
│         └──────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Campos do Cliente

| Campo | Obrigatório | Quando Coletar |
|-------|-------------|----------------|
| phone | Automático | Extraído do WhatsApp (identificador primário) |
| name | Na finalização | Pedir apenas se não vier do Firebird e na hora de finalizar |
| cpf_cnpj | Na finalização | Pedir apenas para nota fiscal, no momento da confirmação |
| address | Na finalização | Pedir se não tem cadastrado ou se cliente quer alterar |
| default_product | Opcional | Salvar automaticamente após primeiro pedido completo |
| default_quantity | Opcional | Salvar automaticamente após primeiro pedido completo |
| default_payment | Opcional | Salvar automaticamente após primeiro pedido completo |

---

## 3. CENÁRIOS DE CONVERSA

### 3.1 Cenário: Cliente Novo - Fluxo Completo

```
CLIENTE: oi, quero gás

ROBÔ: Olá! 👋 Bem-vindo à GasMaster!

Qual botijão você precisa?

🔹 P13 (13kg) - R$ 115,00 - Residencial
🔹 P20 (20kg) - R$ 180,00 - Empilhadeira  
🔹 P45 (45kg) - R$ 350,00 - Comercial

[P13 - R$115] [P20 - R$180] [P45 - R$350]
```

```
CLIENTE: quero 2 do pequeno

→ Detecção: Produto=P13 ("pequeno"), Quantidade=2

ROBÔ: 2x P13 - R$ 230,00 ✅

Qual o endereço de entrega?
(Ex: Rua das Flores, 123 - Boqueirão)
```

```
CLIENTE: rua das flores 123 boqueirão

→ Detecção: Endereço válido, Bairro=Boqueirão (suportado)

ROBÔ: Endereço: Rua das Flores, 123 - Boqueirão ✅

Como prefere pagar?
[💵 Dinheiro] [💳 Cartão]
```

```
CLIENTE: dinheiro, troco pra 300

→ Detecção: Pagamento=DINHEIRO, Troco=R$300

ROBÔ: Para emitir a nota fiscal, preciso do seu CPF ou CNPJ:
```

```
CLIENTE: 123.456.789-00

ROBÔ: E qual seu nome completo?
```

```
CLIENTE: João da Silva

ROBÔ: 📋 Resumo do Pedido

• 2x P13 (13kg) — R$ 230,00
• Entrega: Rua das Flores, 123 - Boqueirão
• Pagamento: Dinheiro (troco p/ R$ 300)
• CPF: ***.456.789-**

Tudo certo?
[✅ Confirmar] [✏️ Alterar] [❌ Cancelar]
```

```
CLIENTE: confirma

ROBÔ: ✅ Pedido #1234 confirmado!

Previsão de entrega: 30-45 minutos
Acompanhe pelo WhatsApp ou digite "status"

Obrigado, João! 🙏
```

---

### 3.2 Cenário: Cliente Recorrente - Atalho Rápido

```
CLIENTE: oi

→ Detecção: Cliente conhecido (João), último pedido: 2x P13

ROBÔ: Oi João! 👋 

Quer o de sempre? 2x P13 no endereço Rua das Flores, 123?

[🔥 Sim, o de sempre] [📦 Outro pedido] [💬 Falar com alguém]
```

```
CLIENTE: isso, o de sempre

→ Detecção: CONFIRMAR + contexto "de sempre"

ROBÔ: 📋 Pedido Rápido

• 2x P13 (13kg) — R$ 230,00
• Entrega: Rua das Flores, 123 - Boqueirão
• Pagamento: Dinheiro

Confirma?
[✅ Confirmar] [✏️ Alterar]
```

```
CLIENTE: confirma

ROBÔ: ✅ Pedido #1235 confirmado!
Previsão: 30-45 minutos

Valeu, João! 🙏
```

---

### 3.3 Cenário: Pedido Completo em Uma Mensagem

```
CLIENTE: manda 2 p13 pra rua das flores 123 boqueirão, pago dinheiro

→ Detecção múltipla:
  - Intenção: COMPRAR
  - Produto: P13
  - Quantidade: 2
  - Endereço: Rua das Flores, 123 - Boqueirão
  - Pagamento: DINHEIRO

ROBÔ: 📋 Entendi! Seu pedido:

• 2x P13 (13kg) — R$ 230,00
• Entrega: Rua das Flores, 123 - Boqueirão
• Pagamento: Dinheiro

Confirma?
[✅ Confirmar] [✏️ Alterar]
```

---

### 3.4 Cenário: Cliente Não Entendido - Recuperação

```
CLIENTE: qero gas

→ Detecção: Intenção COMPRAR (mesmo com erro "qero")

ROBÔ: Qual botijão você precisa?

🔹 P13 (13kg) - R$ 115,00
🔹 P20 (20kg) - R$ 180,00  
🔹 P45 (45kg) - R$ 350,00

[P13] [P20] [P45]
```

```
CLIENTE: asdfgh

→ Detecção: NENHUMA (texto sem sentido)
→ retry_count = 1

ROBÔ: Não consegui entender. Você quer:

[🛒 Comprar gás] [📦 Ver meu pedido] [💬 Falar com atendente]
```

```
CLIENTE: xyzabc

→ Detecção: NENHUMA
→ retry_count = 2

ROBÔ: Hmm, ainda não entendi. Vou te conectar com um atendente, ok?

Um momento... 🙏

[Transfere para atendente humano]
```

---

### 3.5 Cenário: Alteração de Pedido

```
[Após confirmação mostrada]

CLIENTE: alterar

ROBÔ: O que você quer alterar?

[📦 Produto] [🔢 Quantidade] [📍 Endereço] [💳 Pagamento]
```

```
CLIENTE: quantidade

ROBÔ: Quantos botijões P13 você quer?

[1] [2] [3] [Outro]
```

```
CLIENTE: 3

ROBÔ: 📋 Pedido atualizado:

• 3x P13 (13kg) — R$ 345,00
• Entrega: Rua das Flores, 123 - Boqueirão
• Pagamento: Dinheiro

Confirma agora?
[✅ Confirmar] [✏️ Alterar mais]
```

---

### 3.6 Cenário: Rastreamento

```
CLIENTE: cadê meu pedido

→ Detecção: Intenção RASTREAR

ROBÔ: 📦 Seu pedido #1234:

Status: 🚚 Saiu para entrega
Previsão: ~15 minutos

Entregador: Carlos
Veículo: Moto branca

[📞 Ligar p/ entregador] [❌ Cancelar pedido]
```

---

### 3.7 Cenário: Bairro Não Atendido

```
CLIENTE: rua abc 123 centro

→ Detecção: Bairro "centro" não está em supported_bairros

ROBÔ: Poxa, ainda não entregamos no Centro 😕

Atendemos: Alto Boqueirão, Boqueirão, Ganchinho, Hauer, Sítio Cercado, Umbarã, Xaxim

Tem outro endereço nessas regiões?

[💬 Falar com atendente]
```

---

## 4. LÓGICA DE DETECÇÃO

### 4.1 Função normalize_text()

```python
def normalize_text(text: str) -> str:
    """
    Normaliza texto para detecção de intenções e entidades.
    """
    # 1. Lowercase
    text = text.lower()
    
    # 2. Remove acentos
    text = unidecode(text)  # "você" -> "voce"
    
    # 3. Remove pontuação exceto números
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # 4. Remove espaços extras
    text = ' '.join(text.split())
    
    # 5. Expande abreviações comuns
    expansions = {
        'vc': 'voce', 'vcs': 'voces',
        'tb': 'tambem', 'tbm': 'tambem',
        'pq': 'porque', 'pqe': 'porque',
        'oq': 'o que', 'qd': 'quando',
        'qdo': 'quando', 'hj': 'hoje',
        'mt': 'muito', 'mto': 'muito',
        'blz': 'beleza', 'flw': 'falou',
        'vlw': 'valeu', 'kd': 'cade',
        'n': 'nao', 'eh': 'e',
        'ta': 'esta', 'to': 'estou',
        'pf': 'por favor', 'pfv': 'por favor',
        'obg': 'obrigado', 'dnd': 'de nada',
        'dnv': 'de novo', 'agr': 'agora',
        'dps': 'depois', 'msm': 'mesmo',
        'cmg': 'comigo', 'ctg': 'contigo',
        'qq': 'qualquer', 'qm': 'quem',
    }
    
    for abbrev, full in expansions.items():
        text = re.sub(rf'\b{abbrev}\b', full, text)
    
    return text
```

### 4.2 Função detect_intention()

```python
def detect_intention(text: str, context: ConversationContext) -> Intention:
    """
    Detecta a intenção principal da mensagem.
    Retorna a intenção de maior prioridade encontrada.
    """
    normalized = normalize_text(text)
    
    # EMERGÊNCIA (prioridade máxima)
    emergency_keywords = ['vazamento', 'vazando', 'cheiro de gas', 
                          'fogo', 'perigo', 'emergencia']
    if any(kw in normalized for kw in emergency_keywords):
        return Intention.EMERGENCY
    
    # COMPRAR
    buy_keywords = ['quero gas', 'preciso de gas', 'quero comprar',
                    'manda gas', 'pedir gas', 'fazer pedido',
                    'quero um', 'quero botijao', 'sem gas',
                    'acabou o gas', 'gas acabou', 'to sem gas']
    product_codes = ['p13', 'p20', 'p45', '13kg', '20kg', '45kg']
    
    if any(kw in normalized for kw in buy_keywords):
        return Intention.BUY
    if any(code in normalized for code in product_codes):
        return Intention.BUY
    
    # RASTREAR
    track_keywords = ['cade', 'onde esta', 'status', 'meu pedido',
                      'ja saiu', 'demora', 'previsao', 'rastrear']
    if any(kw in normalized for kw in track_keywords):
        return Intention.TRACK
    
    # ATENDENTE
    human_keywords = ['atendente', 'humano', 'pessoa', 'falar com',
                      'atendimento', 'suporte', 'reclamacao']
    if any(kw in normalized for kw in human_keywords):
        return Intention.HUMAN
    
    # CANCELAR
    cancel_keywords = ['cancelar', 'cancela', 'desistir', 'desisto',
                       'nao quero mais', 'deixa pra la']
    if any(kw in normalized for kw in cancel_keywords):
        return Intention.CANCEL
    
    # CONFIRMAR (contextual - só se robô perguntou algo)
    if context.awaiting_confirmation:
        confirm_keywords = ['sim', 'ss', 'confirma', 'confirmo', 
                           'correto', 'certo', 'isso', 'pode',
                           'beleza', 'blz', 'ok', 'fechado']
        if any(kw in normalized for kw in confirm_keywords):
            return Intention.CONFIRM
    
    # NEGAR (contextual)
    if context.awaiting_confirmation:
        deny_keywords = ['nao', 'errado', 'incorreto', 'outro',
                        'alterar', 'trocar', 'mudar']
        if any(kw in normalized for kw in deny_keywords):
            return Intention.DENY
    
    # SAUDAÇÃO
    greeting_keywords = ['oi', 'ola', 'bom dia', 'boa tarde', 
                        'boa noite', 'eai', 'fala', 'salve']
    if any(kw in normalized for kw in greeting_keywords):
        return Intention.GREETING
    
    # Não identificado
    return Intention.UNKNOWN
```

### 4.3 Função extract_entities()

```python
def extract_entities(text: str) -> dict:
    """
    Extrai todas as entidades possíveis de uma mensagem.
    """
    normalized = normalize_text(text)
    entities = {}
    
    # PRODUTO
    product_map = {
        'P13': ['p13', 'p 13', '13kg', '13 kg', 'treze', 'de 13',
                'pequeno', 'residencial', 'normal', 'comum', 'caseiro',
                'opcao 1', 'opção 1', 'primeiro'],
        'P20': ['p20', 'p 20', '20kg', '20 kg', 'vinte', 'de 20',
                'medio', 'empilhadeira', 'opcao 2', 'opção 2', 'segundo'],
        'P45': ['p45', 'p 45', '45kg', '45 kg', 'quarenta e cinco', 'de 45',
                'grande', 'grandao', 'industrial', 'comercial',
                'opcao 3', 'opção 3', 'terceiro']
    }
    
    for product, keywords in product_map.items():
        if any(kw in normalized for kw in keywords):
            entities['product'] = product
            break
    
    # QUANTIDADE
    quantity_map = {
        1: ['1', 'um', 'uma', 'so um', 'apenas um'],
        2: ['2', 'dois', 'duas', 'par'],
        3: ['3', 'tres', 'três', 'trio'],
        4: ['4', 'quatro'],
        5: ['5', 'cinco'],
        6: ['6', 'seis', 'meia duzia'],
    }
    
    for qty, keywords in quantity_map.items():
        if any(kw in normalized for kw in keywords):
            entities['quantity'] = qty
            break
    
    # Se não encontrou quantidade específica, procura número genérico
    if 'quantity' not in entities:
        numbers = re.findall(r'\b(\d{1,2})\b', normalized)
        if numbers:
            qty = int(numbers[0])
            if 1 <= qty <= 10:
                entities['quantity'] = qty
    
    # PAGAMENTO
    payment_map = {
        'cash': ['dinheiro', 'din', 'cash', 'especie', 'na mao', 'em maos'],
        'credit_card': ['cartao', 'credito', 'maquininha', 'visa', 'master'],
        'debit_card': ['debito'],
        'pix': ['pix', 'qr code']
    }
    
    for payment, keywords in payment_map.items():
        if any(kw in normalized for kw in keywords):
            entities['payment'] = payment
            break
    
    # TROCO
    change_match = re.search(r'troco\s*(?:pra|para|de)?\s*(\d+)', normalized)
    if change_match:
        entities['change_for'] = int(change_match.group(1))
    
    # ENDEREÇO (básico - extrai texto após padrões)
    address_patterns = [
        r'(?:rua|av|avenida|travessa)\s+[\w\s]+\d+',
        r'(?:entrega|entregar|endereco)\s*:?\s*(.+)',
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, normalized)
        if match:
            entities['address_raw'] = match.group(0)
            break
    
    # BAIRRO
    supported_bairros = ['alto boqueirão', 'boqueirão', 'ganchinho', 
                         'hauer', 'sítio cercado', 'umbarã', 'xaxim']
    bairros_normalized = [unidecode(b.lower()) for b in supported_bairros]
    
    for i, bairro in enumerate(bairros_normalized):
        if bairro in normalized:
            entities['bairro'] = supported_bairros[i]
            break
    
    return entities
```

---

## 5. ESTRUTURA DE CONTEXTO (Redis)

```python
@dataclass
class ConversationContext:
    # Identificação
    phone: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    is_new_customer: bool = True
    
    # Estado
    state: str = "START"
    retry_count: int = 0
    last_message_at: datetime = None
    
    # Pedido em andamento
    order_id: Optional[str] = None
    selected_product: Optional[str] = None
    selected_quantity: int = 1
    address: Optional[dict] = None
    address_confirmed: bool = False
    payment_method: Optional[str] = None
    change_for: Optional[int] = None
    
    # Flags de contexto
    awaiting_confirmation: bool = False
    awaiting_input_type: Optional[str] = None  # 'product', 'quantity', 'address', 'payment', 'cpf', 'name'
    
    # Entidades pendentes (extraídas mas não confirmadas)
    pending_entities: dict = field(default_factory=dict)
    
    # Histórico curto (últimas 3 mensagens)
    recent_messages: list = field(default_factory=list)
```

---

## 6. MÁQUINA DE ESTADOS SIMPLIFICADA

```
                    ┌─────────────────────────────────────┐
                    │              START                  │
                    │  - Identifica cliente               │
                    │  - Detecta intenção                 │
                    └─────────────────┬───────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
            ▼                         ▼                         ▼
    ┌───────────────┐       ┌───────────────┐        ┌───────────────┐
    │ COLLECTING    │       │  TRACKING     │        │    HUMAN      │
    │ ORDER_DATA    │       │  - Busca      │        │    SUPPORT    │
    │               │       │    pedidos    │        │               │
    │ Coleta:       │       │  - Mostra     │        │ - WebSocket   │
    │ - Produto     │       │    status     │        │ - Operador    │
    │ - Quantidade  │       │               │        │               │
    │ - Endereço    │       └───────────────┘        └───────────────┘
    │ - Pagamento   │
    │ - CPF/Nome    │
    └───────┬───────┘
            │
            │ (dados completos)
            ▼
    ┌───────────────┐
    │  CONFIRMING   │
    │  ORDER        │
    │               │
    │ - Resumo      │
    │ - Confirma?   │
    └───────┬───────┘
            │
      ┌─────┴─────┐
      │           │
      ▼           ▼
┌───────────┐ ┌───────────┐
│ CONFIRMED │ │  EDITING  │
│           │ │           │
│ - Cria    │ │ - Altera  │
│   pedido  │ │   campo   │
│ - Emite   │ │ - Volta   │
│   WS      │ │   p/      │
│           │ │   confirm │
└───────────┘ └───────────┘
```

---

## 7. TRATAMENTO DE ERROS

### 7.1 Níveis de Recuperação

| Nível | retry_count | Ação |
|-------|-------------|------|
| 1 | 0-1 | Reformula pergunta com contexto |
| 2 | 2 | Oferece botões/opções claras |
| 3 | 3+ | Transfere para atendente humano |

### 7.2 Mensagens de Erro

```python
ERROR_MESSAGES = {
    'product_not_found': "Não encontrei esse produto. Temos P13 (13kg), P20 (20kg) e P45 (45kg). Qual você quer?",
    
    'quantity_invalid': "Preciso de um número entre 1 e 10. Quantos botijões você quer?",
    
    'address_incomplete': "Preciso do endereço completo com número e bairro. Ex: Rua das Flores, 123 - Boqueirão",
    
    'bairro_not_supported': "Poxa, ainda não entregamos nessa região 😕\n\nAtendemos: {bairros}\n\nTem outro endereço?",
    
    'payment_invalid': "Aceitamos dinheiro ou cartão. Como prefere pagar?",
    
    'cpf_invalid': "CPF/CNPJ inválido. Por favor, digite apenas os números.",
    
    'generic_not_understood': "Não consegui entender. Você quer:\n[🛒 Comprar gás] [📦 Ver pedido] [💬 Atendente]",
    
    'transfer_to_human': "Vou te conectar com um atendente. Um momento... 🙏"
}
```
