# PROMPT PARA CLINE - REFORMULAÇÃO DO ROBÔ WHATSAPP GASMASTER

## CONTEXTO DO PROJETO

Você está trabalhando no sistema de automação WhatsApp da GasMaster, uma distribuidora de gás. O sistema atual usa um fluxo rígido de menus (aperte 1, 2, 3) que frustra os clientes. Sua missão é transformar o robô em um assistente conversacional inteligente.

## ARQUIVOS DO PROJETO

Estrutura principal:
```
backend/
├── app/
│   ├── api/
│   │   └── webhooks.py          # Recebe mensagens do WhatsApp via WAHA
│   ├── core/
│   │   ├── flow_engine.py       # Orquestra o fluxo, comandos globais
│   │   ├── handlers.py          # Lógica de resposta por estado
│   │   └── state_machine.py     # Estados e transições
│   ├── integrations/
│   │   ├── waha.py              # Cliente WAHA (envio de mensagens)
│   │   └── firebird_client.py   # Integração com ERP Firebird
│   ├── models/
│   │   ├── customer.py          # Modelo Customer (PostgreSQL)
│   │   ├── order.py             # Modelo Order
│   │   └── product.py           # Modelo Product
│   ├── schemas/
│   │   └── webhook.py           # WAHAMessage (phone, text, button_id)
│   └── config.py                # Configurações (bairros, TTL Redis, etc)
```

## OBJETIVO DA REFORMULAÇÃO

Transformar o robô de menu rígido em assistente conversacional que:

1. **Detecta intenção** em vez de depender de menus numéricos
2. **Extrai múltiplas entidades** de uma única mensagem (produto, quantidade, endereço, pagamento)
3. **Tolera erros de digitação** usando normalização e dicionário de sinônimos
4. **Oferece atalhos** para clientes recorrentes ("o de sempre")
5. **Recupera graciosamente** de erros em vez de travar
6. **Confirma uma única vez** no final, não em cada etapa

---

## TAREFAS ESPECÍFICAS

### TAREFA 1: Criar módulo de normalização e detecção

Criar arquivo `backend/app/core/nlp_utils.py` com:

```python
# Funções a implementar:

def normalize_text(text: str) -> str:
    """
    Normaliza texto para detecção:
    1. Lowercase
    2. Remove acentos (unidecode)
    3. Remove pontuação
    4. Expande abreviações (vc->voce, tb->tambem, blz->beleza, etc)
    5. Remove espaços extras
    """
    pass

def detect_intention(text: str, context) -> str:
    """
    Detecta intenção principal:
    - EMERGENCY: vazamento, cheiro de gás, perigo
    - BUY: quero gás, preciso, manda, acabou
    - TRACK: cadê, status, meu pedido
    - HUMAN: atendente, humano, falar com alguém
    - CANCEL: cancelar, desistir
    - CONFIRM: sim, correto, confirma (contextual)
    - DENY: não, errado, alterar (contextual)
    - GREETING: oi, olá, bom dia
    - UNKNOWN: não identificado
    
    Usar hierarquia de prioridades (EMERGENCY > BUY > TRACK > ...)
    """
    pass

def extract_entities(text: str) -> dict:
    """
    Extrai entidades da mensagem:
    - product: P13, P20, P45 (detectar por código, peso, tamanho)
    - quantity: número de botijões (1-10)
    - payment: dinheiro, cartão, pix
    - change_for: valor do troco
    - address_raw: texto do endereço
    - bairro: bairro identificado
    
    Usar dicionário extenso de sinônimos (ver documento anexo)
    """
    pass

def fuzzy_match_product(text: str) -> str | None:
    """
    Identifica produto mesmo com erros de digitação:
    - "butijao pequeno" -> P13
    - "p treze" -> P13
    - "o grandao" -> P45
    """
    pass
```

### TAREFA 2: Criar dicionários de sinônimos

Criar arquivo `backend/app/core/dictionaries.py` com dicionários completos:

