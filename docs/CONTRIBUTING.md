# Guia de Contribuição — GasMaster / MercuryGas

Este documento define o fluxo oficial de branches, pull requests e releases
para o repositório `gas-automation`. Qualquer contribuição (humana ou via
agente) deve seguir este fluxo.

Origem da política: relatório `docs/relatorios/ARCHITECTURE_HEALTH_REPORT_2026-04-30.md`,
§4 Cycle 1, Riscos R-04 e R-07. Issue de implementação: MAX-21.

---

## 1. Modelo de branches

```
feature/*  ──► develop  ──►  release tag  ──►  main
fix/*           ▲                                 ▲
chore/*         │                                 │
                │         (apenas via PR)         │
```

| Branch     | Papel                                                        |
|------------|--------------------------------------------------------------|
| `main`     | Apenas código publicado em produção. Protegida.              |
| `develop`  | Branch padrão. Integração contínua de novas features.        |
| `feature/<slug>` | Desenvolvimento de feature; ramificada de `develop`.   |
| `fix/<slug>`     | Correção de bug; ramificada de `develop`.              |
| `chore/<slug>`   | Tarefa de manutenção/infra; ramificada de `develop`.   |
| `hotfix/<slug>`  | Correção crítica em produção; ramificada de `main`,    |
|                  | aplicada em `main` E `develop`.                        |

Convenção do nome do branch: prefixo + identificador da issue Paperclip.
Exemplos: `feature/MAX-42-pix-reconciliation`, `fix/MAX-77-nfe-timeout`,
`chore/MAX-21-branching-policy`.

---

## 2. Fluxo de trabalho

1. **Crie a branch a partir de `develop`** (não de `main`):

   ```bash
   git fetch origin
   git checkout -b feature/MAX-XX-descricao origin/develop
   ```

2. **Commit e push**. Use mensagens descritivas em inglês ou português,
   referenciando a issue: `MAX-XX: short summary`.

3. **Abra Pull Request com destino `develop`** (não `main`).

4. **Code review obrigatório**: pelo menos 1 aprovação antes do merge.
   O reviewer deve ser diferente do autor.

5. **Merge para `develop`** assim que: review aprovado + checks verdes +
   conversas resolvidas. Estratégia preferida: `Squash and merge`
   (mantém histórico linear em `develop`).

6. **Promoção para `main` (release)**:
   - Acumule features em `develop` até atingir um marco de release.
   - Crie PR `develop` → `main` com changelog do release.
   - Após merge, crie tag `vX.Y.Z` em `main` (`git tag -a vX.Y.Z -m "..."`).
   - `git push origin vX.Y.Z`.

7. **Hotfix em produção**:
   - Branch `hotfix/MAX-XX` a partir de `main`.
   - PR para `main` (review + checks).
   - Após merge: tag de patch (`v1.2.4`) e PR de back-merge para `develop`.

---

## 3. Regras automáticas em `main`

Configuradas via Branch Protection Rules:

- ✅ Apenas merge via Pull Request.
- ✅ ≥ 1 review aprovada antes do merge.
- ✅ Reviews aprovadas são invalidadas se houver novo push (`dismiss_stale_reviews`).
- ✅ Conversas no PR devem ser resolvidas antes do merge.
- 🔜 Status checks de CI obrigatórios — habilitado quando MAX-20 entregar
  o workflow do GitHub Actions (backend `pytest`/`ruff`/`mypy`,
  frontend `vitest`/`vite build`/ESLint).
- ❌ Push direto bloqueado.
- ❌ Force push bloqueado.
- ❌ Deleção da branch bloqueada.
- Administradores podem temporariamente burlar a proteção (`enforce_admins=false`)
  durante a transição para esta política. Será endurecido após MAX-20.

---

## 4. O que NÃO fazer

- ❌ Commit direto em `main`.
- ❌ Commit direto em `develop` (sempre via PR).
- ❌ Force push em `main` ou `develop`.
- ❌ Mesclar PRs sem review.
- ❌ Deixar branches `feature/*` órfãs por mais de 30 dias sem rebase
  contra `develop` — risco de divergência irreversível.
- ❌ Subir tokens, credenciais, certificados ou `.env` no commit.
  Use `.env.example` como referência.

---

## 5. Higiene de branches

- Após o merge do PR, **delete a branch remota** (botão "Delete branch"
  no GitHub) para manter o repositório limpo.
- Branches stale serão arquivadas trimestralmente: `git tag archive/<branch>-<YYYYMMDD>`
  preservando o conteúdo, depois deletadas do remoto.
- Histórico de branches arquivadas: ver tags com prefixo `archive/`.

---

## 6. Mensagens de commit

Convenção recomendada (não obrigatória, mas preferida):

```
<tipo>(<escopo opcional>): <descrição curta>

<corpo opcional explicando o porquê>

Refs: MAX-XX
```

Tipos: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.

---

## 7. Rebase vs. Merge

- Branch de feature contra `develop`: prefira `git rebase origin/develop`
  para manter histórico linear ANTES de abrir o PR.
- Após o PR aberto e em review, evite force-push: use `merge` ou peça
  ao reviewer para aceitar `Squash and merge`.

---

## 8. Quem aprova o quê

| Tipo de mudança                     | Reviewer mínimo                          |
|-------------------------------------|------------------------------------------|
| Backend (`backend/**`)              | Senior Backend Engineer ou CTO           |
| Frontend (`frontend/**`)            | Pleno Full-Stack ou CTO                  |
| Migrations (`backend/alembic/**`)   | Senior Backend Engineer (obrigatório)    |
| Infra/CI (`.github/**`, Dockerfile) | CTO                                      |
| Documentação (`docs/**`)            | Qualquer engenheiro                      |

---

## 9. Dúvidas

Abra issue na board com label `question` e mencione `@CTO`.
