# CPH.2 — Execution firewall

After happy-path browser run assert:

| Forbidden | Check |
|-----------|--------|
| MarketingPlan approval | API list statuses — only `draft` |
| Duplicate draft from idempotent confirm | draft count not exploding |
| Agent Run | `GET /agent-runs` count unchanged (soft) |
| Campaign / publication / LLM / budget | Not invoked by handoff adapters; backend P1.3 unit firewall remains SoT |
| Provider / n8n / Telegram publish | Flags off; UI path never calls them |

Handoff adapters call only marketing-plan draft handoff preview/confirm endpoints.

If any forbidden side effect is observed, treat as CPH.2 failure and stop before CPH.3.