```python
# Produtos
PRODUCT_SYNONYMS = {
    'P13': [
        # Códigos
        'p13', 'p 13', 'p-13',
        # Pesos
        '13', 'treze', '13kg', '13 kg', '13kilos', '13quilos',
        # Tamanhos
        'pequeno', 'menor', 'normal', 'comum', 'residencial', 'caseiro', 'domestico',
        # Opções numéricas
        '1', 'um', 'primeiro', 'opcao 1', 'opção 1',
        # Erros comuns
        'p treze', 'ptreze', 'pe13', 'botijao pequeno', 'butijao', 'bujao',
        # Gírias
        'azulzinho', 'o tradicional', 'gas de cozinha', 'gas normal'
    ],
    'P20': [...],  # Similar para P20
    'P45': [...],  # Similar para P45
}

# Quantidades
QUANTITY_SYNONYMS = {
    1: ['1', 'um', 'uma', 'so um', 'apenas um', 'somente um'],
    2: ['2', 'dois', 'duas', 'par', 'um par'],
    3: ['3', 'tres', 'três', 'trio'],
    # ... até 10
}

# Pagamentos
PAYMENT_SYNONYMS = {
    'cash': ['dinheiro', 'din', 'cash', 'especie', 'na mao', 'em maos', 'cedula', 'moeda'],
    'credit_card': ['cartao', 'credito', 'maquininha', 'visa', 'master', 'mastercard', 'elo'],
    'debit_card': ['debito', 'cartao debito'],
    'pix': ['pix', 'px', 'qr code', 'qrcode', 'chave pix'],
}

# Confirmações
CONFIRM_SYNONYMS = [
    'sim', 'simm', 's', 'ss', 'si', 'uhum', 'aham',
    'certo', 'certinho', 'certeza', 'ctz', 'correto', 'exato', 'exatamente',
    'pode', 'pode ser', 'confirma', 'confirmado', 'confirmo', 'fechado', 'fechou',
    'blz', 'beleza', 'show', 'suave', 'tranquilo', 'top', 'perfeito',
    'bora', 'vamo', 'manda', 'dale', 'partiu',
    'claro', 'obvio', 'sem duvida', 'logico', 'positivo', 'boto fe', 'valeu', 'vlw'
]

# Negações
DENY_SYNONYMS = [
    'nao', 'não', 'naoo', 'n', 'nn', 'nope', 'nem', 'nunca', 'jamais',
    'errado', 'incorreto', 'ta errado', 'nao e isso',
    'cancela', 'cancelar', 'desisto', 'nao quero mais', 'deixa pra la',
    'quero alterar', 'alterar', 'trocar', 'mudar', 'outro', 'diferente'
]

# Abreviações do internetês
ABBREVIATIONS = {
    'vc': 'voce', 'vcs': 'voces',
    'tb': 'tambem', 'tbm': 'tambem',
    'pq': 'porque', 'oq': 'o que',
    'qd': 'quando', 'qdo': 'quando',
    'hj': 'hoje', 'mt': 'muito', 'mto': 'muito',
    'blz': 'beleza', 'flw': 'falou', 'vlw': 'valeu',
    'kd': 'cade', 'msg': 'mensagem',
    'obg': 'obrigado', 'dnd': 'de nada', 'dnv': 'de novo',
    'pf': 'por favor', 'pfv': 'por favor',
    'cmg': 'comigo', 'ctg': 'contigo',
    'ta': 'esta', 'to': 'estou', 'eh': 'e',
    'aki': 'aqui', 'agr': 'agora', 'dps': 'depois',
    'msm': 'mesmo', 'qq': 'qualquer', 'qm': 'quem',
    'n': 'nao', 'ss': 'sim',
}

# Saudações
GREETING_SYNONYMS = [
    'oi', 'oii', 'oiii', 'oie', 'opa', 'eai', 'e ai', 'fala', 'salve',
    'bom dia', 'bomdia', 'bd', 'boa tarde', 'boatarde', 'bt',
    'boa noite', 'boanoite', 'bn', 'ola', 'olá', 'hello', 'hey'
]

# Intenção de compra
BUY_KEYWORDS = [
    'quero gas', 'quero gás', 'preciso de gas', 'preciso de gás',
    'quero comprar', 'quero pedir', 'fazer pedido',
    'manda gas', 'manda gás', 'manda um',
    'sem gas', 'sem gás', 'to sem gas', 'tô sem gás',
    'acabou o gas', 'acabou o gás', 'gas acabou', 'gás acabou',
    'preciso de um botijao', 'quero um botijao',
    'quero o de sempre', 'repete o ultimo', 'igual da outra vez'
]

# Rastreamento
TRACK_KEYWORDS = [
    'cade', 'cadê', 'kd', 'onde esta', 'onde está', 'onde ta',
    'status', 'meu pedido', 'meus pedidos',
    'ja saiu', 'já saiu', 'ta vindo', 'tá vindo',
    'quanto tempo', 'demora quanto', 'previsao', 'previsão'
]

# Atendente humano
HUMAN_KEYWORDS = [
    'atendente', 'atendimento', 'humano', 'pessoa', 'gente',
    'falar com alguem', 'falar com alguém', 'quero falar',
    'suporte', 'reclamacao', 'reclamação', 'problema',
    'nao quero robo', 'não quero robô', 'robo burro'
]
```

