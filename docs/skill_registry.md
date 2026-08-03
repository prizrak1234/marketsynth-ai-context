# Skill Registry (Phase H2.2)

A **Skill** is a versioned capability contract — not a document and not a long prompt.

Package: `app/specialist_skills/` (separate from marketing `app/marketing/skills/` and from Agent Registry).

## SkillDefinition fields

`id`, `code`, `version`, `title`, `domain`, `description`, `specialist_roles`, `input_schema`, `output_schema`, `prerequisites`, `clarification_schema`, `knowledge_scopes`, `required_tools`, `optional_tools`, `quality_gates`, `execution_policy`, `status`, `supersedes_version`.

## Statuses

`draft` | `active` | `paused` | `deprecated` | `archived`

H2.2: all skills are **`draft`** with `execution_policy=draft_only`.

## Initial skills

**Content:** `content.telegram_post`, `content.social_post`, `content.content_plan`, `content.youtube_script`  
**Research:** `research.market_overview`, `research.competitor_analysis`, `research.audience_segmentation`  
**Programmer:** `programmer.telegram_bot_spec`, `programmer.website_spec`, `programmer.automation_spec`  
**Strategy:** `strategy.positioning`, `strategy.offer_design`, `strategy.channel_selection`

API: `GET /specialist-skills` (no prompts, no execution).
