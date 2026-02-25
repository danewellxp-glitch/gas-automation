# 🚀 GUIA DE ATIVAÇÃO - FLOW ENGINE V2
## Como ativar e testar o Flow Engine 2.0

**Data:** 13/02/2026

---

## ⚠️ IMPORTANTE - ANTES DE ATIVAR

O Flow Engine V2 está **desabilitado por padrão** para segurança.

Antes de ativar, verifique:
- ✅ Redis está rodando
- ✅ PostgreSQL está rodando
- ✅ Ollama está rodando (para NLU)
- ✅ Backend está rodando

---

## 📋 PASSO 1: Verificar Serviços

### 1.1 Verificar Redis
```bash
redis-cli ping
# Deve retornar: PONG
```

Se não estiver rodando:
```bash
# Docker
docker-compose up -d redis

# Ou local
redis-server
```

### 1.2 Verificar PostgreSQL
```bash
psql -U postgres -c "SELECT version();"
```

Se não estiver rodando:
```bash
docker-compose up -d postgres
```

### 1.3 Verificar Ollama (NLU)
```bash
curl http://localhost:11434/api/tags
```

Se não estiver rodando:
```bash
# Instalar modelo
ollama pull gemma:2b

# Verificar
ollama list
```

---

## 🔧 PASSO 2: Ativar Flow Engine V2

### Opção A: Ativação Gradual (RECOMENDADO)

Edite o arquivo: `backend/app/core/flow_config.py`

```python
# Linha 56 - Habilitar V2
FEATURE_FLAGS = {
    "flow_engine_v2_enabled": True,  # ← Mudar para True
    "fast_track_enabled": True,
    "repeat_order_enabled": True,
    # ... resto igual
}

# Linha 72 - Rollout gradual (começar com 10%)
ROLLOUT_PERCENTAGE = 10  # ← Mudar de 0 para 10
```

**Com 10%:** Apenas ~10% dos usuários usarão V2 (baseado em hash do telefone)

### Opção B: Ativação Total (TESTE)

```python
# Linha 56
FEATURE_FLAGS = {
    "flow_engine_v2_enabled": True,  # ← True
    # ... resto igual
}

# Linha 72
ROLLOUT_PERCENTAGE = 100  # ← 100 para todos os usuários
```

---

## 🔄 PASSO 3: Reiniciar Backend

### Se estiver usando Docker:
```bash
docker-compose restart backend
```

### Se estiver rodando localmente:
```bash
# Parar o processo atual (Ctrl+C)
# Depois reiniciar:
cd backend
uvicorn app.main:app --reload
```

### Verificar logs:
```bash
# Docker
docker-compose logs -f backend

# Local
# Logs aparecem no terminal
```

Procure por:
```
INFO: FlowEngineV2 inicializado com sucesso
INFO: HandlerRegistry criado com 25 handlers
INFO: MetricsCollector inicializado
INFO: Cliente Redis conectado
```

---

## 📱 PASSO 4: Testar no WhatsApp

### 4.1 Verificar qual versão está ativa

Antes de testar, você pode verificar qual versão um telefone usará:

```python
# No Python shell ou em um script
from app.core.flow_engine_factory import is_v2_enabled

phone = "5511999999999"  # Seu número de teste
print(f"V2 habilitado: {is_v2_enabled(phone)}")
```

### 4.2 Enviar mensagem de teste

Envie uma mensagem simples para o WhatsApp:

```
Olá
```

**Se V2 estiver ativo, você verá:**
```
👋 Olá! Bem-vindo(a) à *GasMaster*!

Sou o assistente virtual e vou te ajudar.

Para começar, você é:
[Pessoa Física] [Pessoa Jurídica]
```

**Se V1 ainda estiver ativo:**
```
Olá! Escolha uma opção:
1 - Fazer pedido
2 - Rastrear pedido
3 - Falar com atendente
```

### 4.3 Testar fluxo completo

Tente fazer um pedido completo:

```
1. "Olá"
2. "Pessoa Física"
3. "João Silva"
4. "P13"
5. "2"
6. "Troca"
7. "Não" (não adicionar mais)
8. "Rua das Flores, 123 - Boqueirão"
9. "Sim" (confirmar endereço)
10. "Pular" (complemento)
11. "Dinheiro"
12. "Não precisa" (troco)
13. "Confirmar"
```

---

## 🔍 PASSO 5: Monitorar Métricas

### 5.1 Endpoint de Métricas

Acesse:
```
http://localhost:8000/metrics
```

Procure por:
```
# Mensagens processadas
flow_engine_messages_total{status="success"} 10

# Tempo de processamento
flow_engine_processing_time_seconds_bucket{le="1.0"} 8

# Taxa de conclusão
flow_engine_order_completion_rate 0.85
```

