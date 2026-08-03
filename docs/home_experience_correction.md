# Home Experience Correction — conversational entry

## Route hierarchy

| Route | Role |
|-------|------|
| `/workspace` | Conversational user home (entry) |
| `/workspace/projects` | Preserved agency operations dashboard |
| `/workspace/tasks` | Specialist/task flows (content, bot, website, …) |
| `/workspace/projects/[id]/…` | Existing commercial lineage |

## Intent categories

`idea_validation`, `market_research`, `competitor_analysis`, `content`, `social_media`, `youtube`, `telegram_bot`, `website`, `saas`, `marketing_strategy`, `general`.

Routing is deterministic in v1 (no fake AI execution). Clarification runs before Project creation when input is ambiguous.
