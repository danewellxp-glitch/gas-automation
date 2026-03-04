## 🚛 Jornada do Pedido: Do WhatsApp à Entrega

Este diagrama ilustra o passo a passo de como um pedido transita pelos sistemas do Gas Automation de forma contínua, invisível ao cliente e rápida para os entregadores.

```mermaid
sequenceDiagram
    autonumber
    
    box rgb(240, 255, 240) Experiência do Cliente
        participant C as 📱 Cliente (WhatsApp)
    end
    box rgb(230, 240, 255) Sistema Central (O Cérebro)
        participant W as 🤖 Bot IA (WAHA)
        participant API as ⚙️ Servidor Central (FastAPI)
        participant WS as 🛜 Serviço de Tempo Real
        participant OP as 💻 Tela do Atendente (Painel)
    end
    box rgb(255, 240, 240) Logística de Entrega
        participant APP as 🚚 Entregador (App Mobile)
    end

    %% FASE 1: O PEDIDO
    Note over C,W: 1. FASE DE ATENDIMENTO
    C->>W: Manda msg: "Quero um gás"
    W->>API: Valida e Entende (Intenção/Estoque)
    API-->>W: Prepara opções e preços
    W-->>C: Envia botões: "P13 (R$ 100) ou P20 (R$ 150)?"
    C->>W: Clica em "P13" e digita "Dinheiro, troco 150"
    W->>API: Fecha o carrinho

    %% FASE 2: ENCAMINHAMENTO
    Note over API,OP: 2. DESPACHO IMEDIATO
    API->>WS: Emite alerta (Tempo Real)
    WS-->>OP: Aparece no painel: "Novo Pedido Pendente"
    API->>OP: Operador ou Sistema Automático aprova! 
    
    API->>WS: Pedido vira "Em Preparação/Despachado"
    API->>APP: Notificação PUSH (Firebase): "Novo Pedido na sua Rota!"

    %% FASE 3: A ENTREGA
    Note over API,APP: 3. AÇÃO NA RUA (MOTORISTA)
    APP->>API: Motorista clica em "ACEITAR ENTREGA"
    API-->>W: Sistema avisa o cliente no Zap
    W-->>C: "🏍️ O João está indo! Placa ABC-1234"
    
    APP->>API: Motorista chega na casa: clica "EM ROTA"
    APP->>API: Motorista entrega: clica "CONCLUÍDO" + Tira foto
    
    %% FASE 4: CONCLUSÃO
    Note over C,APP: 4. CONCLUSÃO & FISCAL
    API-->>W: Baixa feita no sistema
    W-->>C: "✅ Pedido entregue! O Gas Automation agradece."
    API->>API: Dá baixa no estoque e no Firebird (Nota Fiscal)
    WS-->>OP: Pedido some da tela (Fechado)
```

---

### Explicando as Fases (Para Reunião):

1. **A Fricção Cai a Zero**: Sem baixar aplicativos, o cliente abre o Whats, fala do jeito dele e clica em 2 botões. Em menos de 20 segundos o pedido entra na base.
2. **O Painel é Vivo**: O atendente não dá *F5* para recarregar. Se um motoqueiro aprova no app, a cor do pedido na tela do supervisor muda no mesmo milissegundo (via WebSocket).
3. **Logística Sem Papel**: O motoboy recebe no próprio celular a coordenada GPS de onde ir sem precisar ficar mandando áudio ou errando quadra. E só continua para a próxima se a atual bater "Entregue".
4. **Fechamento Fiscal Invisível**: No segundo que o motoboy clica em *Concluído* a secretária não tem que digitar nada no fim da tarde. A integração avisa o banco de dados e fatura sozinho.
