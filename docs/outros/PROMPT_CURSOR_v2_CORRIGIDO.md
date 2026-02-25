# PROMPT CURSOR - CORREÇÃO FLUXO GASMASTER v2

## PROBLEMAS IDENTIFICADOS

### Bug 1: Estado não muda após coletar nome
```
Cliente: Daniel lopes do nascimento
Robô: Prazer, Daniel Lopes Do Nascimento! Agora preciso do seu CPF...

Cliente: 04370412986
Robô: Prazer, 04370412986!  ← ERRO! Tratou CPF como nome
```
**Causa**: O estado não está sendo salvo no Redis após `handle_collecting_name`. O próximo handler ainda é `COLLECTING_NAME`.

### Bug 2: Não diferencia Pessoa Física de Empresa
O fluxo deveria perguntar se é pessoa física ou empresa ANTES de pedir documentos.

### Bug 3: CPF pedido no momento errado
CPF/CNPJ deve ser pedido APENAS no final do pedido, antes da confirmação, e NÃO é para nota fiscal - é para cadastro do cliente.

---

## NOVO FLUXO CORRETO

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENTE NOVO                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Saudação + Pergunta: PF ou Empresa?                        │
│     [👤 Pessoa Física] [🏢 Empresa]                             │
│                          │                                      │
│         ┌────────────────┴────────────────┐                    │
│         ▼                                 ▼                    │
│  ┌─────────────┐                  ┌─────────────┐              │
│  │ PF: Pedir   │                  │ PJ: Pedir   │              │
│  │ NOME        │                  │ NOME da     │              │
│  │             │                  │ EMPRESA     │              │
│  └──────┬──────┘                  └──────┬──────┘              │
│         │                                │                      │
│         └────────────────┬───────────────┘                     │
│                          ▼                                      │
│              ┌─────────────────────┐                           │
│              │ Mostrar PRODUTOS    │                           │
│              │ (sem pedir CPF/CNPJ)│                           │
│              └──────────┬──────────┘                           │
│                         │                                       │
│                         ▼                                       │
│              ... FLUXO DE PEDIDO ...                           │
│              (produto → quantidade → endereço → pagamento)     │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                           │
│              │ ANTES DE CONFIRMAR: │                           │
│              │ Pedir CPF (PF) ou   │                           │
│              │ CNPJ (PJ)           │                           │
│              └──────────┬──────────┘                           │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                           │
│              │ RESUMO + CONFIRMAR  │                           │
│              └─────────────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## IMPLEMENTAÇÃO PASSO A PASSO

### PASSO 1: Corrigir estados em `state_machine.py`

```python
class ConversationState(str, Enum):
    START = "START"
    
    # Estados de cadastro
    ASKING_CUSTOMER_TYPE = "ASKING_CUSTOMER_TYPE"    # Pergunta PF ou PJ
    COLLECTING_NAME = "COLLECTING_NAME"              # Coleta nome (PF ou empresa)
    
    # Estados de pedido
    AWAITING_PRODUCT = "AWAITING_PRODUCT"
    AWAITING_QUANTITY = "AWAITING_QUANTITY"
    CONFIRMING_ADDRESS = "CONFIRMING_ADDRESS"
    AWAITING_ADDRESS = "AWAITING_ADDRESS"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    
    # CPF/CNPJ só antes de confirmar
    COLLECTING_DOCUMENT = "COLLECTING_DOCUMENT"      # Coleta CPF ou CNPJ
    
    CONFIRMING_ORDER = "CONFIRMING_ORDER"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    TRACKING_ORDER = "TRACKING_ORDER"
    TALKING_TO_HUMAN = "TALKING_TO_HUMAN"
    IDLE = "IDLE"
```

Atualizar `ConversationContext`:

```python
@dataclass
class ConversationContext:
    phone: str
    state: str = "START"
    
    # Dados do cliente
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_type: Optional[str] = None  # "PF" ou "PJ"
    is_new_customer: bool = False
    
    # Pedido
    order_id: Optional[str] = None
    selected_product: Optional[str] = None
    selected_quantity: int = 1
    address: Optional[dict] = None
    address_confirmed: bool = False
    payment_method: Optional[str] = None
    change_for: Optional[int] = None
    
    # Controle
    retry_count: int = 0
    last_message_at: datetime = None
    pending_entities: dict = field(default_factory=dict)
```

---

### PASSO 2: Corrigir `get_or_create_customer()` em `handlers.py`

```python
async def get_or_create_customer(db: Session, phone: str, firebird_client=None) -> tuple:
    """
    Busca ou cria cliente.
    
    Retorna:
        tuple: (customer, is_new, has_name)
        - customer: objeto Customer
        - is_new: True se foi criado agora
        - has_name: True se já tem nome cadastrado
    """
    # Limpar telefone (remover @c.us, @lid, etc)
    clean_phone = phone.split('@')[0] if '@' in phone else phone
    
    # 1. Buscar no PostgreSQL
    customer = db.query(Customer).filter(
        Customer.phone.contains(clean_phone)
    ).first()
    
    if customer:
        has_name = bool(customer.name and len(customer.name) > 2)
        return (customer, False, has_name)
    
    # 2. Buscar no Firebird
    if firebird_client:
        try:
            firebird_data = await firebird_client.get_customer_by_phone(clean_phone)
            if firebird_data:
                customer = Customer(
                    phone=phone,
                    name=firebird_data.get('name'),
                    email=firebird_data.get('email'),
                    cpf_cnpj=firebird_data.get('cpf_cnpj'),
                    address=firebird_data.get('address'),
                    firebird_id=firebird_data.get('id'),
                    customer_type="PJ" if firebird_data.get('cpf_cnpj') and len(firebird_data.get('cpf_cnpj', '')) == 14 else "PF"
                )
                db.add(customer)
                db.commit()
                db.refresh(customer)
                
                has_name = bool(customer.name and len(customer.name) > 2)
                return (customer, False, has_name)
        except Exception as e:
            logger.error(f"Erro Firebird: {e}")
    
    # 3. Cliente totalmente novo
    customer = Customer(phone=phone)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    return (customer, True, False)
```

---

### PASSO 3: Reescrever `handle_start()` em `handlers.py`