### TAREFA 3: Refatorar flow_engine.py

Modificar `backend/app/core/flow_engine.py`:

```python
# Substituir o processamento atual por:

async def process_message(self, phone: str, content: str, message_id: str = None):
    """
    Novo fluxo baseado em intenção + entidades.
    """
    # 1. Carregar contexto
    context = await self.get_context(phone)
    
    # 2. Normalizar mensagem
    normalized = normalize_text(content)
    
    # 3. Extrair entidades (pode vir múltiplas de uma vez)
    entities = extract_entities(normalized)
    
    # 4. Mesclar entidades no contexto pendente
    context.pending_entities.update(entities)
    
    # 5. Detectar intenção
    intention = detect_intention(normalized, context)
    
    # 6. Rotear para handler apropriado
    if intention == 'EMERGENCY':
        return await self.handle_emergency(context)
    
    elif intention == 'BUY':
        # Verificar se tem dados completos para atalho
        if self._has_complete_order_data(context):
            return await self.handle_show_confirmation(context)
        else:
            return await self.handle_collect_missing_data(context)
    
    elif intention == 'TRACK':
        return await self.handle_tracking(context)
    
    elif intention == 'HUMAN':
        return await self.handle_transfer_to_human(context)
    
    elif intention == 'CONFIRM' and context.awaiting_confirmation:
        return await self.handle_confirm_order(context)
    
    elif intention == 'DENY' and context.awaiting_confirmation:
        return await self.handle_edit_order(context)
    
    elif intention == 'CANCEL':
        return await self.handle_cancel(context)
    
    elif intention == 'GREETING':
        return await self.handle_greeting(context)
    
    else:
        # Não entendeu - recuperação graciosa
        return await self.handle_not_understood(context)

def _has_complete_order_data(self, context) -> bool:
    """
    Verifica se tem todos os dados para finalizar pedido.
    """
    pe = context.pending_entities
    customer = context.customer
    
    has_product = pe.get('product') or context.selected_product
    has_quantity = pe.get('quantity') or context.selected_quantity
    has_address = pe.get('address') or (customer and customer.address)
    has_payment = pe.get('payment') or context.payment_method
    
    return all([has_product, has_quantity, has_address, has_payment])
```

### TAREFA 4: Refatorar handlers.py

Modificar `backend/app/core/handlers.py`:

```python
# Novos handlers orientados a coleta inteligente:

async def handle_greeting(context):
    """
    Saudação com sugestão inteligente para clientes recorrentes.
    """
    customer = context.customer
    
    if customer and customer.order_count > 0:
        # Cliente recorrente - oferece atalho
        last_order = get_last_order(customer.id)
        
        return {
            'text': f"Oi {customer.name}! 👋\n\n"
                    f"Quer o de sempre? {last_order.quantity}x {last_order.product} "
                    f"no endereço {customer.address}?\n",
            'buttons': [
                {'id': 'repeat_order', 'text': '🔥 Sim, o de sempre'},
                {'id': 'new_order', 'text': '📦 Outro pedido'},
                {'id': 'human', 'text': '💬 Falar com alguém'}
            ]
        }
    else:
        # Cliente novo
        return {
            'text': "Olá! 👋 Bem-vindo à GasMaster!\n\n"
                    "Qual botijão você precisa?\n\n"
                    "🔹 P13 (13kg) - R$ 115,00 - Residencial\n"
                    "🔹 P20 (20kg) - R$ 180,00 - Empilhadeira\n"
                    "🔹 P45 (45kg) - R$ 350,00 - Comercial",
            'buttons': [
                {'id': 'P13', 'text': 'P13 - R$115'},
                {'id': 'P20', 'text': 'P20 - R$180'},
                {'id': 'P45', 'text': 'P45 - R$350'}
            ]
        }

async def handle_collect_missing_data(context):
    """
    Pergunta apenas o que falta, na ordem de prioridade.
    """
    pe = context.pending_entities
    customer = context.customer
    
    # 1. Falta produto?
    if not pe.get('product') and not context.selected_product:
        context.awaiting_input_type = 'product'
        return {
            'text': "Qual botijão você precisa?\n\n"
                    "🔹 P13 (13kg) - R$ 115\n"
                    "🔹 P20 (20kg) - R$ 180\n"
                    "🔹 P45 (45kg) - R$ 350",
            'buttons': [
                {'id': 'P13', 'text': 'P13'},
                {'id': 'P20', 'text': 'P20'},
                {'id': 'P45', 'text': 'P45'}
            ]
        }
    
    # 2. Falta quantidade?
    if not pe.get('quantity') and not context.selected_quantity:
        product = pe.get('product') or context.selected_product
        context.awaiting_input_type = 'quantity'
        return {
            'text': f"Quantos botijões {product} você quer?",
            'buttons': [
                {'id': 'qty_1', 'text': '1'},
                {'id': 'qty_2', 'text': '2'},
                {'id': 'qty_3', 'text': '3'}
            ]
        }
    
    # 3. Falta endereço?
    if not pe.get('address') and not (customer and customer.address):
        context.awaiting_input_type = 'address'
        return {
            'text': "Qual o endereço de entrega?\n"
                    "(Ex: Rua das Flores, 123 - Boqueirão)"
        }
    
    # 4. Falta pagamento?
    if not pe.get('payment') and not context.payment_method:
        context.awaiting_input_type = 'payment'
        return {
            'text': "Como prefere pagar?",
            'buttons': [
                {'id': 'cash', 'text': '💵 Dinheiro'},
                {'id': 'credit_card', 'text': '💳 Cartão'}
            ]
        }
    
    # 5. Falta CPF/CNPJ? (só para clientes novos)
    if not customer.cpf_cnpj:
        context.awaiting_input_type = 'cpf'
        return {
            'text': "Para emitir a nota fiscal, preciso do seu CPF ou CNPJ:"
        }
    
    # 6. Falta nome? (só para clientes novos)
    if not customer.name:
        context.awaiting_input_type = 'name'
        return {
            'text': "E qual seu nome completo?"
        }
    
    # Tudo coletado - mostra confirmação
    return await handle_show_confirmation(context)

async def handle_show_confirmation(context):
    """
    Mostra resumo do pedido para confirmação final.
    """
    pe = context.pending_entities
    customer = context.customer
    
    product = pe.get('product') or context.selected_product
    quantity = pe.get('quantity') or context.selected_quantity or 1
    address = pe.get('address') or customer.address
    payment = pe.get('payment') or context.payment_method
    
    # Calcular total
    price = get_product_price(product)
    total = price * quantity
    
    payment_text = {
        'cash': 'Dinheiro',
        'credit_card': 'Cartão de Crédito',
        'debit_card': 'Cartão de Débito',
        'pix': 'PIX'
    }.get(payment, payment)
    
    # Adicionar info de troco se dinheiro
    if payment == 'cash' and pe.get('change_for'):
        payment_text += f" (troco p/ R$ {pe['change_for']})"
    
    context.awaiting_confirmation = True
    
    return {
        'text': f"📋 *Resumo do Pedido*\n\n"
                f"• {quantity}x {product} — R$ {total:.2f}\n"
                f"• Entrega: {address}\n"
                f"• Pagamento: {payment_text}\n\n"
                f"Tudo certo?",
        'buttons': [
            {'id': 'confirm', 'text': '✅ Confirmar'},
            {'id': 'edit', 'text': '✏️ Alterar'},
            {'id': 'cancel', 'text': '❌ Cancelar'}
        ]
    }

async def handle_not_understood(context):
    """
    Recuperação graciosa quando não entende a mensagem.
    """
    context.retry_count += 1
    
    if context.retry_count == 1:
        # Primeira tentativa: reformula
        return {
            'text': "Não consegui entender. Você quer:\n\n"
                    "• Comprar gás?\n"
                    "• Ver status de um pedido?\n"
                    "• Falar com atendente?",
            'buttons': [
                {'id': 'buy', 'text': '🛒 Comprar gás'},
                {'id': 'track', 'text': '📦 Ver pedido'},
                {'id': 'human', 'text': '💬 Atendente'}
            ]
        }
    
    elif context.retry_count == 2:
        # Segunda tentativa: mais direto
        return {
            'text': "Hmm, ainda não entendi. Toca em uma opção:",
            'buttons': [
                {'id': 'buy', 'text': '🛒 Comprar gás'},
                {'id': 'track', 'text': '📦 Ver pedido'},
                {'id': 'human', 'text': '💬 Atendente'}
            ]
        }
    
    else:
        # Terceira tentativa: transfere para humano
        context.retry_count = 0
        return await handle_transfer_to_human(context)
```

