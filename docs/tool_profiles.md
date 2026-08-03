# Tool Profiles

Per-specialist allow / deny policy for normalized BusinessTools.

Code: `app/specialist_skills/tool_profiles.py`.

## Hard denies (all roles, H2.7)

- `workflow_automation`
- `advertising_platform`

## content_specialist (slice 1)

- Allowed: `knowledge_retrieval`
- Denied: web search, source fetch, workflows, advertising
- Mode: read; max_calls: 0 for the telegram draft path
