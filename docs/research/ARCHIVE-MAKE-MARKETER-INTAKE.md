# Archive Intake — «ИИ маркетолог» (Make blueprints)

| Field | Value |
|-------|-------|
| **Source** | `f:\Мой проект\ИИ маркетолог в n8n.rar` (~197 KB) |
| **Extracted for audit** | `.tmp_archive_make_marketer/` (local only, not committed) |
| **Date** | 2026-07-23 |
| **Decision rubric** | [adopt-adapt-reject-matrix.md](adopt-adapt-reject-matrix.md) |

**Note:** Archive filename says «n8n», but payloads are **Make.com** `.blueprint.json` exports, not n8n workflow JSON.

---

## Inventory (13 substantive files)

### Methodology (4)

| File | Marketsynth mapping |
|------|---------------------|
| `1) Сбор информации о сегменте.md` | **Adapt** → ICP resources (`customer-interview-question-framework`) |
| `2) Распаковка смыслов.md` | **Adapt** → new Skill `ms.skill.customer_meaning_extraction` |
| `3_Упаковка_сильного_торгового_предложения.md` | **Adapt** → `ms.skill.offer_builder` (02.8) |
| `4_Обоснование_торгового_предложения.md` | **Adapt** → Offer Builder + `ms.skill.claim_substantiation` |

### Automations (5 Make blueprints)

| File | Marketsynth mapping |
|------|---------------------|
| `ИИ маркетолог .blueprint.json` | **Reject** architecture; **Reference** Telegram UX |
| `ИИ маркетолог ПЛЮС .blueprint.json` | **Reject** architecture; image URL handoff pattern only |
| `metrica.blueprint.json` | **Adapt** → Skill `ms.skill.web_analytics_analysis` + Connector `connector.yandex_metrica` |
| `Wordstat.blueprint.json` | **Adapt** → Skill `ms.skill.search_demand_analysis` + Connector `connector.yandex_wordstat` |
| `nano banana (url).blueprint.json` | **Adapt** → Connector image gen + `ms.skill.visual_brief` |

### Reference data & orchestrator prompt (4)

| File | Marketsynth mapping |
|------|---------------------|
| `Промпт.md` | **Adapt** → Marketing Director / Intent Router behavior |
| `metrica-dimensions-knowledge-base.json` | **Adapt** → governed reference (not raw agent context) |
| `yandex-regions-codes-knowledge-base.txt` | **Adapt** → versioned region contract |
| `Настройки.png` | **Reference** only |

---

## What «ИИ маркетолог» actually is

```
Telegram WatchUpdates
  → Router (message / voice / photo / caption)
  → single openai-gpt / AI Agent
  → text reply OR photo + caption
```

**PLUS variant:** file upload → public URL → agent with image context.

### Not present (Marketsynth already stronger)

- Skill Registry / frozen packages
- Evidence + provenance discipline
- Approval gates (spend, publish, legal)
- Tenant isolation
- Separate professional Skills
- Analysis vs execution separation
- Provider schema validation + lineage

---

## Methodology highlights (verified from source)

### 1. Segment interview (`1) Сбор информации о сегменте.md`)

Question framework covers:

- current state (точка A)
- pains, desired transformation, measurable outcome
- speed, comfort/service, safety expectations
- fears: negative experience, distrust of topic/org/self, price-value unfairness

**Marketsynth rule:** answers remain `user_statement` — unverified until evidence. **Do not** fork CIM.

### 2. Meaning extraction (`2) Распаковка смыслов.md`)

Core loop:

```
desire → can we satisfy? (yes/partial/no) → mechanism → benefit → promise candidate
```

Includes fear/objection tables and counter-arguments.

**Example domain in file:** crypto trading — contains **high-risk promise language**:

- «стабильный дополнительный доход +10–20%»
- «100% безопасность»
- implied guaranteed outcomes

→ Must flow through **`ms.skill.claim_substantiation`** with compliance flags; **Reject** as production copy.

### 3. Offer packaging (`3_` / `4_`)

Useful structures for Offer Builder models:

- `offer_promise`, `delivery_mechanism`, `benefit_mapping`
- step-by-step technology with intermediate results
- service advantages, risk reversal, price justification
- bundle / upsell / cross-sell framing

**Replace archive phrasing:**

| Archive | Marketsynth |
|---------|-------------|
| «убедить в 100% безопасности» | documented risk-reduction mechanisms + residual risks |
| guaranteed income claims | proof requirements + prohibited promises |

### 4. Orchestrator prompt (`Промпт.md`)

Decision loop (adapt to Intent Router):

1. Classify business task type
2. Determine required data / visual
3. Select tool (Metrica / Wordstat / image gen)
4. Evaluate effect / cost / appropriateness

Rules align with Marketsynth: no fabricated data, no low-value work, business language first.

---

## Blueprint technical notes

### Metrica (`metrica.blueprint.json`)

- NL → LLM (`openai-gpt-3:CreateCompletion`) → Yandex Metrica API params
- Subscenario inputs: `ids`, `metrics`, `dimensions`, `date1`, `date2`, `filtersCustom`
- Uses `metrica-dimensions-knowledge-base.json` as agent context

**Do not port:** hardcoded metric lists, fixed year in prompts, LLM JSON without provider schema validation.

**Do port:** separation of business question → analytical query → connector params.

### Wordstat (`Wordstat.blueprint.json`)

Modes referenced in orchestrator prompt: `one` (default), `short`, `long`; region from KB; optional device.

**Skill:** provider-agnostic demand analysis. **Connector:** Yandex Wordstat only.

### Nano Banana

- prompt → image → temporary URL
- UX rule: max 1 image per user response (budget policy, not global law)

---

## Revised golden path (with archive methodology)

```
Product Marketing Context
        ↓
Market Research
        ↓
Competitor Analysis
        ↓
ICP & Segmentation → CIM
        ↓
Customer Meaning Extraction    ← from «Распаковка смыслов»
        ↓
Market Validation
        ↓
Positioning                    ← frozen 0.1.0 (SKILL-02.7)
        ↓
Claim Substantiation           ← from promise safety logic
        ↓
Offer Builder                  ← from упаковка/обоснование (02.8)
        ↓
Content / Copy / Launch
```

---

## Priority backlog

| Priority | Item |
|----------|------|
| **P0** | `ms.skill.offer_builder` (02.8) |
| **P0 design** | `ms.skill.customer_meaning_extraction` |
| **P0 design** | `ms.skill.claim_substantiation` |
| **P1** | `ms.skill.search_demand_analysis` + Wordstat connector |
| **P1** | `ms.skill.web_analytics_analysis` + Metrica connector |
| **P1** | `ms.skill.visual_brief` + image connector |
| **Resources** | ICP interview framework; Offer mechanism / risk-reversal frameworks |

---

## Explicit rejects

- Import Make blueprints into production
- Single universal agent with all tools
- Telegram bot as sole product architecture
- Financial / safety guarantees without evidence
- Temporary image URLs as permanent assets
- Markdown methodology files as executable Skills without contracts

---

## Related docs

- [SKILL-ROADMAP.md](../rfc/SKILL-ROADMAP.md)
- [SKILL-02-native-skill-matrix.md](../skills/SKILL-02-native-skill-matrix.md)
- [ms.skill.positioning.md](../skills/ms.skill.positioning.md)
- [CIM consumer contracts](../knowledge/CIM-consumer-contracts-v0.1.0.md)
