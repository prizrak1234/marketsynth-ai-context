# PRODUCT-03 — Strategy Capability Cards

> **Program ID:** PRODUCT-03 = Strategy Architecture  
> **Task:** PRODUCT-03-STRATEGY-BLUEPRINT-01 · **Patch:** PRODUCT-03-STRATEGY-BLUEPRINT-PATCH-01  
> **Owns:** Composition unit cards under `project.strategy`  
> **OD-P03-01…10:** OWNER-APPROVED  
> **`owner_freeze`:** **OWNER-FROZEN** (2026-08-02)  
> **Status:** **OWNER-FROZEN**

---

## 0. Card template

| Field | Meaning |
|-------|---------|
| ID | Stable SC-* id |
| Name | Customer-facing name |
| Classification | Strategy composition unit under `project.strategy` — **not** a nav product |
| Purpose | Why it exists |
| Customer value | Contribution to **Approved Strategy Package** (SC-06/07 = fence/honesty, not separate SKUs) |
| Entry conditions | When section may be filled |
| Consumed artifacts | Unique inputs |
| Actions | Edit / regenerate section / full regen (each → **new package version**) |
| Produced artifacts | Section of StrategyPackage |
| Blocking conditions | What blocks completeness |
| Exit conditions | Done criteria |
| Approval | **Package-level** `strategy_package_approval` only (no per-SC approval) |
| Run multiplicity | MVP: sections filled in **one** Strategy run; revisions = new package versions |
| Parallelism | Dependency order; not separate commercial modules |
| Recoverability | Prior package versions immutable |
| Versioning | Any section edit/regen → new StrategyPackage version |
| Invalidation | Must-refresh sets |
| UI surface | Strategy panel section only |
| KPIs | Measurable |
| MVP status | mvp / post-mvp / excluded |
| Out of scope | Explicit non-goals |
| Acceptance criteria | Objectively testable |

**Parent:** one `project.strategy` stage.  
**Catalog wording:** funnel = hypothesis only · offer = Strategy Offer Structure (≠ Launch Offer Artifact) · channel = direction (≠ media execution) · measurement = success criteria (≠ Analytics runtime).

---

## Evidence vs assumption decision table (normative)

| Condition | Outcome |
|-----------|---------|
| ≥1 valid evidence ref from **pinned** Research version | Field may be **evidenced** |
| No valid evidence ref AND package `assumption_constrained=true` AND owner-visible assumption text | Field may be **assumption-tagged** |
| No valid evidence ref AND package NOT assumption-constrained | Field **blocks** |
| No evidence AND no assumption tag (constrained path) | Field **blocks** |
| Claim cites evidence id absent from pin | **Reject** |
| Owner edits an evidenced claim and removes evidence | `evidence_link_status=broken` **or** convert to owner assumption |

**Precedence:** evidenced > assumption-tagged > block. Never invent evidence.

---

## Field schemas (closed)

### SC-01 `target_segment`

| Field ID | Required |
|----------|----------|
| `primary_segment_name` | yes |
| `primary_segment_definition` | yes |
| `geo_focus` | yes |
| `icp_role` | yes |
| `icp_pain` | yes |
| `icp_trigger` | yes |
| `evidence_refs[]` / assumption tags | yes |

### SC-02 `positioning_value`

| Field ID | Required |
|----------|----------|
| `positioning_statement` | yes |
| `value_proposition` | yes |
| `alternative_frame` | yes |
| `evidence_refs[]` / assumption tags | yes |

### SC-03 `offer_structure`

| Field ID | Required | Notes |
|----------|----------|-------|
| `offer_name` | yes | Forbidden: `offer_artifact_version_id`, `post_body`, `publish_job_id` |
| `offer_components[]` | yes (≥1) | Not pricing engine |
| `packaging` | yes | |
| `pricing_assumption` | yes | range / constraints / unknowns / validation need |
| `spend_band_min` | no | If any spend_band_* set, all three + meta required |
| `spend_band_max` | no | |
| `spend_band_currency` | no | ISO-like code string |
| `spend_band_provenance` | required if any band field set | ∈ {`owner_provided`, `research_estimate`, `unknown`} |
| `spend_band_source` | required if any band field set | free text / evidence id |
| `spend_band_confidence` | required if any band field set | ∈ {`low`,`medium`,`high`,`unknown`} |
| `evidence_refs[]` / assumption tags | yes | |

**ROI deny-list:** `guaranteed roi`, `guaranteed revenue`, `predicted revenue`, `will generate $`, `CAC will`.

### SC-04 `messaging_pillars`

| Field ID | Required | Constraints |
|----------|----------|-------------|
| `pillars[]` | yes, 3..5 | `title` ≤80 · `statement` ≤280 · `links_to` ∈ {SC-02, SC-03, evidence_ref} |
| Forbidden | | `post_body`, `content_asset_id`, publish CTAs |

### SC-05 `channel_direction`

