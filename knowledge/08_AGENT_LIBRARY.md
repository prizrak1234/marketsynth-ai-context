# Agent Library

> **Agent OS model:** [docs/AGENT_OS_ARCHITECTURE.md](../docs/AGENT_OS_ARCHITECTURE.md)  
> **Marketing roles:** 14 frozen specialists (AI.119)  
> **Last updated:** 2026-07-29

---

## Platform agents (conceptual)

| Agent / Layer | Purpose | Inputs | Outputs | Permissions |
|---------------|---------|--------|---------|-------------|
| **Business Operator** | Map user intent → scenario → campaign | Natural language intent | Scenario suggestion, campaign draft | Read projects; create campaign on confirm |
| **Business Operator Assist** | Clarify low-confidence intents | Intent + context | Questions, preview, confidence | No auto-create; confidence gate 0.65 |
| **Business Operator LLM Fallback** | Optional LLM when rules fail | Intent (low confidence) | Suggestion only | Off by default; no auto-create |
| **Campaign Supervisor** | Quality control (read-only) | Campaign artifacts | Gaps, contradictions, risks, health | Read-only; never executes |
| **BIV Analyst** | Evidence-backed idea validation | Idea intake, market context | Research report, verdict, evidence | Research APIs; no publish |
| **Launch Pack Composer** | Assemble commercial deliverables | Approved verdict + offer | Launch pack artifacts | Persist request; defer missing skills |

---

## Marketing department v2 (14 roles, frozen)

Baseline specialists — execute via `POST .../execute-specialist` (explicit, one at a time).

| Role | Purpose | Key outputs |
|------|---------|-------------|
| Strategist | Campaign strategy | Strategy doc, priorities |
| Researcher | Market/audience research | Research brief |
| Content Planner | Content calendar/plan | Plan artifacts |
| Copywriter | Text production | Copy drafts |
| SEO Specialist | Search optimization | SEO recommendations |
| SMM Manager | Social strategy | Channel plan |
| Media Buyer | Paid media planning | Media plan |
| Analyst | Performance analysis | Metrics summary |
| Creative Director | Visual direction | Creative brief |
| Producer | Production coordination | Production checklist |
| Editor | Quality review | Edit notes |
| Project Manager | Timeline/coordination | Status, blockers |
| Brand Manager | Brand consistency | Brand guidelines apply |
| PR Manager | PR angles | PR draft |

**Dependencies:** `V2_SPECIALIST_DEPENDENCIES` — separate from frozen v1 matrix.  
**Regression:** `tests/test_phase_ai_123_marketing_department_v2_regression_smoke.py`

---

## Governed skills (`ms.skill.*`)

| Skill package | Purpose | CWF connected |
|---------------|---------|---------------|
| market_validation / v0.2.0 | Idea validation process | Parallel (BIV is separate runtime) |
| market_research | Market research | No |
| icp_segmentation | Audience/ICP | No |
| product_marketing_context | PMC document | No |
| customer_meaning_extraction | Meaning unpack | No |
| offer_builder (PRODUCT-01) | Offer packaging | Partial ✅ |
| n8n_workflow_architecture | Workflow design | No |
| knowledge_linking | KB linking | No |
| presentation_architecture | Deck structure | No |

Manifests: `packages/knowledge/`, `docs/skills/`

---

## Scenario agents (draft plan only)

Five business scenarios in `app/marketing/scenarios/`:

| Scenario ID | Business case |
|-------------|---------------|
| restaurant | Local restaurant promotion |
| dental_clinic_lead_gen | Dental lead generation |
| blogger_content | Content engine |
| saas_launch | SaaS product launch |
| local_promo | Local business promo |

**API:** `POST /projects/{id}/marketing-scenarios/{id}/create-plan` — draft only.

---

## Identity qualification operator (H2.8E, gated)

| Component | Purpose |
|-----------|---------|
| Identity Generation Subsystem | Registry, manifest, preflight |
| Qualification operator | Paid approval, variant selection |
| Identity engine (H2.8D) | Provider transmit, max 5 refs |

**Not commercial** until owner recognizes person in real diagnostic.

---

## Agent permissions model

| Rule | Enforcement |
|------|-------------|
| No auto skill/tool runs | API + Action Center design |
| Sanitize inbound text | `sanitize_payload` |
| Supervisor read-only | No execute endpoints |
| Publishing requires approval | Publication job gates |
| Paid media requires explicit confirm | Video smoke, identity paid approval |
| Industrial domains | `insufficient_governed_knowledge` blocks without fresh KnowledgeSnapshot |

---

## Dependencies between agents

```
Business Operator
  → Campaign (container)
    → Brief Intake (completeness gate)
    → Skills (explicit runs)
    → Tools (via skills or actions)
    → Workflows (checklist recommendations)
    → Supervisor (read-only audit)
    → Action Center (explicit buttons)
```

---

## Cursor / dev agents

| Agent context | File |
|---------------|------|
| Primary instructions | [AGENTS.md](../AGENTS.md) |
| Commercial directive | [.cursor/rules/commercial-product-directive.mdc](../.cursor/rules/commercial-product-directive.mdc) |
| Foundation rules | [.cursor/rules/botfazer-foundation.mdc](../.cursor/rules/botfazer-foundation.mdc) |
| This SoT | [00_INDEX.md](00_INDEX.md) |
