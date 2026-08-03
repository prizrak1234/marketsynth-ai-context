# PROGRAM-CONTENT-01 — AI Creative Platform

> **Program ID:** PROGRAM-CONTENT-01  
> **Title:** AI Creative Platform (Content Factory / Creative Studio)  
> **Status:** **OPEN** · charter accepted (2026-08-02)  
> **Type:** Product program — architecture-first (not generators-first)  
> **Replaces as active development focus:** Commercial Decision Engine (now **FROZEN**)  
> **Inherits (do not reopen casually):** PRODUCT-02 · EM · Fabric · Capability Pattern · PRODUCT-05 Content Architecture · Launch Publication handoff rules  
> **Does not:** Strategy Runtime · Research Hardening early · Launch Runtime · new Execution Model / Fabric / Orchestrator · provider-first UI

---

## 1. Why this program

Marketsynth’s decision spine (Idea → Research → Strategy → Launch) is architecturally locked but **cannot be fully validated** until Research Hardening (≥2026-08-18).

The **second half** of the product — producing marketing materials — is where the user sees the most visible value:

```text
Strategy (or transitional Launch Pack context)
  → Choose channel
  → Choose format
  → Prepare package / brief
  → Generate
  → Send for approval
  → Edit
  → Version
  → Export
  → Publish (Publication-owned)
```

This is **not** “write a post.” It is a **Creative Platform**: artifacts, review, versions, library, and later providers behind a single contract.

---

## 2. Program thesis

| User works with | User does **not** work with |
|-----------------|----------------------------|
| Content · Visual · Video artifacts | Model brand names as product UX |
| Channel + format + package | Raw provider consoles |
| Review / approve / version / export | Hidden mock “success” |
| Library reuse | One-shot chat generation as SoT |

**Providers** (GPT, Claude, Gemini, Flux, Ideogram, Kling, Veo, Higgsfield, Runway, ElevenLabs, …) attach via a **Provider Adapter Layer** only after domain architectures are frozen.

---

## 3. Relationship to frozen packs

| Pack | Relationship |
|------|----------------|
| **PRODUCT-05 Content Architecture** | **OWNER-FROZEN seed** for text domain (Request → Run → Candidate → approved Asset → Publication handoff). Creative Platform **extends** catalog/formats/channels; does **not** casually rewrite freeze text. Conflicts → owner OD. |
| **PRODUCT-06 Visual (old label)** | Superseded as standalone “next after Content” priority; Visual domain continues **inside this program** as Visual Architecture track. |
| **PRODUCT-07 Publication** | Still required for real publish; sequenced **after** Creative domain packs or as parallel handoff contract — **not** Creative Runtime substitute. |
| **Capability Pattern / Fabric** | Mandatory form. No second run/approval model. |
| **Commercial Decision Engine** | **FROZEN** — resume only by owner. |

---

## 4. Target catalog (vision — not MVP)

### Text
Posts · Articles · Email · Telegram · Instagram · LinkedIn · X · Facebook · Landing · Ads · Creatives copy · PDF · Presentations

### Visual
Images · Banners · Carousels · Covers · Previews · Infographics

### Video
Video · Shorts · Reels · TikTok · YouTube · Storyboard · Prompt packs

**Rule:** Catalog is a **menu of product intents**. MVP ships **few formats that sell**, not the whole matrix on day one.

---

## 5. Domain tracks (architecture-first order)

| # | Track | Core flow (logical) | Runtime |
|---|-------|---------------------|---------|
| 1 | **Text Architecture** | Request → Brief → Draft → Review → Approved Content → Versions → Exports | After Text freeze |
| 2 | **Visual Architecture** | Request → Brief → Prompt → Generation → Selection → Approved Visual → Versions | After Visual freeze |
| 3 | **Video Architecture** | Request → Storyboard → Prompt Pack → Generation → Review → Approved Video | After Video freeze |
| 4 | **Creative Review** | Comments · approvals · version diffs across Text/Visual/Video | Shared |
| 5 | **Asset Library** | Search · tags · reuse · lineage | After artifacts exist |
| 6 | **Provider Adapter Layer** | Unified generate/edit/export contract; model-agnostic UX | After ≥1 domain freeze |
| 7 | **Creative Runtime** | Pattern-compliant runs | **Only after** domain architectures OWNER-FROZEN |

**Forbidden order:** providers / generators / Universal Studio UI **before** Text (and then Visual) architecture freeze.

---

## 6. MVP posture (program-level)

**In early MVP (proposed — refine in first architecture pack):**

- Command Center entry: **Create materials** (not a separate product inside Marketsynth).  
- Text: reuse PRODUCT-05 invariants; expand MVP formats **one commercial path first** (likely Telegram / post package aligned to CWF), not 18 channels.  
- Visual: one working visual format path (not full studio).  
- Review + versions + export honesty.  
- Publication handoff remains Publication-owned (PackageJob canonical when Publication pack exists).

**Out of early MVP:**

- Full multi-channel matrix live  
- Video studio completeness  
- Identity/DIS expansion  
- Provider marketplace UI  
- Strategy/Research Runtime restart  
- Declaring every catalog item as sellable SKU

---

## 7. Invariants (program)

1. Creative Platform = Project Command Center capability family — **not** a separate SaaS inside Marketsynth.  
2. Artifacts > models.  
3. Approved assets immutable; edit/regen → new version.  
4. Fabric CapabilityRun / InputSnapshot / ApprovalRecord semantics — no parallel engine.  
5. No fake progress / silent mock in commercial path.  
6. Publication = external send; Creative ≠ auto-publish.  
7. PRODUCT-05 freeze remains binding until owner OD amends.  
8. No new foundation layer (no Asset Framework / Orchestrator product).  
9. Decision Engine stays FROZEN until owner unfreeze.  
10. Creative Runtime does not auto-start from this charter.

---

## 8. First tasks (do not auto-run)

| Order | Task (proposed) | Purpose |
|-------|-----------------|---------|
| 0 | This charter | Program OPEN |
| 1 | `PROGRAM-CONTENT-01-TEXT-ARCHITECTURE-01` | Pattern pack: extend/align Text domain from PRODUCT-05 toward Creative Platform catalog + MVP cut |
| 2 | `PROGRAM-CONTENT-01-VISUAL-ARCHITECTURE-01` | Visual domain pack (replaces orphan PRODUCT-06 kickoff label) |
| 3 | Creative Review + Asset Library (docs) | Shared review/library contracts |
| 4 | Provider Adapter contract (docs) | Model-agnostic layer |
| 5 | Publication Architecture (as needed for handoff) | External send boundary |
| 6 | Creative Runtime | Only after freezes |

Methodology unchanged: **Draft → Audit → Owner Decisions → Patch → OWNER-FROZEN**.

---

## 9. Explicit stop

Charter recorded. **No** Text/Visual/Video pack draft until owner Cursor TZ for task **1**.  
**No** code · **no** providers · **no** Strategy Runtime · **no** Research run.
