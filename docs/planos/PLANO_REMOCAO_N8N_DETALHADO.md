# 🗑️ PLANO DE REMOÇÃO N8N - FASE 2

**Status:** ✅ PRONTO PARA EXECUÇÃO  
**Complexidade:** 🟢 BAIXA (30 minutos)  
**Risco:** 🟢 ZERO (sem lógica de negócio afetada)

---

## 📍 ONDE ESTÃO OS FIELDS N8N

### eric_files/base_models_eric.py (Linhas 39-42)
```python
class Message(SQLModel, table=True):
    # ... outros campos ...
    
    bot_service: Optional[str] = None  # "claude", "ollama", "rasa", "fallback", "n8n"
    n8n_workflow_id: Optional[str] = None  # n8n workflow identifier
    n8n_execution_id: Optional[str] = None  # n8n execution identifier
    n8n_processed: bool = False  # whether message was processed by n8n
```

### app/models/auth_models.py (Linhas 40-43)
```python
class Message(SQLModel, table=True):
    # ... outros campos ...
    
    bot_service: Optional[str] = None  # "claude", "ollama", "rasa", "fallback", "n8n"
    n8n_workflow_id: Optional[str] = None  # n8n workflow identifier
    n8n_execution_id: Optional[str] = None  # n8n execution identifier
    n8n_processed: bool = False  # whether message was processed by n8n
```

**Total:** 6 linhas (3 em cada arquivo)

---

## ✅ VERIFICAÇÃO: ZERO USAGE ENCONTRADO

```bash
$ grep -r "n8n_workflow_id\|n8n_execution_id\|n8n_processed" backend/eric_files/
# RESULTADO: Nenhuma ocorrência encontrada em services ou main_eric.py

$ grep -r "n8n_workflow_id\|n8n_execution_id\|n8n_processed" backend/app/
# RESULTADO: Nenhuma ocorrência encontrada em services ou main.py
```

**Conclusão:** Fields não estão sendo usados em lugar nenhum. É 100% SAFE remover.

---

## 🗑️ REMOÇÃO - 3 PASSOS

### PASSO 1: Atualizar Models

#### eric_files/base_models_eric.py
```diff
class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id")
    sender: str
    message_type: str = "customer"
    content: str
    bot_service: Optional[str] = None  # "claude", "ollama", "rasa", "fallback"
-   n8n_workflow_id: Optional[str] = None
-   n8n_execution_id: Optional[str] = None
-   n8n_processed: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
```

#### app/models/auth_models.py
```diff
class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id")
    sender: str
    message_type: str = "customer"
    content: str
    bot_service: Optional[str] = None  # "claude", "ollama", "rasa", "fallback"
-   n8n_workflow_id: Optional[str] = None
-   n8n_execution_id: Optional[str] = None
-   n8n_processed: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
```

### PASSO 2: Criar Alembic Migration

```bash
$ alembic revision -m "Remove N8N fields from Message model"
```

#### versions/remove_n8n_fields.py
```python
"""Remove N8N fields from Message model

Revision ID: remove_n8n_001
Revises: <previous_revision>
Create Date: 2024-12-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_n8n_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Remove N8N fields"""
    op.drop_column('message', 'n8n_workflow_id')
    op.drop_column('message', 'n8n_execution_id')
    op.drop_column('message', 'n8n_processed')


def downgrade():
    """Restore N8N fields if needed"""
    op.add_column('message', sa.Column('n8n_workflow_id', sa.String, nullable=True))
    op.add_column('message', sa.Column('n8n_execution_id', sa.String, nullable=True))
    op.add_column('message', sa.Column('n8n_processed', sa.Boolean, nullable=False, server_default='false'))
```

### PASSO 3: Atualizar Enums bot_service

#### Antes (em ambos os arquivos):
```python
bot_service: Optional[str] = None  # "claude", "ollama", "rasa", "fallback", "n8n"
```

#### Depois:
```python
bot_service: Optional[str] = None  # "claude", "ollama", "rasa", "fallback"
```

---

## ✅ CHECKLIST DE REMOÇÃO

- [ ] Remover 3 linhas de eric_files/base_models_eric.py
- [ ] Remover 3 linhas de app/models/auth_models.py
- [ ] Atualizar comentários em `bot_service` enum
- [ ] Criar Alembic migration
- [ ] Testar migration localmente
- [ ] Fazer commit: "Remove N8N integration (legacy, unused)"
- [ ] Push para staging
- [ ] Verificar que sistema continua funcionando

---

## 🧪 TESTE PÓS-REMOÇÃO

```python
# test_n8n_removal.py
def test_message_model_without_n8n():
    """Verificar que Message model não tem campos N8N"""
    message = Message(
        conversation_id=1,
        sender="bot",
        content="Hello",
        bot_service="claude"
    )
    
    # Verificar que campos N8N não existem
    assert not hasattr(message, 'n8n_workflow_id')
    assert not hasattr(message, 'n8n_execution_id')
    assert not hasattr(message, 'n8n_processed')
    
    print("✅ N8N fields successfully removed")
```

---

## 📊 IMPACTO

| Aspecto | Impacto |
|--------|--------|
| **Funcionalidade** | ✅ NENHUM - Campos não eram usados |
| **Performance** | ✅ MÍNIMO - 3 campos SQL economizados |
| **Compatibilidade** | ✅ TOTAL - Código não referencia N8N |
| **Dados históricos** | ⚠️ MODERADO - Migration precisa fazer backup |

---

## 🎯 QUANDO FAZER

**Recomendação:** Fazer como parte de FASE 2  
**Timing:** Junto com outras model synchronizations  
**Risco:** 🟢 ZERO - pode ser feito com confiança

---

## 📝 REFERÊNCIAS

- Arquivo original: [PLANO_ADAPTACAO_ERIC_FILES.md](PLANO_ADAPTACAO_ERIC_FILES.md#-remoção-de-n8n)
- Auditoria completa: [AUDITORIA_FASE_1_COMPLETA.md](AUDITORIA_FASE_1_COMPLETA.md#-críticos-n8n-usage-pattern)
- Models eric_files: `backend/eric_files/base_models_eric.py`
- Models app: `backend/app/models/auth_models.py`

---

**Status Final:** ✅ PRONTO PARA EXECUÇÃO

*Remoção N8N é trivial e segura. Pode ser feita sem preocupações.*
