## Phase AI.16.1 — Programmer domain readiness audit (freeze)

This audit **freezes** the Programmer specialist path (Phase AI.16). Programmer is a **safe consultant / technical spec architect** only — not a code-changing or external-system agent.

**Not in this freeze:** GitHub integration, repository access, file writes, shell, deploy pipelines, live Telegram bot creation, secrets management, or Media/Tilda/Email domains.

---

## General routing (frozen)

| Domain | Behavior |
|--------|----------|
| **marketing** | Delegate to Marketer orchestrator (AI.14 chains unchanged) |
| **programmer** | Delegate to Programmer child run (consultation) |
| **unknown** | Clarification text, **no** specialist child run |

Router (`app/agents/general/router.py`):

- Programmer-priority phrases (`telegram bot`, …) run **before** marketing `telegram` match.
- Broad programmer phrases: `api`, `скрипт`, `webhook`, `tilda`, `код`, …

---

## Programmer role (frozen)

| Rule | Status |
|------|--------|
| Child `AgentRun` under General | **Required** (depth **1**) |
| Programmer spawns children | **Forbidden** |
| Tool allowlist | **Empty** |
| Changes project source code | **Forbidden** |
| Shell / GitHub / filesystem / deploy | **Forbidden** |
| External network execution | **Forbidden** |
| Secrets access | **Forbidden** |
| Live Telegram bot provisioning | **Forbidden** |

Programmer may:

- Explain approaches in LLM reply text.
- Propose plans and pseudocode in the response.
- Attach an in-memory **`technical_task_draft`** object on the run `output_payload`.

---

## AgentRun hierarchy under General

| Depth | Run |
|-------|-----|
| **0** | General parent |
| **1** | Programmer child (`source` = `general_delegation`, `delegated_domain` = `programmer`) |

Programmer path does **not** create marketer subagent runs. `count_children(programmer_run_id) == 0` after delegation.

`AgentRunService` rejects `create_run(..., parent_agent_run_id=programmer_run.id)` with **Programmer runs cannot spawn child runs**.

---

## Output contract (frozen)

After successful Programmer execution, `output_payload` may include:

```json
{
  "programmer_mode": "consultation",
  "technical_task_draft": {
    "kind": "technical_task_draft",
    "title": "Technical task draft (consultation)",
    "summary": "...",
    "scope": "...",
    "deliverables": ["..."],
    "assistant_excerpt": "...",
    "persisted": false
  }
}
```

| Field | Rule |
|-------|------|
| `technical_task_draft.persisted` | **Must be** `false` (no DB persistence in AI.16) |
| Write tools on run | **None** |

Built in `app/agents/programmer/execution.py` — `build_technical_task_draft()` / `merge_programmer_output_payload()`.

---

## Chat API

| Field | Programmer path |
|-------|-----------------|
| `general_delegation.domain` | `"programmer"` |
| `general_delegation.agent_run_id` | Programmer child run id |
| `subagent_chain` | **null** / absent |

Direct orchestrator chat: no `general_delegation` (unchanged).

---

## UI

`GeneralDelegationPanel` uses domain-generic labels:

- `marketing` → “Delegated to Marketer”
- `programmer` → “Delegated to Programmer”
- Link text: “Specialist run” (not orchestrator-only)

---

## Freeze checklist

```bash
uv run pytest tests/test_general_programmer_domain.py
uv run pytest tests/test_phase_ai_16_programmer_domain_invariants.py
```

**Next phases (not here):** GitHub/repo/file-write agent with separate security model; Media domain skeleton.
