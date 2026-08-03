# Skill ↔ UserRequest Route Matrix (Phase H2.2)

| H1 route category | Specialist | Skill / path |
|-------------------|------------|--------------|
| `content` | content_specialist | `content.telegram_post` (+ clarification) |
| `content_plan` | content_planner | `content.content_plan` |
| `social_media` | content_specialist | `content.social_post` |
| `youtube` | content_specialist | `content.youtube_script` |
| `telegram_bot` | programmer | `programmer.telegram_bot_spec` |
| `website` | programmer | `programmer.website_spec` |
| `automation` | programmer | `programmer.automation_spec` |
| `market_research` | researcher | `research.market_overview` |
| `competitor_analysis` | researcher | `research.competitor_analysis` |
| `marketing_strategy` | strategist | `strategy.positioning` **if** domain eligibility |
| `idea_validation` | researcher | **ProjectBrief / Investigation** — not a simple skill |
| `saas` | programmer | project intake — no single draft skill yet |
| `general` / `unsupported` | — | clarify / none |

Implementation: `app/specialist_skills/route_mapping.py`.
