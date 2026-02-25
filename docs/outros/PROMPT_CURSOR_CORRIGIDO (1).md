# PROMPT CURSOR - CORREÇÃO DO FLUXO DE IDENTIFICAÇÃO GASMASTER

## PROBLEMA ATUAL

O robô está mostrando o menu antigo para TODOS os clientes:
```
Ola! Bem-vindo a GasMaster!
Como posso ajudar?
1. Fazer Pedido
2. Meus Pedidos
3. Atendente
```

Isso acontece porque:
1. A função `get_or_create_customer()` não retorna se o cliente é novo ou não
2. O handler de saudação não diferencia cliente novo de recorrente
3. O fluxo não coleta nome/CPF de clientes novos

---

## SOLUÇÃO: IMPLEMENTAÇÃO PASSO A PASSO

### PASSO 1: Modificar `get_or_create_customer()` em `handlers.py`

Localize a função `get_or_create_customer` e modifique para retornar uma tupla `(customer, is_new, has_complete_data)`:

```python
async def get_or_create_customer(db: Session, phone: str, firebird_client=None) -> tuple:
    """
    Busca ou cria cliente.
    
    Retorna:
        tuple: (customer, is_new, has_complete_data)
        - customer: objeto Customer
        - is_new: True se foi criado agora (não existia em lugar nenhum)
        - has_complete_data: True se tem nome E (cpf_cnpj OU endereço)
    """
    # 1. Buscar no PostgreSQL
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    
    if customer:
        # Cliente existe no PostgreSQL
        has_complete_data = bool(customer.name) and bool(customer.cpf_cnpj or customer.address)
        return (customer, False, has_complete_data)
    
    # 2. Buscar no Firebird (ERP legado)
    if firebird_client:
        try:
            firebird_data = await firebird_client.get_customer_by_phone(phone)
            if firebird_data:
                # Encontrou no Firebird - criar no PostgreSQL com dados completos
                customer = Customer(
                    phone=phone,
                    name=firebird_data.get('name'),
                    email=firebird_data.get('email'),
                    cpf_cnpj=firebird_data.get('cpf_cnpj'),
                    address=firebird_data.get('address'),
                    firebird_id=firebird_data.get('id')
                )
                db.add(customer)
                db.commit()
                db.refresh(customer)
                
                has_complete_data = bool(customer.name) and bool(customer.cpf_cnpj or customer.address)
                return (customer, False, has_complete_data)  # Não é novo, veio do Firebird
        except Exception as e:
            logger.error(f"Erro ao buscar no Firebird: {e}")
    
    # 3. Cliente totalmente novo - criar apenas com telefone
    customer = Customer(phone=phone)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    return (customer, True, False)  # É novo, não tem dados completos
```

---

### PASSO 2: Criar novos estados em `state_machine.py`

Adicione estes estados para coleta de dados:

```python
class ConversationState(str, Enum):
    START = "START"
    
    # NOVOS ESTADOS PARA COLETA DE DADOS
    COLLECTING_NAME = "COLLECTING_NAME"          # Aguardando nome do cliente
    COLLECTING_CPF = "COLLECTING_CPF"            # Aguardando CPF/CNPJ
    
    # Estados existentes
    AWAITING_PRODUCT = "AWAITING_PRODUCT"
    AWAITING_QUANTITY = "AWAITING_QUANTITY"
    CONFIRMING_ADDRESS = "CONFIRMING_ADDRESS"
    AWAITING_ADDRESS = "AWAITING_ADDRESS"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    CONFIRMING_ORDER = "CONFIRMING_ORDER"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    TRACKING_ORDER = "TRACKING_ORDER"
    TALKING_TO_HUMAN = "TALKING_TO_HUMAN"
    IDLE = "IDLE"
```

Adicione no `ConversationContext`:

```python
@dataclass
class ConversationContext:
    # ... campos existentes ...
    
    # NOVOS CAMPOS
    is_new_customer: bool = False           # Se é cliente totalmente novo
    has_complete_data: bool = False         # Se tem dados completos
    pending_name: Optional[str] = None      # Nome aguardando confirmação
    pending_cpf: Optional[str] = None       # CPF aguardando confirmação
    collecting_data_for: str = "order"      # "order" ou "registration"
```

---

### PASSO 3: Modificar `handle_start()` em `handlers.py`

Substitua completamente a função `handle_start`:

