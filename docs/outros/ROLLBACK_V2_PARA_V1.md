# Rollback: V2 → V1

**Data:** 2026-02-13  
**Horário:** 20:58  
**Status:** ✅ CONCLUÍDO

---

## 🔄 Motivo do Rollback

O Flow Engine V2 apresentou múltiplos erros de incompatibilidade com o model `Customer` do banco de dados, causando falha total do bot.

**Erros encontrados:**
- `AttributeError: 'Customer' object has no attribute 'document'`
- `AttributeError: 'Customer' object has no attribute 'tipo_documento'`
- `AttributeError: 'Customer' object has no attribute 'addresses'`

**Decisão:** Rollback para V1 para restaurar operação imediata.

---

## ✅ Ações Executadas

### 1. Desativação do V2 via Feature Flags

**Arquivo:** `backend/app/core/flow_config.py`

```python
# ANTES
FEATURE_FLAGS = {
    "flow_engine_v2_enabled": True,
    ...
}
ROLLOUT_PERCENTAGE = 100

# DEPOIS
FEATURE_FLAGS = {
    "flow_engine_v2_enabled": False,  # DESATIVADO
    ...
}
ROLLOUT_PERCENTAGE = 0  # DESATIVADO
```

### 2. Restauração do Flow Engine V1

**Backup encontrado:** `backend/app/core/v1_backup_20260213_175454/flow_engine_v1.py`

```bash
# Restaurar V1 do backup
cp backend/app/core/v1_backup_20260213_175454/flow_engine_v1.py \
   backend/app/core/flow_engine.py
```

**Resultado:**
- ✅ `flow_engine.py` agora contém o código V1 original
- ✅ Wrapper V2 foi removido

### 3. Reinicialização do Backend

```bash
docker-compose restart backend
```

**Status:** ✅ Backend iniciado com sucesso usando V1

---

## 📊 Estado Atual

| Componente | Status | Versão |
|------------|--------|--------|
| Flow Engine | ✅ Ativo | **V1** |
| Feature Flag V2 | ❌ Desativado | `False` |
| Rollout Percentage | ❌ 0% | `0` |
| Backend | ✅ Rodando | V1 |

---

## 🧪 Como Testar

```bash
# 1. Verificar logs (não deve ter erro de AttributeError)
docker-compose logs backend | grep -E "ERROR|AttributeError"

# 2. Testar no WhatsApp
Enviar: "menu"
Enviar: "1"

# Deve funcionar normalmente com V1
```

---

## 📝 Próximos Passos (Quando Corrigir V2)

### Problemas a Resolver no V2:

1. **Mapeamento de Campos:**
   - `document` ↔ `cpf_cnpj`
   - `addresses` (plural) ↔ `address` (singular)

2. **Campos Inexistentes no Model:**
   - `tipo_documento` → Calcular baseado em CPF/CNPJ
   - `customer_type` → Não existe no model
   - `default_address_idx` → Não existe no model
   - `last_order_data` → Não existe no model
   - `preferences` → Não existe no model
   - `order_count` → Não existe no model

3. **Estratégia:**
   - Usar `getattr()` com fallback para campos opcionais
   - Criar campos derivados (customer_type baseado em CPF/CNPJ)
   - Converter tipos quando necessário (singular ↔ plural)

### Como Reativar V2 (Após Correções):

```bash
# 1. Editar flow_config.py
FEATURE_FLAGS = {
    "flow_engine_v2_enabled": True,
}
ROLLOUT_PERCENTAGE = 10  # Começar com 10%

# 2. Reiniciar backend
docker-compose restart backend

# 3. Monitorar logs
docker-compose logs -f backend | grep ERROR

# 4. Testar com usuários reais
# 5. Aumentar gradualmente: 10% → 25% → 50% → 100%
```

---

## 🔗 Documentos Relacionados

- `CORRECAO_ERRO_CUSTOMER_MODEL.md` - Tentativa de correção (incompleta)
- `CORRECAO_COMPLETA_MODEL_CUSTOMER.md` - Análise completa dos erros
- `CORRECAO_MENU_GREETING_RETURNING.md` - Correção do menu (aplicada mas insuficiente)
- `BUG_FIX_COMPLETE_FOLLOWUP.md` - Correção do loop (aplicada mas insuficiente)

---

## ⚠️ Lições Aprendidas

1. **Sempre testar com dados reais antes de deploy 100%**
2. **Validar schema do banco antes de desenvolver**
3. **Fazer rollout gradual (0% → 10% → 25% → 50% → 100%)**
4. **Manter backup V1 sempre disponível**
5. **Ter script de rollback automatizado**

---

## 📂 Arquivos de Backup Disponíveis

```
backend/app/core/v1_backup_20260213_175454/
├── flow_engine_v1.py      (41KB) ✅ RESTAURADO
├── handlers_v1.py         (76KB)
└── state_machine_v1.py    (12KB)
```

---

**Status Final:** ✅ SISTEMA OPERACIONAL COM V1

O bot está funcionando normalmente com Flow Engine V1.
