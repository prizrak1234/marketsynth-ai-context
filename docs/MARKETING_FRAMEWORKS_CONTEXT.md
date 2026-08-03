# Marketing Frameworks Context

Canonical **business frameworks** the marketing agent and skills must follow. These define *what* professional output looks like before tools or copy run.

Implementations: `MarketingSkillType` executors, campaign `skill_context` summaries, future LLM prompts seeded from `knowledge/`.

---

## 1. Segment research

**Purpose:** Who we sell to and what blocks them — before messaging or offer work.

| Dimension | Capture |
|-----------|---------|
| Socio-demo | Age, income band, role, geography |
| Geo | Markets, cities, service radius |
| Pains | Current frustrations (concrete, not generic) |
| Desires | Outcomes they want |
| Fears | Risks they avoid (money, time, shame, health) |
| Current state | Where they are today |
| Desired state | Where they want to be |

**Output artifact:** `segment_summary` on campaign skill context.

**Skill mapping:** `segment_research`

---

## 2. Meaning unpacking

**Purpose:** Translate pains/desires into messaging building blocks.

| Element | Description |
|---------|-------------|
| Desires table | Structured wants vs. blockers |
| Benefits | What the client gains |
| Fears | Emotional and rational barriers |
| Objections | Stated reasons not to buy |
| Counter-arguments | Responses to objections |
| Promise formulations | Testable headline-level promises |

**Output artifact:** merged into `offer_summary` / meaning fields on skill context.

**Skill mapping:** `meaning_unpacking`

---

## 3. Offer packaging

**Purpose:** Structure a strong commercial offer — not final ad copy.

| Element | Description |
|---------|-------------|
| Measurable result | What the client can measure (leads, revenue, time saved) |
| Speed | How fast they get the result |
| Mechanism | How delivery works (simple explanation) |
| Simplicity | Why it's easy to start |
| Safety | Risk reduction (guarantee, proof, process) |
| Core thesis | One-sentence offer spine |

**Output artifact:** `offer_summary` on campaign skill context.

**Skill mapping:** `offer_packaging`

---

## 4. Offer justification

**Purpose:** Business case and CTA — why now, why us, why this price.

| Element | Description |
|---------|-------------|
| Target fit | Why this audience needs this offer |
| How it works | Steps or delivery model |
| Why it works | Proof, logic, mechanism credibility |
| Convenience | Friction removed |
| Safety proof | Cases, guarantees, credentials |
| Value breakdown | What's included vs. alternatives |
| Price justification | Why the price matches value |
| CTA | Single clear next step |

**Output artifact:** justification fields in skill output / `offer_summary`.

**Skill mapping:** `offer_justification`

---

## Framework order in campaigns

Typical professional sequence:

```
Segment research
  → Meaning unpacking (optional if brief rich)
  → Offer packaging
  → Offer justification
  → Demand validation (Wordstat)
  → Traffic validation (Metrica)
  → Content / media / publishing
```

Supervisor and workflow layers recommend this order; they do not auto-run it.

## Source material

Detailed prompts and examples live under:

- `knowledge/` (topical corpus)
- `skills/*/references/`
- `knowledge/prompts/`, `knowledge/manuals/`

## Related docs

- [MARKETING_AGENT_TARGET_MODEL.md](MARKETING_AGENT_TARGET_MODEL.md)
- [PROJECT_KNOWLEDGE_MAP.md](PROJECT_KNOWLEDGE_MAP.md)
