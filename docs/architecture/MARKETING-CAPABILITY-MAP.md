# Marketing Capability Map

**Program:** ARCHIVE-MKT-01 / SKILL-02 native marketer contour  
**Status:** Conceptual (read-only — no orchestration runtime)

## Hierarchy

```
Profession → Capability → Skill → Connector → Tool
```

## AI Marketing Director

The orchestrating marketer may:

- classify intent and required capabilities;
- recommend Skill sequence;
- identify missing evidence;
- stop workflow on blockers;
- request human approval.

It may **not**:

- grant tool permissions;
- activate Skills autonomously;
- bypass Market Validation;
- bypass Claim Substantiation;
- bypass human approval;
- execute external actions directly.

## Capabilities

### 1. Customer Research

| Skill | Package | Role |
|-------|---------|------|
| Product Marketing Context | `ms.skill.product_marketing_context` | Business context |
| Market Research | `ms.skill.market_research` | Market signals |
| Customer Interview Design | `ms.skill.customer_interview_design` | Interview guide (questions ≠ evidence) |
| ICP & Segmentation | `ms.skill.icp_segmentation` | CIM producer |
| Customer Meaning Extraction | `ms.skill.customer_meaning_extraction` | Meanings → promise candidates |

### 2. Competitive Intelligence

| Skill | Package |
|-------|---------|
| Competitor Analysis | `ms.skill.competitor_analysis` |

### 3. Commercial Decision

| Skill | Package |
|-------|---------|
| Market Validation | `ms.skill.market_validation` | Authoritative viability verdict |

### 4. Positioning and Claims

| Skill | Package |
|-------|---------|
| Positioning | `ms.skill.positioning` | CIM consumer — hypotheses only |
| Claim Substantiation | `ms.skill.claim_substantiation` | **Mandatory gate** before offer claims |

### 5. Offer Architecture

| Skill | Package |
|-------|---------|
| Offer Builder | `ms.skill.offer_builder` | Substantiated offer candidates only |

### 6. Future Execution (not in ARCHIVE-MKT-01)

Content Strategy · Copywriting · SEO · Advertising Planning · Launch Strategy · Analytics

### 7. Engineering (KB-SKILL-01)

| Skill | Package |
|-------|---------|
| n8n Workflow Architecture | `ms.skill.n8n_workflow_architecture` |
| n8n Workflow Debugging | `ms.skill.n8n_workflow_debugging` |
| n8n Deployment Review | `ms.skill.n8n_deployment_review` |
| Knowledge Linking | `ms.skill.knowledge_linking` |
| Presentation Architecture | `ms.skill.presentation_architecture` |

Workflow JSON from external archives remains **catalog_only** — see [WORKFLOW-CAPABILITY-MAP.md](WORKFLOW-CAPABILITY-MAP.md).

## Golden path

```
CIM → Interview Design → Meaning Extraction → Market Validation → Positioning
  → Claim Substantiation → Offer Builder → (future Copy / Launch)
```

**Critical contour:** Customer meaning → Promise candidate → Claim substantiation → Offer candidate.

## Shared knowledge

- **CIM** `packages/knowledge/customer_intelligence/0.1.0/` — canonical customer model
- **Marketing Claims** `packages/knowledge/marketing_claims/0.1.0/` — claim, promise, proof, risk-reversal schemas