```python
async def handle_start(
    phone: str,
    content: str,
    context: ConversationContext,
    db: Session,
    firebird_client=None
) -> FlowResult:
    """
    Handler inicial - identifica cliente e direciona fluxo.
    """
    customer, is_new, has_name = await get_or_create_customer(db, phone, firebird_client)
    
    # Salvar no contexto
    context.customer_id = str(customer.id)
    context.is_new_customer = is_new
    
    # =====================================
    # CLIENTE COM NOME (recorrente ou do Firebird)
    # =====================================
    if has_name:
        context.customer_name = customer.name
        context.customer_type = customer.customer_type or "PF"
        
        # Verificar se tem pedidos anteriores
        last_order = db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.status != "cancelled"
        ).order_by(Order.created_at.desc()).first()
        
        if last_order and customer.address:
            # Oferece atalho "o de sempre"
            return FlowResult(
                next_state="AWAITING_PRODUCT",
                responses=[
                    Response(
                        type="buttons",
                        text=f"Oi, *{customer.name}*! 👋\n\n"
                             f"Quer repetir o último pedido?\n"
                             f"• {last_order.items[0].quantity if last_order.items else 1}x "
                             f"{last_order.items[0].product.code if last_order.items else 'P13'}\n"
                             f"• {customer.address.get('full_address', 'Endereço cadastrado')}\n",
                        buttons=[
                            {"id": "repeat_last", "text": "🔥 Repetir pedido"},
                            {"id": "new_order", "text": "📦 Novo pedido"},
                            {"id": "track", "text": "📍 Meus pedidos"}
                        ]
                    )
                ],
                context_updates={
                    "customer_name": customer.name,
                    "customer_type": context.customer_type
                }
            )
        else:
            # Tem nome mas não tem pedido anterior - ir direto para produtos
            return await show_products(context, db)
    
    # =====================================
    # CLIENTE NOVO OU SEM NOME
    # =====================================
    # Perguntar se é Pessoa Física ou Empresa
    return FlowResult(
        next_state="ASKING_CUSTOMER_TYPE",
        responses=[
            Response(
                type="buttons",
                text="Olá! 👋 Bem-vindo à *GasMaster*!\n\n"
                     "Sou o assistente virtual e vou te ajudar.\n\n"
                     "Para começar, você é:",
                buttons=[
                    {"id": "PF", "text": "👤 Pessoa Física"},
                    {"id": "PJ", "text": "🏢 Empresa"}
                ]
            )
        ],
        context_updates={"is_new_customer": True}
    )


async def show_products(context: ConversationContext, db: Session) -> FlowResult:
    """Helper para mostrar lista de produtos."""
    products = db.query(Product).filter(Product.active == True).all()
    
    product_lines = []
    buttons = []
    for p in products:
        if p.code == "P13":
            product_lines.append(f"🔹 *P13* (13kg) - R$ {p.price:.2f} - Residencial")
        elif p.code == "P20":
            product_lines.append(f"🔹 *P20* (20kg) - R$ {p.price:.2f} - Empilhadeira")
        elif p.code == "P45":
            product_lines.append(f"🔹 *P45* (45kg) - R$ {p.price:.2f} - Comercial")
        buttons.append({"id": p.code, "text": f"{p.code} - R${p.price:.0f}"})
    
    greeting = f"*{context.customer_name}*, qual" if context.customer_name else "Qual"
    
    return FlowResult(
        next_state="AWAITING_PRODUCT",
        responses=[
            Response(
                type="buttons",
                text=f"{greeting} botijão você precisa?\n\n" + "\n".join(product_lines),
                buttons=buttons[:3]  # Máximo 3 botões
            )
        ]
    )
```

---

### PASSO 4: Criar `handle_asking_customer_type()` em `handlers.py`

```python
async def handle_asking_customer_type(
    phone: str,
    content: str,
    context: ConversationContext,
    db: Session
) -> FlowResult:
    """
    Handler para quando perguntamos se é PF ou PJ.
    """
    normalized = content.lower().strip()
    
    # Detectar tipo pelo botão ou texto
    is_pf = any(x in normalized for x in ['pf', 'fisica', 'física', 'pessoa', '👤'])
    is_pj = any(x in normalized for x in ['pj', 'empresa', 'juridica', 'jurídica', 'cnpj', '🏢'])
    
    if is_pj:
        context.customer_type = "PJ"
        return FlowResult(
            next_state="COLLECTING_NAME",
            responses=[
                Response(
                    type="text",
                    text="🏢 Certo! Qual o *nome da empresa*?"
                )
            ],
            context_updates={"customer_type": "PJ"}
        )
    
    elif is_pf:
        context.customer_type = "PF"
        return FlowResult(
            next_state="COLLECTING_NAME",
            responses=[
                Response(
                    type="text",
                    text="👤 Certo! Qual o seu *nome completo*?"
                )
            ],
            context_updates={"customer_type": "PF"}
        )
    
    else:
        # Não entendeu - repetir pergunta
        context.retry_count += 1
        
        if context.retry_count >= 2:
            # Assumir PF após 2 tentativas
            context.customer_type = "PF"
            return FlowResult(
                next_state="COLLECTING_NAME",
                responses=[
                    Response(
                        type="text",
                        text="Vou continuar como pessoa física.\n\n"
                             "Qual o seu *nome completo*?"
                    )
                ],
                context_updates={"customer_type": "PF", "retry_count": 0}
            )
        
        return FlowResult(
            next_state="ASKING_CUSTOMER_TYPE",
            responses=[
                Response(
                    type="buttons",
                    text="Por favor, escolha uma opção:",
                    buttons=[
                        {"id": "PF", "text": "👤 Pessoa Física"},
                        {"id": "PJ", "text": "🏢 Empresa"}
                    ]
                )
            ]
        )
```