### TAREFA 5: Atualizar modelo Customer

Modificar `backend/app/models/customer.py`:

```python
# Adicionar campos para preferências:

class Customer(Base):
    # ... campos existentes ...
    
    # Novos campos para atalhos
    default_product = Column(String(10), nullable=True)  # P13, P20, P45
    default_quantity = Column(Integer, default=1)
    default_payment = Column(String(20), nullable=True)  # cash, credit_card, pix
    
    # Métricas
    order_count = Column(Integer, default=0)
    last_order_at = Column(DateTime, nullable=True)
    
    # WhatsApp
    whatsapp_name = Column(String(100), nullable=True)  # pushName do WAHA
```

### TAREFA 6: Atualizar ConversationContext

Modificar `backend/app/core/state_machine.py`:

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
    
    # NOVOS CAMPOS para fluxo conversacional
    awaiting_confirmation: bool = False
    awaiting_input_type: Optional[str] = None  # 'product', 'quantity', 'address', 'payment', 'cpf', 'name'
    pending_entities: dict = field(default_factory=dict)  # Entidades extraídas mas não confirmadas
    recent_messages: list = field(default_factory=list)  # Últimas 3 mensagens para contexto
```

---

## REGRAS IMPORTANTES

1. **NÃO QUEBRAR FUNCIONALIDADE EXISTENTE**: O sistema está em produção. Mudanças devem ser incrementais.

2. **MANTER COMPATIBILIDADE COM WAHA**: O formato de envio de mensagens (texto, botões) deve permanecer o mesmo.

3. **REDIS TTL**: Manter TTL de 1800 segundos (30 min) para contexto.

4. **BAIRROS SUPORTADOS**: Manter lista em config.py: Alto Boqueirão, Boqueirão, Ganchinho, Hauer, Sítio Cercado, Umbarã, Xaxim.

5. **INTEGRAÇÃO FIREBIRD**: Continuar buscando clientes no Firebird se não encontrar no PostgreSQL.

6. **WEBSOCKET**: Manter emissão de eventos para painel do operador.

7. **EVENT LOG**: Continuar logando mensagens recebidas/enviadas no PostgreSQL.

---

## ORDEM DE IMPLEMENTAÇÃO SUGERIDA

1. **Fase 1**: Criar `nlp_utils.py` e `dictionaries.py` (sem alterar fluxo existente)
2. **Fase 2**: Adicionar campos no modelo `Customer` e `ConversationContext`
3. **Fase 3**: Criar novos handlers em paralelo aos existentes
4. **Fase 4**: Refatorar `flow_engine.py` para usar novo sistema
5. **Fase 5**: Testes extensivos com mensagens reais
6. **Fase 6**: Remover código legado

---

## TESTES ESPERADOS

Após implementação, o robô deve passar nestes cenários:

```
# Cenário 1: Pedido completo em uma mensagem
INPUT: "manda 2 p13 pra rua das flores 123 boqueirão pago dinheiro"
EXPECTED: Mostrar resumo e pedir confirmação (pular todas as perguntas)

# Cenário 2: Erro de digitação
INPUT: "qero butijao de gaz"
EXPECTED: Detectar intenção COMPRAR, perguntar qual produto

# Cenário 3: Cliente recorrente
INPUT: "oi" (cliente com histórico)
EXPECTED: Oferecer "o de sempre" baseado no último pedido

# Cenário 4: Linguagem informal
INPUT: "e ae, kd meu pedido q pedi hj cedo"
EXPECTED: Detectar intenção RASTREAR, mostrar status

# Cenário 5: Recuperação de erro
INPUT: "asdfghjkl" (3 vezes)
EXPECTED: Transferir para atendente humano após 3 tentativas
```

---

## ARQUIVOS ANEXOS

Consulte os documentos anexos para:
- Dicionário completo de sinônimos (produtos, quantidades, pagamentos, confirmações)
- Abreviações do internetês brasileiro
- Erros ortográficos comuns
- Fluxogramas detalhados
- Cenários de conversa completos
