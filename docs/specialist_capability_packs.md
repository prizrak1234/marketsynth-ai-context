# Specialist Capability Packs (Phase H2.2)

Each specialist role receives a **Capability Pack**:

role + allowed skills + knowledge scopes + tool profile + output/approval/quality/locale policies.

| Role | Default skill | Forbidden tools (examples) |
|------|---------------|----------------------------|
| `content_specialist` | `content.telegram_post` | shell, deploy, publish, verdict approve |
| `content_planner` | `content.content_plan` | shell, deploy, publish |
| `researcher` | `research.market_overview` | verdict approve, unreviewed scrape |
| `programmer` | `programmer.telegram_bot_spec` | shell, filesystem write, git mutate, deploy |
| `strategist` | `strategy.positioning` | shell, deploy, publish |

Implementation: `app/specialist_skills/capability_packs.py`.
