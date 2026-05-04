# ADR 0001 — Handler v1 → v2 Cutover

- **Status:** Proposed (pending CTO sign-off)
- **Date:** 2026-05-02
- **Author:** Senior Backend Engineer
- **Issue:** [MAX-23](/MAX/issues/MAX-23) — reports back to [MAX-11](/MAX/issues/MAX-11) (Architecture Health Report, Risk R-03)
- **Supersedes / supersedés:** none — first ADR in `docs/adr/`

## Context

The Architecture Health Report ([`docs/relatorios/ARCHITECTURE_HEALTH_REPORT_2026-04-30.md`](../relatorios/ARCHITECTURE_HEALTH_REPORT_2026-04-30.md)) flagged R-03 — *handler v1/v2 dual code path* — as a P1 risk. The CTO described the situation as:

> `app/core/handlers.py` is 2,163 LOC and a v2 refactor (`app/core/handlers_v2/`) is half-finished, creating a dual code path.

A close re-read of the source disagrees with that framing in one important way: **the dual code path is no longer live**. What remains is *dead but undeleted* legacy code that still imports symbols which no longer exist, and it pollutes the import graph. This ADR documents what is actually wired up, what is orphaned, and proposes a path forward.

## Audit findings (current state — 2026-05-02)

### 1. Live entrypoints into the message-handling pipeline

Every active caller of the handler pipeline goes through the `flow_engine` singleton exported from `app.core.flow_engine`:

| File | Line(s) | Caller |
|---|---|---|
| `backend/app/api/webhooks.py` | 742, 756, 799, 954, 957, 969 | WAHA webhook (production traffic) |
| `backend/app/api/test_flow.py` | 12, 47, 51, 87 | Internal test endpoint |
| `backend/app/api/admin_debug.py` | 23, 104, 107, 145, 318, 319, 331 | Admin replay / debug tooling |

All three of these import from `app.core.flow_engine`, which today is **`FlowEngineWrapper`** — a thin shim that lazy-loads `flow_engine_v2` and adapts the response shape to the legacy `(responses, context, new_state)` contract. There are **no remaining call sites** that import functions from `app.core.handlers` (the legacy 2,163-LOC file).

```bash
$ rg --no-heading 'from app\.core\.handlers ' backend/ \
    --glob '!**/v1_backup_*/**' --glob '!**/handlers_v2/**'
# (no matches)
```

The router file `backend/app/core/flow_engine_router.py` still exists and references the legacy `flow_engine`/`handlers` chain at lines 104, 185, 207, 217, but **nothing imports `flow_engine_router`** — it is also orphaned. The de facto cutover happened when `flow_engine.py` was rewritten as `FlowEngineWrapper` (commit context unclear; predates the audit window).

### 2. What `app/core/handlers.py` still defines (and why it cannot run)

The legacy file declares 23 top-level handler coroutines (2,163 LOC):

```text
handle_start, handle_awaiting_product, handle_awaiting_quantity,
handle_confirming_address, handle_awaiting_address, handle_awaiting_payment,
handle_awaiting_pix, handle_order_confirmed, handle_confirming_order,
handle_tracking_order, handle_talking_to_human, handle_greeting,
handle_asking_customer_type, handle_collecting_name, handle_collecting_document,
handle_collect_missing_data, handle_show_confirmation, handle_confirm_order,
handle_edit_order, handle_not_understood, handle_emergency,
handle_repeat_order, handle_faq
```

It opens with:

```python
# backend/app/core/handlers.py:21-22
from app.core.state_machine import ConversationState, ConversationContext
from app.core.flow_engine import MessageResponse, ProcessedMessage
```

Both `MessageResponse` and `ProcessedMessage` were removed from `app/core/flow_engine.py` when it became a v2 wrapper. **The file no longer imports cleanly** — any attempt to `from app.core.handlers import …` would now raise `ImportError`. The 2,163 LOC is unreachable code masquerading as risk.

### 3. `app/core/handlers_v2/` — module ownership and parity status

