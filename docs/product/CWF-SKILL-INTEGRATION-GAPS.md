# CWF–Skill Integration Gaps

**Audit:** PRODUCT-00

## CWF documentation inventory

| Document | Path | Status |
|----------|------|--------|
| CWF.1a Intent Entry UX | `docs/product/CWF.1a-intent-entry-ux.md` | ✅ On disk, implemented (routing) |
| CWF.1 canonical spec | — | ❌ **No standalone RFC** — implied by code/i18n only |
| Launch Pack decision | `app/commercial_workflow/decision_branch.py` | ✅ Implemented |
| Launch Pack service | `app/services/launch_pack_service.py` | ✅ Request persistence |
| BIV | `app/business_idea_validation/` | ✅ Full runtime |

---

## CWF.1 promised vs delivered

| Launch Pack included item (i18n key) | Skill package | Runtime | UI artifact |
|--------------------------------------|---------------|---------|-------------|
| Audience | icp_segmentation | ❌ | ❌ |
| Positioning | positioning | ❌ | ❌ |
| **Offer** | **offer_builder** | ✅ PRODUCT-01 runtime | ✅ review UI |
| Launch plan | launch_strategy (deferred) | ❌ | ❌ |
| 3 Telegram posts | copywriting (deferred) | ❌ | ❌ |
| Visuals | visual_brief (missing) | ❌ | ❌ |
| Publication prep | distribution (gap) | ⚠️ backend only | ❌ |

**Drift (partially closed PRODUCT-01):** Offer Builder runtime + review UI wired. Positioning/claims still bridged from BIV until dedicated runtimes. Content/posts/visuals remain deferred.

---

## Skills not connected to CWF

All 11 commercial `ms.skill.*` packages:

- Not invoked by Launch Pack service
- Not invoked by intent navigation (except BIV parallel path)
- Not in `execute-specialist` product flow for Home

**Exception:** BIV is CWF-connected but implemented as **`app/business_idea_validation/`**, not as `ms.skill.market_validation` package loader.

---

## CWF logic not represented by Skills

| CWF behavior | Implementation | Skill gap |
|--------------|----------------|-----------|
| Idea validation | BIV skill module | Parallel to ms.skill.market_validation package |
| Launch Pack request | DB + service | No launch_strategy skill |
| Content draft in assistant | user_requests + LLM | No copywriting skill |
| Content Factory generate | content_factory service | No content_strategy skill |
| Telegram dry-run | publication jobs API | No governed distribution skill |

---

## UI routing conflicts

| Issue | Location | Impact |
|-------|----------|--------|
| Intent cards → generic assistant | `intent-navigation.ts` | B–J bypass governed Skills |
| Legacy intake wizard | `/workspace/projects/new/*` | Parallel Alpha path |
| `intent-routing.ts` legacy rules | points to `/workspace/projects/new?scenario=idea_validation` | Overridden by CWF.1a for BIV |
| Review queue empty shell | `/workspace/review` | Blocks journey L |
| Channels empty shell | `/workspace/channels` | Blocks publication setup |
| Content Factory off-path | owner preview only | G/H not connected |
| Publication execute blocked | `content-factory-publish-panel.tsx` | L blocked in UI |

---

## Duplicate / dead logic

| Area | Notes |
|------|-------|
| Product Alpha routes | investigation, strategy, verdict workspaces — frozen parallel to CWF home |
| Recovery preview R3 | Redirect; Content Factory panel orphaned |
| market_validation v0.1.0 root + v0.2.0 subdir | Version ambiguity; frozen hash is 0.2.0 |
| Discovery vs Product | KB-WPL discovery routes capabilities; product UI ignores discovery |

---

## Integration gap summary

```
CWF Decision Layer     ✅ (verdict → branch → request)
CWF Delivery Layer     ❌ (no Skill execution → no artifacts)
CWF Publication Layer  ⚠️ (backend only, UI blocked)
Skill Package Layer    ✅ (contracts on disk)
Skill Runtime Layer    ❌ (except BIV)
```

**Primary integration debt (updated):** PRODUCT-01 Offer runtime **implemented** — owner acceptance pending. Next: **PRODUCT-02** Content Strategy + Copywriting OR governed content golden path after approved Offer.

---

## CWF.1 / CWF.1a unchanged confirmation

PRODUCT-00 audit did **not** modify CWF.1a implementation or architectural invariants. Drift is **documented**, not patched in code.