---

### PASSO 5: Corrigir `handle_collecting_name()` em `handlers.py`

**IMPORTANTE**: Este handler DEVE salvar o contexto no Redis E mudar o estado corretamente.

```python
async def handle_collecting_name(
    phone: str,
    content: str,
    context: ConversationContext,
    db: Session
) -> FlowResult:
    """
    Handler para coletar nome do cliente ou empresa.
    IMPORTANTE: Após coletar, vai direto para PRODUTOS (não pede CPF aqui).
    """
    name = content.strip()
    
    # Validar nome
    if len(name) < 2:
        return FlowResult(
            next_state="COLLECTING_NAME",  # Permanece no mesmo estado
            responses=[
                Response(
                    type="text",
                    text="Nome muito curto. Por favor, digite o nome completo:"
                )
            ]
        )
    
    if len(name) > 100:
        name = name[:100]
    
    # Formatar nome
    name = name.title()
    
    # Salvar no banco de dados
    customer = db.query(Customer).filter(Customer.id == context.customer_id).first()
    if customer:
        customer.name = name
        customer.customer_type = context.customer_type
        db.commit()
        logger.info(f"Nome salvo para cliente {customer.id}: {name}")
    
    # Atualizar contexto
    context.customer_name = name
    
    # IR DIRETO PARA PRODUTOS (não pedir CPF agora!)
    if context.customer_type == "PJ":
        greeting = f"Prazer, *{name}*! 🏢"
    else:
        greeting = f"Prazer, *{name}*! 👋"
    
    # Buscar produtos
    products = db.query(Product).filter(Product.active == True).all()
    
    product_lines = []
    buttons = []
    for p in products:
        if p.code == "P13":
            product_lines.append(f"🔹 *P13* (13kg) - R$ {p.price:.2f}")
        elif p.code == "P20":
            product_lines.append(f"🔹 *P20* (20kg) - R$ {p.price:.2f}")
        elif p.code == "P45":
            product_lines.append(f"🔹 *P45* (45kg) - R$ {p.price:.2f}")
        buttons.append({"id": p.code, "text": f"{p.code} - R${p.price:.0f}"})
    
    return FlowResult(
        next_state="AWAITING_PRODUCT",  # MUDA PARA PRODUTOS!
        responses=[
            Response(
                type="buttons",
                text=f"{greeting}\n\n"
                     f"Qual botijão você precisa?\n\n" + "\n".join(product_lines),
                buttons=buttons[:3]
            )
        ],
        context_updates={
            "customer_name": name,
            "state": "AWAITING_PRODUCT"  # Força atualização do estado
        }
    )
```

---

### PASSO 6: Criar `handle_collecting_document()` - CHAMADO ANTES DE CONFIRMAR

Este handler é chamado APENAS antes de mostrar o resumo final, quando já tem produto, quantidade, endereço e pagamento.

