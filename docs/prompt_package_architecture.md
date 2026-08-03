# Prompt Package Architecture

A PromptPackage is a versioned lineage record of an assembled specialist
prompt. It stores hashes and versions only — never hidden reasoning, never
secrets, never raw provider dumps.

Contract: `PromptPackage` in `app/schemas/contracts.py`.

Fields of note:

- `constitutional_prompt_version`
- `role_prompt_version`
- `skill_instruction_version`
- `output_schema_version`
- `quality_profile_version`
- `tool_policy_version`
- `knowledge_snapshot_id` / `knowledge_snapshot_hash`
- `rendered_hash`
