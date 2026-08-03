# Marketing Profession Map

**Profession:** `profession.ai_marketing_director`  
**Phase:** KB-WPL-01.7

## Golden path (required dependencies)

```
product_context → market_research → competitive_intelligence → customer_intelligence
→ market_validation → positioning → claim_substantiation → offer_architecture → launch_strategy
```

Optional downstream: content_strategy → copywriting; launch_strategy → distribution → analytics → learning_and_feedback.

## Skill bindings (implemented)

| Capability | Skill |
|------------|-------|
| product_context | `ms.skill.product_marketing_context` |
| market_research | `ms.skill.market_research` |
| competitive_intelligence | `ms.skill.competitor_analysis` |
| customer_intelligence | `ms.skill.icp_segmentation` + CIM v0.1.0 |
| customer_interview_design | `ms.skill.customer_interview_design` |
| customer_meaning_extraction | `ms.skill.customer_meaning_extraction` |
| market_validation | `ms.skill.market_validation` |
| positioning | `ms.skill.positioning` |
| claim_substantiation | `ms.skill.claim_substantiation` |
| offer_architecture | `ms.skill.offer_builder` |
| presentation_architecture | `ms.skill.presentation_architecture` |

## Deferred capabilities

content_strategy, copywriting, launch_strategy, distribution, marketing_analytics, learning_and_feedback.

## Rules

- Positioning consumes CIM — does not replace it.
- Claim substantiation precedes customer-facing offer claims.
- Publication/distribution requires human approval (deferred — gap recorded).