| Field ID | Required |
|----------|----------|
| `channels_ranked[]` | yes — each: `channel_id`, `rationale`, `segment_fit`, `risks?`, `assumptions?` |
| `primary_channel_id` | yes |
| `hypothesis` | yes — what Launch will test |

**Forbidden:** `budget_allocation`, `media_plan`, `schedule`, `bot_token`, `publication_job_id`, execution config.

### SC-06 `launch_constraints`

| Field ID | Required |
|----------|----------|
| `constraints[]` | yes (≥1) — `constraint_id`, `text`, `severity` ∈ {hard, soft} |

**Role:** boundary fence for Launch — **not** a separate paid SKU.

### SC-07 `measurement_criteria`

| Field ID | Required |
|----------|----------|
| `criteria[]` | yes (≥1) — `criterion_id`, `metric_or_signal`, `assumption_tag?` |
| `funnel_hypothesis` | optional short — **not** funnel builder |

**Role:** honesty / success bar — **not** Analytics runtime, **not** separate SKU. Same ROI deny-list.

### Package-level

| Field ID | Required |
|----------|----------|
| `summary` | yes |
| `risks[]` | yes |
| `open_assumptions[]` | yes |
| `limitations` | yes |
| `next_action` | yes |
| `assumption_constrained` | yes boolean |
| `research_version_pin` | yes |
| `accepted_risks[]` | yes if constrained |

---

## SC-01 — Target Segment & ICP

| Field | Value |
|-------|-------|
| ID | `SC-01` |
| Purpose | Lock whom we pursue |
| Customer value | Focus for first Launch |
| Consumed | Pinned Research audience/geo evidence; Intake |
| Produced | `target_segment` |
| Approval | Package-level only |
| Invalidation | Change ⇒ must-refresh SC-02…SC-07 |
| MVP | mvp |
| Out of scope | Multi-market; CRM segments |
| Acceptance | Schema + decision table; invented evidence ⇒ reject |

---

## SC-02 — Positioning & Value Proposition

| Field | Value |
|-------|-------|
| ID | `SC-02` |
| Purpose | Lock how we win / what we promise |
| Consumed | SC-01; competitor/problem evidence |
| Produced | `positioning_value` |
| Invalidation | By SC-01; change ⇒ SC-03, SC-04 |
| MVP | mvp (merged Positioning+VP) |
| Out of scope | Brand books, DIS |
| Acceptance | Both positioning + VP complete per schema |

---

## SC-03 — Offer Structure

| Field | Value |
|-------|-------|
| ID | `SC-03` |
| Purpose | Lock what we sell (structure) + pricing assumptions |
| Boundary | ≠ Launch Offer Artifact |
| Invalidation | Change ⇒ SC-04, SC-06, SC-07 |
| Approval | Package-level; + `budget_assumptions_acknowledgement` if any spend_band_min/max/currency present |
| MVP | mvp |
| Out of scope | Pricing engine, checkout |
| Acceptance | Forbidden Launch fields absent; band fields have provenance/source/confidence; ROI deny-list clean; pricing_assumption alone does not require budget ack |

---

## SC-04 — Messaging Pillars

| Field | Value |
|-------|-------|
| ID | `SC-04` |
| Purpose | Lock what we say for later Content |
| Boundary | ≠ ContentPackage |
| Invalidation | By SC-02/03 |
| MVP | mvp |
| Acceptance | 3..5 pillars; no post_body; each links_to set |

---

## SC-05 — Channel Direction

| Field | Value |
|-------|-------|
| ID | `SC-05` |
| Purpose | Preferred channels + why + hypothesis |
| Boundary | ≠ media plan / budget / schedule / publish |
| Seeds Launch | `primary_channel_id` into LaunchInputSnapshot as direction seed; Launch owns ops |
| MVP | mvp |
| Acceptance | Reject ops fields; primary ∈ ranked list |

---

## SC-06 — Launch Constraints

| Field | Value |
|-------|-------|
| ID | `SC-06` |
| Classification | Boundary / honesty unit (**not SKU**) |
| Purpose | Fence Launch must not violate |
| Customer value | Completes Strategy Package; not sold alone |
| MVP | mvp |
| Acceptance | ≥1 constraint; LaunchInputSnapshot copies constraint ids + Strategy version |

---

## SC-07 — Measurement Criteria

| Field | Value |
|-------|-------|
| ID | `SC-07` |
| Classification | Boundary / honesty unit (**not SKU**) |
| Purpose | Observable success criteria / light funnel hypothesis |
| Boundary | ≠ Analytics dashboard / A/B / ROI engine |
| MVP | mvp |
| Acceptance | ≥1 criterion; ROI deny-list clean |

---

## Parent stage

| Field | Value |
|-------|-------|
| ID | `project.strategy` |
| Produced | StrategyPackage (one run OK for MVP) |
| Exit | `strategy_package_approval` |
| Entry | Research acceptance **or** `partial_strategy_override` |
| Runtime | blueprint |

---

## Parallelism

```text
SC-01 → SC-02 → SC-03 → (SC-04 ∥ SC-05) → (SC-06 ∥ SC-07) → package approval → launch_handoff_approval
```
