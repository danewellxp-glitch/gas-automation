# 📁 Sistema de Organização Automática de Documentos

Este sistema organiza automaticamente todos os arquivos `.md` e `.txt` criados pelo chat em pastas categorizadas.

## ✅ O que foi implementado

1. **Script Python** (`organize_docs.py`) - Classifica e organiza documentos
2. **Git Hook** (`.git/hooks/post-commit`) - Organiza automaticamente após commits
3. **Estrutura de Pastas** (`docs/`) - 12 categorias organizadas
4. **102 arquivos organizados** - Todos os documentos existentes foram movidos

## 🚀 Como usar

### Organização Manual

```bash
# Ver o que seria feito (sem alterar nada)
python3 organize_docs.py --dry-run

# Organizar todos os documentos
python3 organize_docs.py

# Modo silencioso (apenas estatísticas)
python3 organize_docs.py --quiet
```

### Organização Automática

O sistema já está configurado para organizar automaticamente:

1. **Git Hook**: Após cada commit que inclui arquivos `.md` ou `.txt`, os documentos são organizados automaticamente
2. **Manual**: Execute `python3 organize_docs.py` quando quiser reorganizar

## 📂 Estrutura de Pastas

```
docs/
├── relatorios/      # Relatórios, análises, diagnósticos, auditorias
├── resumos/         # Resumos executivos, conclusões, sumários
├── checklists/      # Checklists, listas de verificação
├── planos/          # Planos, planejamentos, sprints, fases
├── guias/           # Guias, tutoriais, instruções
├── correcoes/       # Correções, soluções de problemas, fixes
├── migracoes/       # Migrações, conversões, adaptações
├── arquitetura/     # Arquitetura, schemas, mapas, diagramas
├── testes/          # Testes, debug, validações
├── scripts/         # Scripts, utilitários, ferramentas
├── configuracao/    # Configurações, setup, deploy
└── outros/          # Outros documentos não classificados
```

## 🎯 Classificação Automática

O sistema classifica arquivos baseado em palavras-chave no nome:

| Palavra-chave | Categoria |
|--------------|-----------|
| relatorio, analise, auditoria, diagnostico | `relatorios/` |
| resumo, sumario, conclusao, executivo | `resumos/` |
| checklist, lista, verificacao | `checklists/` |
| plano, sprint, fase, roadmap | `planos/` |
| guia, tutorial, instrucoes | `guias/` |
| correcao, fix, solucao, problema | `correcoes/` |
| migracao, migration, conversao | `migracoes/` |
| arquitetura, schema, mapa, diagrama | `arquitetura/` |
| teste, test, debug | `testes/` |
| script, create, generate | `scripts/` |
| config, setup, deploy | `configuracao/` |

## 📌 Arquivos que Permanecem na Raiz

Estes arquivos **não** são movidos automaticamente:
- `README.md`
- `.gitignore`
- `.env.example`
- `docker-compose.yml`

## 🔧 Personalização

Para ajustar a classificação, edite `organize_docs.py`:

```python
CATEGORY_KEYWORDS = {
    "sua_categoria": ["palavra1", "palavra2", ...],
    ...
}
```

## 📊 Estatísticas da Organização

- **Total organizado**: 102 arquivos
- **Por categoria**:
  - Resumos: 22
  - Planos: 17
  - Relatórios: 13
  - Outros: 24
  - Correções: 6
  - Migrações: 5
  - Arquitetura: 5
  - Checklists: 4
  - Guias: 3
  - Testes: 3

## ⚠️ Notas Importantes

1. O script **não sobrescreve** arquivos duplicados - adiciona timestamp ao nome
2. Arquivos já organizados não são movidos novamente
3. O git hook só executa se houver arquivos `.md` ou `.txt` no commit
4. Pastas `backend/`, `frontend/`, `docs/` são ignoradas automaticamente

## 🐛 Troubleshooting

### Script não executa
```bash
chmod +x organize_docs.py
python3 organize_docs.py
```

### Git hook não funciona
```bash
chmod +x .git/hooks/post-commit
```

### Reorganizar tudo novamente
```bash
# Mover arquivos de volta para a raiz (se necessário)
# Depois execute:
python3 organize_docs.py
```

## 📝 Exemplo de Uso

1. Chat cria `RELATORIO_VARREDURA_SISTEMA.md` na raiz
2. Você faz commit: `git add . && git commit -m "Add relatório"`
3. Git hook detecta arquivo `.md` no commit
4. Script organiza automaticamente → `docs/relatorios/RELATORIO_VARREDURA_SISTEMA.md`
5. Pronto! Documento organizado ✅

---

**Criado em**: 23 de Janeiro de 2026  
**Versão**: 1.0
