# UserRequest Skill Context (Phase H2.5)

On route resolve (especially `content` → `content.telegram_post`):

1. Resolve skill + capability pack  
2. Evaluate clarification / skill inputs  
3. If incomplete → `needs_clarification` (no snapshot)  
4. If complete → retrieve approved knowledge → create snapshot → `ready_for_draft`

## Persisted fields

`skill_code`, `skill_version`, `capability_pack_code/version`, `knowledge_snapshot_id/hash`, `execution_readiness`, `missing_inputs`, `quality_profile_code`, `skill_inputs`.

## Hard guarantee

`ready_for_draft` **does not** call LLM, AgentRun, tools, or publication.

Implementation: `app/domain/user_request_skill_context.py`, `UserRequestService`.