```python
async def handle_collecting_document(
    phone: str,
    content: str,
    context: ConversationContext,
    db: Session
) -> FlowResult:
    """
    Handler para coletar CPF (PF) ou CNPJ (PJ).
    Chamado ANTES da confirmação final do pedido.
    """
    import re
    
    # Limpar entrada
    doc = re.sub(r'[^0-9]', '', content)
    
    # Validar baseado no tipo de cliente
    if context.customer_type == "PJ":
        # Espera CNPJ (14 dígitos)
        if len(doc) != 14:
            return FlowResult(
                next_state="COLLECTING_DOCUMENT",
                responses=[
                    Response(
                        type="text",
                        text="❌ CNPJ inválido. Digite os *14 números* do CNPJ:"
                    )
                ]
            )
        doc_type = "CNPJ"
        formatted = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    else:
        # Espera CPF (11 dígitos)
        if len(doc) != 11:
            return FlowResult(
                next_state="COLLECTING_DOCUMENT",
                responses=[
                    Response(
                        type="text",
                        text="❌ CPF inválido. Digite os *11 números* do CPF:"
                    )
                ]
            )
        
        # Validar CPF
        if not validate_cpf(doc):
            return FlowResult(
                next_state="COLLECTING_DOCUMENT",
                responses=[
                    Response(
                        type="text",
                        text="❌ CPF inválido. Verifique e digite novamente:"
                    )
                ]
            )
        
        doc_type = "CPF"
        formatted = f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    
    # Salvar no banco
    customer = db.query(Customer).filter(Customer.id == context.customer_id).first()
    if customer:
        customer.cpf_cnpj = doc
        db.commit()
    
    # Agora mostrar resumo do pedido para confirmação
    return await show_order_summary(context, db, doc_type, formatted)


def validate_cpf(cpf: str) -> bool:
    """Valida dígitos verificadores do CPF."""
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    for i in range(9, 11):
        value = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
        digit = ((value * 10) % 11) % 10
        if digit != int(cpf[i]):
            return False
    return True


async def show_order_summary(
    context: ConversationContext, 
    db: Session,
    doc_type: str,
    formatted_doc: str
) -> FlowResult:
    """Mostra resumo do pedido para confirmação final."""
    
    # Buscar preço do produto
    product = db.query(Product).filter(Product.code == context.selected_product).first()
    price = product.price if product else 0
    total = price * context.selected_quantity
    
    # Formatar endereço
    address_text = "Endereço não informado"
    if context.address:
        address_text = context.address.get('full_address', str(context.address))
    
    # Formatar pagamento
    payment_map = {
        'cash': '💵 Dinheiro',
        'credit_card': '💳 Cartão de Crédito',
        'debit_card': '💳 Cartão de Débito',
        'pix': '📱 PIX'
    }
    payment_text = payment_map.get(context.payment_method, context.payment_method)
    
    if context.payment_method == 'cash' and context.change_for:
        payment_text += f" (troco p/ R$ {context.change_for})"
    
    # Mascarar documento
    if doc_type == "CPF":
        masked_doc = f"***.{formatted_doc[4:7]}.{formatted_doc[8:11]}-**"
    else:
        masked_doc = f"**.{formatted_doc[3:6]}.{formatted_doc[7:10]}/****-**"
    
    return FlowResult(
        next_state="CONFIRMING_ORDER",
        responses=[
            Response(
                type="buttons",
                text=f"📋 *Resumo do Pedido*\n\n"
                     f"👤 {context.customer_name}\n"
                     f"📄 {doc_type}: {masked_doc}\n\n"
                     f"📦 {context.selected_quantity}x {context.selected_product} — *R$ {total:.2f}*\n"
                     f"📍 {address_text}\n"
                     f"💳 {payment_text}\n\n"
                     f"✅ *Confirma o pedido?*",
                buttons=[
                    {"id": "confirm", "text": "✅ Confirmar"},
                    {"id": "edit", "text": "✏️ Alterar"},
                    {"id": "cancel", "text": "❌ Cancelar"}
                ]
            )
        ]
    )
```

---

### PASSO 7: Modificar `handle_awaiting_payment()` para ir para COLLECTING_DOCUMENT

Quando o cliente escolhe o pagamento, ANTES de confirmar, pedir o CPF/CNPJ:

```python
async def handle_awaiting_payment(
    phone: str,
    content: str,
    context: ConversationContext,
    db: Session
) -> FlowResult:
    """
    Handler para forma de pagamento.
    Após escolher, vai para COLLECTING_DOCUMENT (se não tem CPF/CNPJ).
    """
    normalized = content.lower().strip()
    
    # Detectar forma de pagamento
    payment = None
    change_for = None
    
    if any(x in normalized for x in ['dinheiro', 'cash', 'din', 'especie']):
        payment = 'cash'
        # Verificar se mencionou troco
        import re
        match = re.search(r'troco\s*(?:pra|para|de|p/)?\s*(\d+)', normalized)
        if match:
            change_for = int(match.group(1))
    
    elif any(x in normalized for x in ['credito', 'crédito', 'cartao', 'cartão', 'credit']):
        payment = 'credit_card'
    
    elif any(x in normalized for x in ['debito', 'débito', 'debit']):
        payment = 'debit_card'
    
    elif any(x in normalized for x in ['pix', 'px']):
        payment = 'pix'
    
    if not payment:
        return FlowResult(
            next_state="AWAITING_PAYMENT",
            responses=[
                Response(
                    type="buttons",
                    text="Como você prefere pagar?",
                    buttons=[
                        {"id": "cash", "text": "💵 Dinheiro"},
                        {"id": "credit_card", "text": "💳 Cartão"}
                    ]
                )
            ]
        )
    
    # Salvar pagamento no contexto
    context.payment_method = payment
    context.change_for = change_for
    
    # Verificar se já tem CPF/CNPJ cadastrado
    customer = db.query(Customer).filter(Customer.id == context.customer_id).first()
    
    if customer and customer.cpf_cnpj:
        # Já tem documento - ir direto para confirmação
        doc = customer.cpf_cnpj
        if len(doc) == 11:
            doc_type = "CPF"
            formatted = f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
        else:
            doc_type = "CNPJ"
            formatted = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
        
        return await show_order_summary(context, db, doc_type, formatted)
    
    # Não tem documento - pedir agora
    if context.customer_type == "PJ":
        doc_text = "Para finalizar, preciso do *CNPJ* da empresa:\n_(apenas números)_"
    else:
        doc_text = "Para finalizar, preciso do seu *CPF*:\n_(apenas números)_"
    
    return FlowResult(
        next_state="COLLECTING_DOCUMENT",
        responses=[
            Response(
                type="text",
                text=f"✅ Pagamento: {payment_map.get(payment, payment)}\n\n{doc_text}"
            )
        ],
        context_updates={
            "payment_method": payment,
            "change_for": change_for
        }
    )


# Mapas globais
payment_map = {
    'cash': '💵 Dinheiro',
    'credit_card': '💳 Cartão de Crédito',
    'debit_card': '💳 Cartão de Débito',
    'pix': '📱 PIX'
}
```

---

### PASSO 8: Atualizar roteamento em `flow_engine.py`

```python
async def _route_to_handler(self, state: str, phone: str, content: str, context, db, firebird_client=None):
    """Roteia para o handler apropriado."""
    
    # Mapa de handlers
    handlers = {
        "START": lambda: handle_start(phone, content, context, db, firebird_client),
        "ASKING_CUSTOMER_TYPE": lambda: handle_asking_customer_type(phone, content, context, db),
        "COLLECTING_NAME": lambda: handle_collecting_name(phone, content, context, db),
        "AWAITING_PRODUCT": lambda: handle_awaiting_product(phone, content, context, db),
        "AWAITING_QUANTITY": lambda: handle_awaiting_quantity(phone, content, context, db),
        "CONFIRMING_ADDRESS": lambda: handle_confirming_address(phone, content, context, db),
        "AWAITING_ADDRESS": lambda: handle_awaiting_address(phone, content, context, db),
        "AWAITING_PAYMENT": lambda: handle_awaiting_payment(phone, content, context, db),
        "COLLECTING_DOCUMENT": lambda: handle_collecting_document(phone, content, context, db),
        "CONFIRMING_ORDER": lambda: handle_confirming_order(phone, content, context, db),
        "ORDER_CONFIRMED": lambda: handle_order_confirmed(phone, content, context, db),
        "TRACKING_ORDER": lambda: handle_tracking_order(phone, content, context, db),
        "TALKING_TO_HUMAN": lambda: handle_talking_to_human(phone, content, context, db),
    }
    
    handler = handlers.get(state)
    if handler:
        result = await handler()
        
        # IMPORTANTE: Atualizar estado no contexto
        if result and result.next_state:
            context.state = result.next_state
            await self.save_context(phone, context)  # Salvar no Redis!
        
        return result
    
    # Estado desconhecido - ir para START
    return await handle_start(phone, content, context, db, firebird_client)
```

