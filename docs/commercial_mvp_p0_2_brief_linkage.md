# Commercial MVP P0.2 — ProjectBrief linkage

Investigation creation requires:

1. Valid Project owned by caller
2. Existing **submitted** ProjectBrief for same Project/owner
3. Exact `project_brief_id`, `project_brief_version`, `input_fingerprint` match

Rejected:

- draft Brief (`brief_not_submitted`)
- wrong version / fingerprint
- Brief from another Project
- local-only draft without backend ID

## Versioning

- First Investigation `version` = 1
- New Investigation increments version per Project
- Explicit supersede from completed creates next version and marks prior `superseded`
- No silent overwrite; history readable via list

Fingerprint at create is stored on Investigation for audit; Brief remain SoT for intake content.
