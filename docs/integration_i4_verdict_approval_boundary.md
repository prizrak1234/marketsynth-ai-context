# Integration I4 — Verdict approval boundary

| Decision kind | Authorizes | I4 rule |
|---------------|------------|---------|
| A. Verdict review (`draft`→`under_review`→`approved` local) | Commercial acceptance of a **preview** verdict (FE) | Does **not** create ExecutionApproval |
| B. Execution approval | Real external execute / Telegram | Untouched; never auto-created from verdict |
| C. Budget approval | Financial scope | Not in I4 |
| D. Publication approval | Package publish path | Untouched resource `/approve` |

Resource approve endpoints (plan, asset, package) remain artifact gates — **not** Business Verdict.

No polymorphic `ApprovalRequest` engine exists; do not overload ContentAsset approve for verdicts.

`verdictApprovalCreatesExecutionApproval() === false` enforced in selfcheck.