---

### PASSO 9: Verificar `save_context()` em `flow_engine.py`

Garantir que o estado está sendo salvo corretamente no Redis:

```python
async def save_context(self, phone: str, context: ConversationContext):
    """Salva contexto no Redis."""
    key = f"chat:{phone}"
    
    # Converter para dict
    data = {
        "phone": context.phone,
        "state": context.state,  # IMPORTANTE!
        "customer_id": context.customer_id,
        "customer_name": context.customer_name,
        "customer_type": context.customer_type,
        "is_new_customer": context.is_new_customer,
        "order_id": context.order_id,
        "selected_product": context.selected_product,
        "selected_quantity": context.selected_quantity,
        "address": context.address,
        "address_confirmed": context.address_confirmed,
        "payment_method": context.payment_method,
        "change_for": context.change_for,
        "retry_count": context.retry_count,
        "pending_entities": context.pending_entities,
    }
    
    # Salvar com TTL
    await self.redis.setex(
        key, 
        self.config.redis_conversation_ttl,  # 1800 segundos
        json.dumps(data)
    )
    
    logger.debug(f"Contexto salvo para {phone}: state={context.state}")
```

---

## NOVO FLUXO ESPERADO

### Cliente Novo - Pessoa Física:
```
Cliente: oi
Robô: Olá! 👋 Bem-vindo à *GasMaster*!
      Sou o assistente virtual e vou te ajudar.
      Para começar, você é:
      [👤 Pessoa Física] [🏢 Empresa]

Cliente: pessoa física
Robô: 👤 Certo! Qual o seu *nome completo*?

Cliente: Daniel Lopes do Nascimento
Robô: Prazer, *Daniel Lopes Do Nascimento*! 👋
      Qual botijão você precisa?
      🔹 *P13* (13kg) - R$ 115.00
      🔹 *P20* (20kg) - R$ 180.00
      🔹 *P45* (45kg) - R$ 350.00
      [P13 - R$115] [P20 - R$180] [P45 - R$350]

... (fluxo de pedido: produto → quantidade → endereço → pagamento) ...

Cliente: dinheiro
Robô: ✅ Pagamento: 💵 Dinheiro
      
      Para finalizar, preciso do seu *CPF*:
      _(apenas números)_

Cliente: 04370412986
Robô: 📋 *Resumo do Pedido*
      
      👤 Daniel Lopes Do Nascimento
      📄 CPF: ***.704.129-**
      
      📦 2x P13 — *R$ 230.00*
      📍 Rua das Flores, 123 - Boqueirão
      💳 💵 Dinheiro
      
      ✅ *Confirma o pedido?*
      [✅ Confirmar] [✏️ Alterar] [❌ Cancelar]
```

### Cliente Novo - Empresa:
```
Cliente: oi
Robô: ... [👤 Pessoa Física] [🏢 Empresa]

Cliente: empresa
Robô: 🏢 Certo! Qual o *nome da empresa*?

Cliente: Restaurante Sabor Caseiro
Robô: Prazer, *Restaurante Sabor Caseiro*! 🏢
      Qual botijão você precisa?
      ...

... (no final) ...

Robô: Para finalizar, preciso do *CNPJ* da empresa:
      _(apenas números)_
```

---

## CHECKLIST

- [ ] Estado `ASKING_CUSTOMER_TYPE` criado
- [ ] Estado `COLLECTING_DOCUMENT` criado (substituiu `COLLECTING_CPF`)
- [ ] `handle_start()` pergunta PF ou PJ para clientes novos
- [ ] `handle_asking_customer_type()` criado
- [ ] `handle_collecting_name()` vai para PRODUTOS (não para CPF)
- [ ] `handle_awaiting_payment()` vai para `COLLECTING_DOCUMENT`
- [ ] `handle_collecting_document()` valida CPF ou CNPJ baseado no tipo
- [ ] `save_context()` salva o estado corretamente no Redis
- [ ] Roteamento atualizado no `flow_engine.py`
