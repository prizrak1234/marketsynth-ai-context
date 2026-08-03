# CPH.1 — Investigation: Alembic revision `20260608_0033`

## Question

Why does local PostgreSQL `botfazer` report `alembic_version = 20260608_0033` while the code tree head is `20260614_0036` and **no file** defines `20260608_0033`?

## Classification (evidence-based)

**Primary class: D — orphaned / malformed revision relative to the current tree**  
**Secondary class: A — effects of deleted (never-committed) migrations remain in the DB**  
**Not:** E (cannot reconstruct exact original migration file from local git)  
**Not** silently stampable to `20260614_0036`.

Confidence: **high** that this is **not** commercial `20260614_0033` (BusinessVerdict).

## Evidence table

| Finding | Evidence | Confidence | Consequence |
|---------|----------|------------|-------------|
| Revision ID absent from code | `list_code_revisions()` / `alembic/versions/*.py` — no `20260608_0033`; `assert` in CPH.1 tests | High | `database_revision_missing_from_tree` |
| `alembic current` fails | `Can't locate revision identified by '20260608_0033'` | High | Cannot upgrade/downgrade this DB with current tree |
| Commercial tables missing on `botfazer` | Inventory: no `project_briefs`, `investigations`, …, `implementation_*` | High | DB is **not** at Commercial MVP schema |
| AI.60x / ops tables present | `campaign_learnings`, `project_insights`, `project_decisions`, `project_goals`, `decision_outcome_evidence`, `execution_approvals`, `workflow_execution_runs`, campaign report snapshots | High | Schema path diverged via Strategic Memory / workforce WIP |
| Date prefix `20260608` vs commercial `20260614` | Commercial chain files are `20260614_0029`…`0036`; git commit `4c3de96` added `20260614_0033` (BusinessVerdict), not `20260608_0033` | High | Different lineage |
| Missing migration files never in freeze commits | Conversation/git status earlier showed untracked `20260608_003*_phase_ai_60*.py`; not in `b1cade2` tree | Medium–High | Likely stamped/applied from local WIP then files removed |
| Local git cannot restore exact script | `git log -- "**/20260608_0033*"` empty for that ID | High | Option E (restore exact migration) **blocked** |
| Backup restore reproduces state | Restore to `botfazer_cph1_restore` → revision `20260608_0033`, `campaign_learnings=true`, `project_briefs=false` | High | Backup faithful; problem is real schema drift |
| Clean tree upgrade reaches head | Fresh `botfazer_cph1` → `upgrade head` → `20260614_0036` + all commercial tables | High | Problem is **this DB's history**, not inability to bootstrap PG |

## Ruled out / not claimed

| Claim | Status |
|-------|--------|
| Same as `20260614_0033` BusinessVerdict | **False** (different ID; different schema effects) |
| Exact original migration recoverable from local history | **Not proven** → Option E unavailable |
| Safe to `alembic stamp head` | **Forbidden** — would lie about schema parity |
| From remote-only branch | Not investigated (no remote ops in CPH.1); not required for conclusion |

## Error code

`database_revision_missing_from_tree`

## Recommended next action

Do **not** mutate `botfazer` Alembic metadata. Use disposable `botfazer_cph1` for Commercial MVP / pilot. Owner-approved rebuild of local data DB only after backup (see reconciliation plan).