| Module | LOC | States owned (from `handler_registry.py`) | Parity status |
|---|---|---|---|
| `base.py` | 482 | (foundation) `BaseHandler`, `HandlerResult`, `MessageResponse`, NLU helpers | N/A — base class |
| `greeting_handlers.py` | 619 | `GREETING_INITIAL`, `GREETING_RETURNING` | ✅ Replaces `handle_start`, `handle_greeting` |
| `identify_handlers.py` | 801 | `IDENTIFY_TYPE`, `IDENTIFY_NAME_PF`, `IDENTIFY_NAME_PJ`, `IDENTIFY_DOCUMENT_CPF`, `IDENTIFY_DOCUMENT_CNPJ`, `IDENTIFY_UNKNOWN_PHONE`, `IDENTIFY_ASSOCIATE_PHONE` | ✅ Replaces `handle_asking_customer_type`, `handle_collecting_name`, `handle_collecting_document` (+ adds the unknown/associate-phone branch absent in v1) |
| `ordering_handlers.py` | 1,055 | `ORDERING_PRODUCT`, `ORDERING_QUANTITY`, `ORDERING_OPERATION`, `ORDERING_MORE_ITEMS`, `ORDERING_ADDRESS`, `ORDERING_ADDRESS_CONFIRM`, `ORDERING_COMPLEMENT`, `ORDERING_CONFIRM_REPEAT` | ✅ Replaces `handle_awaiting_product`, `handle_awaiting_quantity`, `handle_awaiting_address`, `handle_confirming_address`, `handle_repeat_order`, `handle_edit_order` |
| `checkout_handlers.py` | 738 | `CHECKOUT_PAYMENT`, `CHECKOUT_CHANGE`, `CHECKOUT_SUMMARY` | ✅ Replaces `handle_awaiting_payment`, `handle_awaiting_pix`, `handle_show_confirmation` |
| `complete_handlers.py` | 193 | `COMPLETE_CONFIRMED`, `COMPLETE_FOLLOWUP` | ✅ Replaces `handle_order_confirmed`, `handle_confirm_order` |
| `support_handlers.py` | 482 | `SUPPORT_HUMAN`, `SUPPORT_FAQ`, `TRACKING_STATUS`, `TRACKING_OPTIONS`, `ERROR_RECOVERY` | ✅ Replaces `handle_talking_to_human`, `handle_faq`, `handle_tracking_order`, `handle_not_understood`, `handle_emergency` |
| `__init__.py` | 87 | (re-exports) | N/A |

**Total v2 surface:** 4,457 LOC across 8 files, 25 handlers covering 25 conversation states (vs. 17 states / 23 handlers in v1). The state machine `state_machine_v2.py` is the source of truth wired into `FlowEngineV2` and the `handler_registry`.

### 4. Test coverage of v2

`backend/tests/test_handlers_v2/` contains a parallel test module per v2 handler file (`test_base_handler.py`, `test_greeting_handlers.py`, `test_identify_handlers.py`, `test_ordering_handlers.py`, `test_checkout_handlers.py`, `test_complete_handlers.py`, `test_support_handlers.py`) plus `conftest.py`. v1 tests in `tests/test_flow_engine.py` import `FlowEngine`, `MessageResponse`, `ProcessedMessage` from `app.core.flow_engine` — symbols that no longer exist; **that test file is broken at import time** and must be deleted or rewritten as part of the cutover.

### 5. Other v1 stragglers still imported by live code

`app.core.state_machine` (legacy 311-LOC enum + transitions) is still imported by:

- `backend/app/core/__init__.py:5`
- `backend/app/api/admin_debug.py:24`
- `backend/app/api/test_flow.py:118`
- `backend/scripts/diagnose_bot_state.py:26`
- `backend/tests/test_flow_engine.py:8`
- `backend/app/core/handlers.py:21` (already-dead)

The legacy enum and the v2 enum share none of the same value strings (`start`, `awaiting_product`, … vs. `greeting_initial`, `ordering_product`, …). Anything that reads the legacy enum is reading state the v2 engine never writes — these importers are reading dead state too, and `admin_debug.py` / `test_flow.py` will display stale categories in the admin UI until they are migrated.

## Decision drivers

1. **Compliance:** keeping a 2,163-LOC dead file in production source obstructs onboarding, security review, and SOC-style audits. Auditors cannot tell the dead code is dead without reading it.
2. **Drift risk:** as long as the file is in the tree, a future PR could "fix" the import error and reanimate two thousand lines of bypassed business logic.
3. **Test signal:** `tests/test_flow_engine.py` is broken at import; whatever pytest selector picks it up will fail or be silently skipped, making CI red/yellow misleading.
4. **No business value at risk:** v2 has been the only live path for an unknown-but-non-zero amount of time; rolling back to v1 is impossible (it does not import).

## Options considered

### Option A — Full cutover (delete legacy v1 files outright)

Delete `app/core/handlers.py`, `app/core/state_machine.py`, `app/core/flow_engine_router.py`, `app/core/v1_backup_20260213_175454/`, and the broken `tests/test_flow_engine.py`. Migrate `admin_debug.py`, `test_flow.py`, `scripts/diagnose_bot_state.py`, and `app/core/__init__.py` to import from `state_machine_v2`. Re-export `ConversationState` from `app/core/__init__.py` if external callers exist (none found in this repo, but `__init__.py` is a public surface).

