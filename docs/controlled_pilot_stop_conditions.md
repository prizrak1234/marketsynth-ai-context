# Controlled pilot stop conditions

Stop the pilot **immediately** if any of the following occur:

| Signal | Why |
|--------|-----|
| Cross-owner data visible or writable | Isolation failure |
| Confirmed data loss | Integrity / RPO breach |
| Backup restore drill fails or last known good backup corrupt | Recovery unsafe |
| Auth bypass or privilege escalation | Security |
| Session revoke fails (old cookie still works) | Session integrity |
| Wrong / unknown Alembic revision in use | Schema safety |
| Silent mock fallback on commercial path | Misleading product |
| MarketingPlan approved or specialists dispatched unexpectedly | Execution firewall |
| Agent Run / Campaign / LLM / publication / budget side effect from pilot path | Firewall |
| Secrets in logs, UI, or client bundle | Security |
| Persistent login/session failures for pilot users | Availability / trust |
| Severely misleading Verdict without evidence trace | Product honesty |

Operator actions on stop:

1. Revoke all browser sessions for pilot users.
2. Set backend to not-ready / stop accepting logins if needed.
3. Preserve database; do not stamp/migrate ad-hoc.
4. Record incident with correlation IDs and timestamps.
5. Escalate to owner before any resume.
