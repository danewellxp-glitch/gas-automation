# 🔄 MIGRAÇÃO COMPLETA V1 → V2
## Substituição Total do Flow Engine

**Objetivo:** Remover V1 completamente e usar apenas V2

---

## 📋 PLANO DE MIGRAÇÃO

### Opção A: Migração Direta (RECOMENDADO)
Substituir o arquivo `flow_engine.py` atual pelo novo sistema V2.

### Opção B: Backup e Substituição
Fazer backup do V1 e ativar V2 como padrão.

---

## 🎯 PASSOS DA MIGRAÇÃO

### 1. Fazer Backup do V1 (Segurança)

```bash
# Backup do flow engine antigo
mv backend/app/core/flow_engine.py backend/app/core/flow_engine_v1_backup.py

# Backup dos handlers antigos
mv backend/app/core/handlers.py backend/app/core/handlers_v1_backup.py

# Backup da state machine antiga
mv backend/app/core/state_machine.py backend/app/core/state_machine_v1_backup.py
```

### 2. Criar Novo flow_engine.py (Wrapper para V2)

O novo `flow_engine.py` será um wrapper simples que usa o V2:

```python
"""
Flow Engine - Sistema de Conversação V2
Este arquivo substitui completamente o V1.
"""

from app.core.flow_engine_v2 import FlowEngineV2
from app.core.flow_engine_factory import get_flow_engine_v2
from app.core.handler_registry import get_handler_registry
from app.core.context_manager import ContextManager

# Singleton global
_engine_instance = None

async def get_flow_engine():
    """Obtém instância do Flow Engine V2."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = await get_flow_engine_v2()
    return _engine_instance

# Alias para compatibilidade
flow_engine = get_flow_engine()
```

### 3. Atualizar Webhooks

O webhook já está atualizado para usar o router, mas vamos simplificar:

```python
# backend/app/api/webhooks.py
# Linha ~706

# ANTES (V1):
from app.core.flow_engine import flow_engine

# DEPOIS (V2):
from app.core.flow_engine_v2 import FlowEngineV2
from app.core.flow_engine_factory import get_flow_engine_v2

# No início do handler:
engine = await get_flow_engine_v2()
result = await engine.process_message(phone, message, trace_id=trace_id)
```

### 4. Adaptar Formato de Resposta

O V2 retorna formato diferente, precisamos adaptar:

```python
# V2 retorna: List[Dict] com {type, text, buttons, media_url}
# V1 espera: objeto com .responses e .success

class V2ResponseAdapter:
    def __init__(self, responses):
        self.responses = [
            {
                "type": r.get("type", "text"),
                "content": r.get("text", ""),
                "buttons": r.get("buttons"),
            }
            for r in responses
        ]
        self.success = True
```

---

## 🔧 ARQUIVOS A MODIFICAR

### 1. backend/app/core/flow_engine.py
**Ação:** Substituir completamente

**Novo conteúdo:**
```python
"""
Flow Engine V2 - Sistema de Conversação
Substitui completamente o Flow Engine V1.
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class FlowEngineWrapper:
    """
    Wrapper que expõe interface compatível com V1
    mas usa V2 internamente.
    """
    
    def __init__(self):
        self._v2_engine = None
    
    async def _get_v2_engine(self):
        """Lazy load do V2 engine."""
        if self._v2_engine is None:
            from app.core.flow_engine_factory import get_flow_engine_v2
            self._v2_engine = await get_flow_engine_v2()
        return self._v2_engine
    
    async def process_message(
        self,
        phone: str,
        message: str,
        message_id: Optional[str] = None,
        waha_chat_id: Optional[str] = None,
    ):
        """Processa mensagem (interface compatível com V1)."""
        engine = await self._get_v2_engine()
        
        # Processar com V2
        responses = await engine.process_message(
            phone=phone,
            message=message,
            trace_id=message_id,
        )
        
        # Converter para formato V1
        return self._adapt_response(responses)
    
    def _adapt_response(self, v2_responses: List[Dict]):
        """Adapta resposta V2 para formato V1."""
        class V1Response:
            def __init__(self, responses):
                self.responses = []
                for r in responses:
                    self.responses.append({
                        "type": r.get("type", "text"),
                        "content": r.get("text", ""),
                        "buttons": r.get("buttons"),
                        "media_url": r.get("media_url"),
                    })
                self.success = True
        
        return V1Response(v2_responses)
    
    async def send_responses(
        self,
        phone: str,
        responses: List[Dict],
        trace_id: Optional[str] = None,
    ):
        """Envia respostas via WAHA."""
        from app.integrations.waha import waha_client
        
        results = {"sent": 0, "failed": 0}
        
        for response in responses:
            try:
                content = response.get("content") or response.get("text", "")
                buttons = response.get("buttons")
                
                if buttons:
                    await waha_client.send_buttons(phone, content, buttons)
                else:
                    await waha_client.send_text(phone, content)
                
                results["sent"] += 1
            except Exception as e:
                logger.error(f"Erro ao enviar resposta: {e}")
                results["failed"] += 1
        
        return results
    
    async def get_context(self, phone: str):
        """Obtém contexto (compatibilidade V1)."""
        engine = await self._get_v2_engine()
        # V2 usa ContextManager internamente
        # Retornar None para compatibilidade
        return None
    
    async def save_context(self, context):
        """Salva contexto (compatibilidade V1)."""
        # V2 gerencia contextos automaticamente
        pass


# Singleton global
flow_engine = FlowEngineWrapper()
```

### 2. backend/app/api/webhooks.py
**Ação:** Manter import simples

```python
# Linha ~706
from app.core.flow_engine import flow_engine

# Usar normalmente (wrapper cuida da conversão)
result = await flow_engine.process_message(
    phone=phone,
    message=content,
    message_id=message_id,
    waha_chat_id=original_chat_id,
)
```

---

## ✅ CHECKLIST DE MIGRAÇÃO

- [ ] Fazer backup dos arquivos V1
- [ ] Criar novo `flow_engine.py` (wrapper)
- [ ] Verificar que `flow_config.py` tem V2 habilitado
- [ ] Remover imports de V1 em outros arquivos
- [ ] Testar webhook com mensagem simples
- [ ] Testar fluxo completo de pedido
- [ ] Monitorar logs por 24h
- [ ] Remover backups após confirmação

---

## 🚀 SCRIPT DE MIGRAÇÃO AUTOMÁTICA

Criei um script que faz tudo automaticamente:

```bash
./migrar_para_v2.sh
```

---

## 🔙 ROLLBACK (Se necessário)

Se algo der errado, restaurar V1:

```bash
./rollback_para_v1.sh
```

---

## 📊 VANTAGENS DA MIGRAÇÃO COMPLETA

✅ **Código mais limpo** - Sem duplicidade  
✅ **Manutenção mais fácil** - Apenas uma versão  
✅ **Performance melhor** - Sem overhead de routing  
✅ **Menos confusão** - Time trabalha em uma versão só  
✅ **Evolução mais rápida** - Foco em V2  

---

## ⚠️ IMPORTANTE

Após a migração:
1. **Monitorar logs** por 24-48h
2. **Verificar métricas** (taxa de erro, tempo de resposta)
3. **Testar todos os fluxos** manualmente
4. **Manter backup V1** por 1 semana
5. **Documentar mudanças** para o time

---

**Pronto para migrar?** Execute: `./migrar_para_v2.sh`