```python
async def handle_start(
    phone: str,
    content: str,
    context: ConversationContext,
    db: Session,
    firebird_client=None
) -> FlowResult:
    """
    Handler inicial que diferencia cliente novo de recorrente.
    """
    # Buscar/criar cliente
    customer, is_new, has_complete_data = await get_or_create_customer(
        db, phone, firebird_client
    )
    
    # Salvar no contexto
    context.customer_id = str(customer.id)
    context.customer_name = customer.name
    context.is_new_customer = is_new
    context.has_complete_data = has_complete_data
    
    # Detectar intenção da mensagem
    normalized = normalize_text(content)
    intention = detect_intention(normalized, context)
    entities = extract_entities(normalized)
    
    # Guardar entidades extraídas
    if entities:
        context.pending_entities = entities
    
    # ========================================
    # CENÁRIO 1: Cliente NOVO (nunca comprou)
    # ========================================
    if is_new:
        # Saudação para cliente novo + pedir nome
        context.state = "COLLECTING_NAME"
        
        responses = [
            Response(
                type="text",
                text="Olá! 👋 Bem-vindo à *GasMaster*!\n\n"
                     "Sou o assistente virtual e vou te ajudar a pedir seu gás.\n\n"
                     "Para começar, qual é o seu *nome completo*?"
            )
        ]
        
        return FlowResult(
            next_state="COLLECTING_NAME",
            responses=responses,
            context_updates={"is_new_customer": True, "customer_id": str(customer.id)}
        )
    
    # ========================================
    # CENÁRIO 2: Cliente RECORRENTE com dados completos
    # ========================================
    if has_complete_data and customer.name:
        # Verificar se tem pedidos anteriores para sugerir "o de sempre"
        last_order = get_last_order(db, customer.id)
        
        if last_order:
            # Cliente frequente - oferece atalho
            context.state = "AWAITING_PRODUCT"
            
            responses = [
                Response(
                    type="buttons",
                    text=f"Oi, *{customer.name}*! 👋 Que bom te ver de novo!\n\n"
                         f"Quer repetir o último pedido?\n"
                         f"• {last_order.quantity}x {last_order.product_code}\n"
                         f"• Entrega: {customer.address}\n",
                    buttons=[
                        {"id": "repeat_last", "text": "🔥 Sim, o de sempre"},
                        {"id": "new_order", "text": "📦 Novo pedido"},
                        {"id": "track_order", "text": "📍 Ver pedidos"}
                    ]
                )
            ]
        else:
            # Cliente cadastrado mas sem pedidos anteriores
            products = get_products_with_prices(db)
            product_text = format_product_list(products)
            
            responses = [
                Response(
                    type="buttons",
                    text=f"Oi, *{customer.name}*! 👋\n\n"
                         f"Qual botijão você precisa?\n\n{product_text}",
                    buttons=[
                        {"id": "P13", "text": f"P13 - R${products['P13']:.0f}"},
                        {"id": "P20", "text": f"P20 - R${products['P20']:.0f}"},
                        {"id": "P45", "text": f"P45 - R${products['P45']:.0f}"}
                    ]
                )
            ]
        
        return FlowResult(
            next_state="AWAITING_PRODUCT",
            responses=responses,
            context_updates={"customer_name": customer.name}
        )
    
    # ========================================
    # CENÁRIO 3: Cliente existe mas INCOMPLETO (falta nome ou CPF)
    # ========================================
    if not customer.name:
        context.state = "COLLECTING_NAME"
        
        responses = [
            Response(
                type="text",
                text="Olá! 👋 Vi que você já entrou em contato antes.\n\n"
                     "Para agilizar seu pedido, qual é o seu *nome completo*?"
            )
        ]
        
        return FlowResult(
            next_state="COLLECTING_NAME",
            responses=responses
        )
    
    # Fallback: tem nome mas falta CPF - seguir para produtos
    products = get_products_with_prices(db)
    product_text = format_product_list(products)
    
    responses = [
        Response(
            type="buttons",
            text=f"Oi, *{customer.name}*! 👋\n\n"
                 f"Qual botijão você precisa?\n\n{product_text}",
            buttons=[
                {"id": "P13", "text": f"P13 - R${products['P13']:.0f}"},
                {"id": "P20", "text": f"P20 - R${products['P20']:.0f}"},
                {"id": "P45", "text": f"P45 - R${products['P45']:.0f}"}
            ]
        )
    ]
    
    return FlowResult(
        next_state="AWAITING_PRODUCT",
        responses=responses
    )


def get_last_order(db: Session, customer_id: str):
    """Busca o último pedido do cliente."""
    from ..models.order import Order
    
    return db.query(Order).filter(
        Order.customer_id == customer_id,
        Order.status != "cancelled"
    ).order_by(Order.created_at.desc()).first()


def get_products_with_prices(db: Session) -> dict:
    """Busca produtos com preços do banco."""
    from ..models.product import Product
    
    products = db.query(Product).filter(Product.active == True).all()
    return {p.code: p.price for p in products}


def format_product_list(products: dict) -> str:
    """Formata lista de produtos para exibição."""
    lines = []
    descriptions = {
        'P13': '🔹 *P13* (13kg) - Residencial',
        'P20': '🔹 *P20* (20kg) - Empilhadeira',
        'P45': '🔹 *P45* (45kg) - Comercial'
    }
    for code, price in products.items():
        desc = descriptions.get(code, f'🔹 *{code}*')
        lines.append(f"{desc} - R$ {price:.2f}")
    return '\n'.join(lines)
```

