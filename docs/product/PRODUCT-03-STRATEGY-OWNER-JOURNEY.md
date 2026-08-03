# PRODUCT-03 — Strategy Owner Journey

> **Program ID:** PRODUCT-03 = Strategy Architecture  
> **Task:** PRODUCT-03-STRATEGY-BLUEPRINT-01 · **Patch:** PRODUCT-03-STRATEGY-BLUEPRINT-PATCH-01  
> **Owns:** Owner path after Research → Strategy → Launch readiness  
> **Placement only** — no UI layout; no IA/Registry edit in this patch  
> **OD-P03:** OWNER-APPROVED · **`owner_freeze`:** **OWNER-FROZEN** (2026-08-02)  
> **Status:** **OWNER-FROZEN**

---

## 0. Current vs target path (honesty)

| Path | Flow |
|------|------|
| **Current implemented** | Research → transitional **Launch Pack / Offer (CWF)** |
| **Target (this blueprint)** | Research → owner decision → **Strategy** → Launch |

Until Strategy Runtime: do not present Strategy as live. Follow-up: `PRODUCT-03-JOURNEY-IA-DRIFT-01` after freeze.

---

## 1. Journey spine (target)

```text
Research result → owner decision → Strategy start → progress (SC-01…07)
  → review → approve / reject / edit / regenerate / revoke-override
  → Launch readiness (LaunchInputSnapshot) | mid-Launch owner choice if stale
```

**Container:** Project Command Center → Strategy panel. Not Workspace Strategy app.

---

## 2. Surfaces

Research/Partial/Verdict · Strategy panel · Review · Detail drawer · Approval · History/versions · Launch panel (later)

---

## Branch A — Full Research accepted

| Field | Value |
|-------|-------|
| CTAs | Continue to Strategy · Export Research · Pause |
| System | SIS pin + StrategyCandidate (one run may fill all SC) |
| Blocking | Missing `research_acceptance` |
| Next | Draft D |

---

## Branch B — Partial override

| Field | Value |
|-------|-------|
| CTAs | Override & start Strategy · Improve Research · Stop · later **Revoke override** |
| System | `partial_strategy_override`; `assumption_constrained=true`; accepted_risks[]; inherited gaps |
| Blocking | Auto-continue without override |
| Revoke | SIS unusable; candidate invalidated; handoff blocked; if Launch handed off → mid-Launch owner choice; history kept; resume = new Research or new override + new SIS |

---

## Branch C — Research rejected

Strategy CTAs disabled · Rerun / abandon · No SIS

---

## Branch D — Strategy draft

| Field | Value |
|-------|-------|
| CTAs | Edit section · Regenerate section · Regenerate all · Submit review |
| Rule | **Any** edit/regen → **new version** (immutable prior) |
| Manual edit | Attribution + timestamp; no-evidence → assumption; broken evidence marked |
| Next | E / F / H |

---

## Branch E — Needs clarification

| Field | Value |
|-------|-------|
| CTAs | Answer · Edit (→ new version) · Reject · Approve if cleared |
| Note | `strategy_candidate_review` ≠ Launch unlock |

---

## Branch F — Rejected

Launch blocked · Revise (new version) · Research · Abandon

---

## Branch G — Revised

New version · cascade must-refresh · Diff/history · Submit review

---

## Branch H — Approved

| Field | Value |
|-------|-------|
| CTAs | Approve Strategy (`strategy_package_approval`) · **separate** Proceed to Launch (`launch_handoff_approval`) · Export (approved only) |
| Note | Approve ≠ Launch enter |
| Export | Customer-readable + JSON; ACL tenant/project |

---

## Branch I — Stale / Research update / mid-Launch

| Field | Value |
|-------|-------|
| Labels | `stale_viewable` · `stale_launch_blocking` · `revalidated` |
| CTAs | Revise Strategy · `research_revalidation` (discouraged) · View pin diff |
| Mid-Launch | Continue Launch · Rebuild Launch · Cancel · Partial update dependents — **no auto-rewrite** |

---

## Branch J — Abandon Strategy

Cancel runs · keep artifacts · ProjectLifecycle owner decision

---

## Persisted layers

ProjectLifecycleState · CapabilityRunState (Strategy runs) · ArtifactVersionState · ApprovalRecords (`research_acceptance`, `partial_strategy_override`, `strategy_candidate_review`, `strategy_package_approval`, `budget_assumptions_acknowledgement`, `research_revalidation`, `strategy_rollback`, `launch_handoff_approval`)

---

## Alignment

Legacy `/strategy` routes ≠ Command Center. CWF Home Offer = transitional until Runtime.
