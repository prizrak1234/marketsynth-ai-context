# Workflow Capability Map

**Program:** KB-SKILL-01.6  
**Status:** Read-only mapping — workflow presence ≠ released capability

## Hierarchy

```
Profession → Capability → Skill → Workflow Pattern → Connector → Tool
```

## AI Marketing Director

### 1. Research

| Capability | Related Skills | Workflow patterns (catalog) | Production readiness |
|------------|----------------|----------------------------|----------------------|
| Market Research | `ms.skill.market_research` | competitor/market JSON families | catalog_only |
| Competitor Analysis | `ms.skill.competitor_analysis` | content-gap workflows | catalog_only |
| Website Audit | — | CRO/audit workflows | catalog_only |
| SEO Gap Analysis | — | SEO/keyword workflows | catalog_only |
| Review Analysis | — | review-scraping workflows | catalog_only |

### 2. Customer Intelligence

| Capability | Related Skills |
|------------|----------------|
| ICP & Segmentation | `ms.skill.icp_segmentation` |
| Interview Design | `ms.skill.customer_interview_design` |
| Meaning Extraction | `ms.skill.customer_meaning_extraction` |

### 3. Strategy

| Capability | Related Skills |
|------------|----------------|
| Market Validation | `ms.skill.market_validation` |
| Positioning | `ms.skill.positioning` |
| Offer Builder | `ms.skill.offer_builder` |

### 4. Content

| Capability | Related Skills | Notes |
|------------|----------------|-------|
| Presentation Architecture | `ms.skill.presentation_architecture` | Spec only — no Marp execution |
| Blog / Social / YouTube | — (future) | Publication workflows **catalog_only** |

### 5. Distribution

Telegram, Instagram, LinkedIn, WordPress publication workflows map to **Distribution** capabilities. All require **human approval** and Connector Gateway — **not production-ready**.

### 6. Analytics

SEO reporting, funnel, content performance workflows — **reference_only** until governed analytics connectors exist.

### 7. Engineering

| Capability | Skill | Adaptation status |
|------------|-------|-------------------|
| n8n Workflow Architecture | `ms.skill.n8n_workflow_architecture` | candidate |
| n8n Workflow Debugging | `ms.skill.n8n_workflow_debugging` | candidate |
| n8n Deployment Review | `ms.skill.n8n_deployment_review` | candidate |
| Knowledge Linking | `ms.skill.knowledge_linking` | candidate |
| Workflow Backup | — | catalog patterns only |

## Mapping rules

Each workflow template mapping includes:

- `workflow_template_id`
- `capability_id`
- `related_skill_ids`
- `required_connectors` (future)
- `required_approval` (true for publication/write)
- `security_class`
- `adaptation_status` (default: `catalog_only`)
- `production_readiness` (default: false)

**Presence of a workflow does not prove a capability is released.**

See also: [MARKETING-CAPABILITY-MAP.md](MARKETING-CAPABILITY-MAP.md)