### 5.2 Logs Estruturados

Procure nos logs por:
```
[trace_id] Processando mensagem
[trace_id] NLU detectou: buy (confiança: 0.95)
[trace_id] Executando handler: OrderingProductHandler
[trace_id] Transição: ordering_product → ordering_quantity
[trace_id] Processamento concluído em 150.23ms
```

---

## 🐛 TROUBLESHOOTING

### Problema 1: "Redis não configurado"

**Solução:**
1. Verificar se Redis está rodando
2. Verificar variável de ambiente `REDIS_URL`
3. Adicionar em `.env`:
```bash
REDIS_URL=redis://localhost:6379/0
```

### Problema 2: "Handler não encontrado"

**Solução:**
1. Verificar se todos os handlers foram importados
2. Reiniciar backend
3. Verificar logs de inicialização

### Problema 3: "NLU timeout"

**Solução:**
1. Verificar se Ollama está rodando
2. Verificar modelo instalado: `ollama list`
3. Aumentar timeout em `flow_config.py`:
```python
LLM_TIMEOUT_MS = 5000  # 5 segundos
```

### Problema 4: V2 não está sendo usado

**Solução:**
1. Verificar `FEATURE_FLAGS["flow_engine_v2_enabled"]` = True
2. Verificar `ROLLOUT_PERCENTAGE` > 0
3. Testar com outro telefone (hash pode estar fora do percentual)
4. Ou aumentar `ROLLOUT_PERCENTAGE` para 100

---

## 📊 PASSO 6: Aumentar Rollout Gradualmente

Após testar e validar, aumente gradualmente:

```python
# Dia 1: 10%
ROLLOUT_PERCENTAGE = 10

# Dia 2: Se tudo ok, 25%
ROLLOUT_PERCENTAGE = 25

# Dia 3: 50%
ROLLOUT_PERCENTAGE = 50

# Dia 4: 75%
ROLLOUT_PERCENTAGE = 75

# Dia 5: 100%
ROLLOUT_PERCENTAGE = 100
```

**Sempre monitorar:**
- Taxa de erro < 5%
- Tempo de resposta < 1s
- Taxa de conclusão > 70%

---

## 🔙 ROLLBACK (Se necessário)

Se algo der errado, desative rapidamente:

```python
# backend/app/core/flow_config.py

FEATURE_FLAGS = {
    "flow_engine_v2_enabled": False,  # ← Desabilitar
    # ...
}

# Ou apenas reduzir rollout
ROLLOUT_PERCENTAGE = 0  # ← Voltar para 0%
```

Depois reiniciar:
```bash
docker-compose restart backend
```

---

## ✅ CHECKLIST DE ATIVAÇÃO

- [ ] Redis rodando
- [ ] PostgreSQL rodando
- [ ] Ollama rodando com modelo gemma:2b
- [ ] Backend rodando
- [ ] `flow_engine_v2_enabled = True`
- [ ] `ROLLOUT_PERCENTAGE` definido (10-100)
- [ ] Backend reiniciado
- [ ] Logs verificados (sem erros)
- [ ] Teste manual no WhatsApp realizado
- [ ] Métricas sendo coletadas
- [ ] Fluxo completo testado

---

## 📞 TESTE RÁPIDO

Execute este script para teste rápido:

```python
# test_v2.py
import asyncio
from app.core.flow_engine_factory import get_flow_engine_v2, is_v2_enabled

async def test():
    phone = "5511999999999"
    
    # Verificar se V2 está habilitado
    print(f"V2 habilitado para {phone}: {is_v2_enabled(phone)}")
    
    # Obter engine
    engine = await get_flow_engine_v2()
    
    # Processar mensagem
    responses = await engine.process_message(phone, "Olá")
    
    # Mostrar respostas
    for i, resp in enumerate(responses):
        print(f"\nResposta {i+1}:")
        print(resp['text'])

# Executar
asyncio.run(test())
```

---

## 🎯 RESUMO

1. **Habilitar V2:** `flow_engine_v2_enabled = True`
2. **Definir Rollout:** `ROLLOUT_PERCENTAGE = 10` (ou 100 para teste)
3. **Reiniciar Backend:** `docker-compose restart backend`
4. **Testar WhatsApp:** Enviar "Olá"
5. **Monitorar:** Verificar logs e métricas
6. **Aumentar Gradualmente:** 10% → 25% → 50% → 100%

---

**Boa sorte com o teste! 🚀**

Se encontrar problemas, verifique os logs e as métricas primeiro.