---

### PASSO 4: Criar handler para COLLECTING_NAME

Adicione em `handlers.py`:

```python
async def handle_collecting_name(
    phone: str,
    content: str,
    context: ConversationContext,
    db: Session
) -> FlowResult:
    """
    Handler para coletar nome do cliente.
    """
    # Validar nome (mínimo 3 caracteres, máximo 100)
    name = content.strip()
    
    if len(name) < 3:
        return FlowResult(
            next_state="COLLECTING_NAME",
            responses=[
                Response(
                    type="text",
                    text="Por favor, digite seu *nome completo* (mínimo 3 letras):"
                )
            ]
        )
    
    if len(name) > 100:
        name = name[:100]
    
    # Capitalizar nome
    name = name.title()
    
    # Salvar nome no banco
    customer = db.query(Customer).filter(Customer.id == context.customer_id).first()
    if customer:
        customer.name = name
        db.commit()
    
    # Atualizar contexto
    context.customer_name = name
    
    # Agora pedir CPF/CNPJ
    return FlowResult(
        next_state="COLLECTING_CPF",
        responses=[
            Response(
                type="text",
                text=f"Prazer, *{name}*! 😊\n\n"
                     f"Agora preciso do seu *CPF ou CNPJ* para emitir a nota fiscal:\n\n"
                     f"_(Digite apenas os números)_"
            )
        ],
        context_updates={"customer_name": name}
    )
```

---

### PASSO 5: Criar handler para COLLECTING_CPF

Adicione em `handlers.py`:

```python
import re

def validate_cpf(cpf: str) -> bool:
    """Valida CPF brasileiro."""
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    # Validação dos dígitos verificadores
    for i in range(9, 11):
        value = sum((int(cpf[num]) * ((i + 1) - num) for num in range(0, i)))
        digit = ((value * 10) % 11) % 10
        if digit != int(cpf[i]):
            return False
    return True


def validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ brasileiro."""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False
    # Validação simplificada
    return True


def format_cpf_cnpj(value: str) -> str:
    """Formata CPF ou CNPJ para exibição parcial."""
    clean = re.sub(r'[^0-9]', '', value)
    if len(clean) == 11:
        # CPF: ***.456.789-**
        return f"***.{clean[3:6]}.{clean[6:9]}-**"
    elif len(clean) == 14:
        # CNPJ: **.456.789/0001-**
        return f"**.{clean[2:5]}.{clean[5:8]}/{clean[8:12]}-**"
    return value


async def handle_collecting_cpf(
    phone: str,
    content: str,
    context: ConversationContext,
    db: Session
) -> FlowResult:
    """
    Handler para coletar CPF/CNPJ do cliente.
    """
    # Limpar entrada
    cpf_cnpj = re.sub(r'[^0-9]', '', content)
    
    # Validar
    is_valid = False
    if len(cpf_cnpj) == 11:
        is_valid = validate_cpf(cpf_cnpj)
    elif len(cpf_cnpj) == 14:
        is_valid = validate_cnpj(cpf_cnpj)
    
    if not is_valid:
        return FlowResult(
            next_state="COLLECTING_CPF",
            responses=[
                Response(
                    type="text",
                    text="❌ CPF/CNPJ inválido.\n\n"
                         "Por favor, digite novamente apenas os *números*:\n"
                         "• CPF: 11 dígitos\n"
                         "• CNPJ: 14 dígitos"
                )
            ]
        )
    
    # Salvar no banco
    customer = db.query(Customer).filter(Customer.id == context.customer_id).first()
    if customer:
        customer.cpf_cnpj = cpf_cnpj
        db.commit()
    
    # Marcar dados como completos
    context.has_complete_data = True
    
    # Mostrar produtos
    products = get_products_with_prices(db)
    product_text = format_product_list(products)
    
    formatted_doc = format_cpf_cnpj(cpf_cnpj)
    
    return FlowResult(
        next_state="AWAITING_PRODUCT",
        responses=[
            Response(
                type="buttons",
                text=f"✅ Cadastro concluído!\n\n"
                     f"📋 *{context.customer_name}*\n"
                     f"📄 {formatted_doc}\n\n"
                     f"Agora sim! Qual botijão você precisa?\n\n{product_text}",
                buttons=[
                    {"id": "P13", "text": f"P13 - R${products['P13']:.0f}"},
                    {"id": "P20", "text": f"P20 - R${products['P20']:.0f}"},
                    {"id": "P45", "text": f"P45 - R${products['P45']:.0f}"}
                ]
            )
        ],
        context_updates={"has_complete_data": True}
    )
```

