# Product

> **Canonical inventory:** [docs/product/MARKETSYNTH-PLATFORM-MAP.md](../docs/product/MARKETSYNTH-PLATFORM-MAP.md)  
> **Last updated:** 2026-07-29

---

## Product definition

**Marketsynth** sells **evidence-backed business decisions and launch execution** — starting with idea validation and a Telegram-ready Launch Pack.

Legacy internal label: **BotFazer** (code paths unchanged).

---

## Packages & editions

| Package | Status | Contents |
|---------|--------|----------|
| **Launch Pack (CWF.1)** | Active P0 | BIV, verdict, risks, audience, positioning, offer, launch plan, 3 posts, 1–3 visuals, Telegram publish |
| **Business Idea Validator (CMVP.1)** | Accepted; integrity repair open | Evidence-backed research, gap-directed coverage, verdict |
| **Offer Builder (PRODUCT-01)** | Runtime exists; **not frozen** | Offer artifact + review UI |
| **Marketing Campaign OS (AI.146–265)** | Frozen layers | 14-role dept, scenarios, wizard, campaigns, skills, supervisor |
| **Video Studio (VS.1–2A)** | Frozen | Image→video smoke + Commercial Home persistence |
| **Beta launch pack (AI.96–100)** | Frozen | Access gate, tester guide, demo reset |
| **Identity Generation (H2.8E)** | Gated | Not product until owner diagnostic acceptance |

No public pricing tiers documented in repo — **pricing logic TBD by owner**. Commercial gate: willingness-to-pay per PR, not feature count.

---

## Features (by domain)

### Active / P0

- Commercial Home intent entry (CWF.1a)
- BIV intake with specificity gate (PRODUCT-01.3A)
- Evidence funnel + commercial research
- Business verdict persistence
- Launch Pack request service
- Offer Builder runtime + review
- Telegram publishing (real send with approval)

### Accepted / frozen (demonstrable, not current sprint)

- Marketing pipeline AI.27–39
- Content/Media/Publishing AI.40–79
- MVP demo + beta QA AI.80–100
- Marketing dept v2, scenarios, wizard, campaign layers AI.110–265
- Workflow library pilot (50 n8n templates, download only)

### Architecture only / planned

- Website Builder, Direct/Ads execution, BI
- Full skill package loader for all 11 `ms.skill.*` in CWF
- DIS (Digital Identity System) — forbidden until CGP.10C

---

## Customer journey

### Canonical platform journey (target)

```
Idea → Onboarding → Workspace → Research (BIV) → Verdict → Strategy → Readiness
→ Campaign → Content → Media → Publishing → Analytics → Optimization
```

### Active commercial slice (CWF.1)

```
Idea → Research → Evidence → Verdict → Offer → Launch Plan
→ 3 Content Assets → Optional Visuals → Telegram Approval → Real Publication → Delivery Evidence
```

See [09_WORKFLOWS.md](09_WORKFLOWS.md) for step detail.

---

## Commercial positioning

| Dimension | Position |
|-----------|----------|
| **Category** | AI Business OS (not chatbot, not agent marketplace) |
| **Wedge** | Validate before spend; launch with evidence |
| **Proof** | Browser-verifiable golden path with real Telegram send |
| **Honesty** | Gaps visible when skills/content/visuals deferred |

---

## Product constitution

- Ch.1 Home: [docs/HOME_PRODUCT_RULE.md](../docs/HOME_PRODUCT_RULE.md) — business decisions, not AI control panel
- Ch.2 Video: [docs/VIDEO_STUDIO_PRODUCT.md](../docs/VIDEO_STUDIO_PRODUCT.md)
- Index: [docs/PRODUCT_CONSTITUTION.md](../docs/PRODUCT_CONSTITUTION.md)

---

## Known product gaps (summary)

Full list: [13_KNOWN_PROBLEMS.md](13_KNOWN_PROBLEMS.md) · Audit: [docs/product/CWF-SKILL-INTEGRATION-GAPS.md](../docs/product/CWF-SKILL-INTEGRATION-GAPS.md)

- Launch Pack items without skill runtime: audience, positioning, launch plan, posts, visuals
- BIV report integrity issues (owner rejection 2026-07-24) — **PRODUCT-01.3 P0**
- Review queue / Channels UI shells block publication setup journey
- Content Factory off main path (owner preview only)