- **Effort:** ~1.5 days (1 dev). Most of the work is migrating `admin_debug.py` and `test_flow.py` to v2 state names, which requires deciding whether to expose v2's 25 states in admin UI or collapse them to a v1-compatible projection. `state_machine.py` and `handlers.py` themselves are pure deletions.
- **Risk:** Low. Static analysis confirms zero live importers of the deleted modules. The migration of admin tooling is the only non-mechanical bit; if delayed, admin/test endpoints continue to work but display the v1 enum until updated.
- **Reversibility:** Full git history retained; recovery is `git revert`. v1 logic is also preserved untouched in `v1_backup_20260213_175454/`.

### Option B — Phased migration with deadline (e.g., delete after T+30 days)

Add a freeze annotation to the top of `handlers.py` and `state_machine.py` ("DO NOT EDIT — deletion scheduled YYYY-MM-DD; see ADR-0001"), open child issues for the admin-tooling migration, then delete on the deadline.

- **Effort:** ~0.5 day now (annotations + child issues) + ~1.5 days at T+30 to actually delete. Total ≈ 2 days, spread out.
- **Risk:** Medium. The window is exactly when "harmless" PRs have time to accidentally repair the import error or reference the legacy state enum. Deadlines also slip — Cycle 1 is already shipping on a 30-day budget.
- **Reversibility:** Same as A.

### Option C — Freeze-and-fork (move v1 to a `legacy/` subtree, keep indefinitely)

Move `handlers.py`/`state_machine.py`/`flow_engine_router.py` into `app/core/legacy/`, mark the package non-importable from production code via a `conftest.py` or `pyproject` exclusion, and leave it there as documentation.

- **Effort:** ~1 day (move + import-fence + admin migration).
- **Risk:** High *long-term*. Pays the inspection cost forever and produces nothing useful that `git log app/core/handlers.py` does not already give you. Auditors still have to read the file to confirm it is fenced. The `v1_backup_20260213_175454/` folder is *already* doing exactly this — adding a second tier of "frozen but kept" code doubles the confusion.
- **Reversibility:** N/A — this *is* the long-term state.

## Decision

**Recommend Option A — Full cutover.** The legacy code is already non-functional (`ImportError` on first reference); keeping it is pure cost. The Cycle 1 risk register also called this out as P1, and Option A is the only one that closes R-03 within the cycle.

Recommended split:

1. **PR 1 — Delete dead code (this ADR's PR or the next):**
   - Delete `app/core/handlers.py`
   - Delete `app/core/flow_engine_router.py`
   - Delete `app/core/v1_backup_20260213_175454/`
   - Delete `tests/test_flow_engine.py`
2. **PR 2 — Migrate state-enum importers to v2:**
   - Update `app/core/__init__.py` to re-export `ConversationState` from `state_machine_v2`
   - Update `app/api/admin_debug.py`, `app/api/test_flow.py`, `scripts/diagnose_bot_state.py`
   - Delete `app/core/state_machine.py` once those importers are clean
   - Add an integration test that admin debug returns the v2 enum values
3. **PR 3 — Optional follow-up** (track separately, not part of R-03 closure):
   - Promote `flow_engine.py` from a wrapper to the canonical engine and rename `flow_engine_v2.py` (cosmetic; defer until naming inconsistency causes real friction)

## Acceptance criteria

R-03 is closed when **all** of the following hold:

- [ ] `git ls-files backend/app/core/handlers.py backend/app/core/state_machine.py backend/app/core/flow_engine_router.py backend/app/core/v1_backup_20260213_175454` returns nothing
- [ ] `rg 'from app\.core\.handlers ' backend/` returns nothing
- [ ] `rg 'from app\.core\.state_machine ' backend/` returns nothing
- [ ] `pytest backend/tests -q` collects without `ImportError` on legacy modules
- [ ] `app/core/__init__.py` re-exports `ConversationState` from `state_machine_v2` (preserves external `from app.core import ConversationState` callers if any exist)
- [ ] Admin debug UI (`/admin/debug/*`) renders v2 state names (`greeting_initial`, …) without 500s

## Out of scope (explicitly)

- Splitting `app/api/financeiro.py` (1,636 LOC) — covered by R-09 in Cycle 2.
- Refactoring `flow_engine_v2.py` itself — it works; renames can wait.
- Decomposing the larger v2 handler files (`ordering_handlers.py` 1,055 LOC, `identify_handlers.py` 801 LOC). These are within v2 and replace much larger v1 surface; further breakdown is a maintainability nice-to-have, not a risk item.

## References

- Architecture Health Report — `docs/relatorios/ARCHITECTURE_HEALTH_REPORT_2026-04-30.md` (Risk R-03)
- v2 design notes — `GASMASTER_FLOW_ENGINE_2.0_COMPLETO.md` (referenced in `handler_registry.py:5`)
- Issue thread — [MAX-23](/MAX/issues/MAX-23)