---

### PASSO 6: Atualizar `flow_engine.py` para rotear os novos estados

No método que roteia para handlers, adicione:

```python
async def _route_to_handler(self, state: str, phone: str, content: str, context, db):
    """Roteia para o handler apropriado baseado no estado."""
    
    handlers = {
        "START": handle_start,
        "COLLECTING_NAME": handle_collecting_name,      # NOVO
        "COLLECTING_CPF": handle_collecting_cpf,        # NOVO
        "AWAITING_PRODUCT": handle_awaiting_product,
        "AWAITING_QUANTITY": handle_awaiting_quantity,
        "CONFIRMING_ADDRESS": handle_confirming_address,
        "AWAITING_ADDRESS": handle_awaiting_address,
        "AWAITING_PAYMENT": handle_awaiting_payment,
        "CONFIRMING_ORDER": handle_confirming_order,
        "ORDER_CONFIRMED": handle_order_confirmed,
        "TRACKING_ORDER": handle_tracking_order,
        "TALKING_TO_HUMAN": handle_talking_to_human,
    }
    
    handler = handlers.get(state)
    if handler:
        return await handler(phone, content, context, db)
    
    # Fallback para START
    return await handle_start(phone, content, context, db)
```

---

### PASSO 7: Adicionar imports necessários

No topo de `handlers.py`:

```python
import re
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from ..models.customer import Customer
from ..models.order import Order
from ..models.product import Product
from .state_machine import ConversationContext, ConversationState
from .nlp_utils import normalize_text, detect_intention, extract_entities

logger = logging.getLogger(__name__)
```

---

## FLUXO ESPERADO APÓS IMPLEMENTAÇÃO

### Cliente NOVO (primeira vez):
```
Cliente: oi
Robô: Olá! 👋 Bem-vindo à *GasMaster*!
      Sou o assistente virtual e vou te ajudar a pedir seu gás.
      Para começar, qual é o seu *nome completo*?

Cliente: João da Silva
Robô: Prazer, *João Da Silva*! 😊
      Agora preciso do seu *CPF ou CNPJ* para emitir a nota fiscal:
      _(Digite apenas os números)_

Cliente: 12345678900
Robô: ✅ Cadastro concluído!
      📋 *João Da Silva*
      📄 ***.456.789-**
      
      Agora sim! Qual botijão você precisa?
      🔹 *P13* (13kg) - Residencial - R$ 115.00
      🔹 *P20* (20kg) - Empilhadeira - R$ 180.00
      🔹 *P45* (45kg) - Comercial - R$ 350.00
      [P13 - R$115] [P20 - R$180] [P45 - R$350]
```

### Cliente RECORRENTE (já comprou antes):
```
Cliente: oi
Robô: Oi, *João Da Silva*! 👋 Que bom te ver de novo!
      
      Quer repetir o último pedido?
      • 2x P13
      • Entrega: Rua das Flores, 123 - Boqueirão
      
      [🔥 Sim, o de sempre] [📦 Novo pedido] [📍 Ver pedidos]
```

### Cliente INCOMPLETO (existe mas falta nome):
```
Cliente: oi
Robô: Olá! 👋 Vi que você já entrou em contato antes.
      Para agilizar seu pedido, qual é o seu *nome completo*?
```

---

## CHECKLIST DE VERIFICAÇÃO

Após implementar, verifique:

- [ ] `get_or_create_customer()` retorna tupla `(customer, is_new, has_complete_data)`
- [ ] Estados `COLLECTING_NAME` e `COLLECTING_CPF` existem em `state_machine.py`
- [ ] `handle_start()` diferencia os 3 cenários (novo, recorrente, incompleto)
- [ ] `handle_collecting_name()` valida e salva nome no banco
- [ ] `handle_collecting_cpf()` valida CPF/CNPJ e salva no banco
- [ ] `flow_engine.py` roteia para os novos handlers
- [ ] Importações estão corretas em todos os arquivos

---

## COMANDO PARA TESTAR

Após implementar, reinicie o servidor e teste enviando "oi" de um número novo que não existe no banco.

```bash
# Verificar se cliente foi criado
psql -d gasmaster -c "SELECT id, phone, name, cpf_cnpj, created_at FROM customers ORDER BY created_at DESC LIMIT 5;"
```
