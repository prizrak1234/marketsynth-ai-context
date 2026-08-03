# P1.2 Approval and execution boundary

| Action | Triggered by handoff? |
|--------|----------------------|
| MarketingPlan draft create | yes (confirm only) |
| MarketingPlan approve | no |
| Specialist task dispatch | no |
| Agent Run | no |
| Campaign create | no |
| Execution / publication approval | no |
| Provider / budget | no |

Firewall characterization tests assert zero AgentRun / Campaign / execution-run / LLM rows after confirm.
