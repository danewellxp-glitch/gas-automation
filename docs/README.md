# 📁 Documentação Organizada

Esta pasta contém toda a documentação do projeto organizada automaticamente por categoria.

## 🗂️ Estrutura de Pastas

- **`relatorios/`** - Relatórios, análises, diagnósticos, auditorias, estatísticas
- **`resumos/`** - Resumos executivos, conclusões, sumários, análises finais
- **`checklists/`** - Checklists, listas de verificação
- **`planos/`** - Planos, planejamentos, sprints, fases, roadmaps
- **`guias/`** - Guias, tutoriais, instruções, quick references
- **`correcoes/`** - Correções, soluções de problemas, fixes, bugs resolvidos
- **`migracoes/`** - Migrações, conversões, adaptações de código
- **`arquitetura/`** - Arquitetura, schemas, mapas, diagramas, estruturas
- **`testes/`** - Testes, debug, validações
- **`scripts/`** - Scripts, utilitários, ferramentas
- **`configuracao/`** - Configurações, setup, deploy, docker
- **`outros/`** - Outros documentos não classificados automaticamente

## 🤖 Automação

Os documentos são organizados automaticamente:

1. **Git Hook**: Após cada commit que inclui arquivos `.md` ou `.txt`, o sistema organiza automaticamente
2. **Manual**: Execute `python3 organize_docs.py` na raiz do projeto
3. **Script**: Execute `./auto_organize.sh` para organização rápida

## 📝 Como Funciona

O sistema classifica arquivos baseado em palavras-chave no nome do arquivo:

- Arquivos com "relatorio", "analise", "auditoria" → `relatorios/`
- Arquivos com "resumo", "sumario", "conclusao" → `resumos/`
- Arquivos com "plano", "sprint", "fase" → `planos/`
- E assim por diante...

## ⚙️ Configuração

Para ajustar a classificação, edite o arquivo `organize_docs.py` na raiz do projeto e modifique o dicionário `CATEGORY_KEYWORDS`.

## 📌 Arquivos que Permanecem na Raiz

Os seguintes arquivos **não** são movidos automaticamente:
- `README.md`
- `.gitignore`
- `.env.example`
- `docker-compose.yml`

## 🔄 Reorganizar

Se precisar reorganizar todos os documentos novamente:

```bash
# Ver o que seria feito (sem alterar nada)
python3 organize_docs.py --dry-run

# Executar a organização
python3 organize_docs.py

# Modo silencioso
python3 organize_docs.py --quiet
```
