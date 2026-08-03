# Commercial MVP P0.3 — Source Domain

## Outcome

Durable, **immutable**, versioned, owner/project-scoped **Source** registry for information provenance.

Source answers only: *Where did this information come from?*  
Evidence (P0.4) answers: *What does this prove?*

## Ownership / reuse

- `project_id` required; reuse within Project only
- `InvestigationSourceLink` for Investigation usage (many-to-many, no row duplication)
- Cross-project / cross-owner forbidden

## Schema (no analysis fields)

Identity + provenance: type, provenance_type, title, origin, url, domain, publisher, language, country, dates, freshness, reliability, status, fingerprint, content_hash, etag, version, supersedes_source_id, license, capabilities, bounded metadata.

**Forbidden:** conclusion, proof, reasoning, verdict, analysis, recommendation, summary, evidence body, document dump.

## SourceSnapshot

Architectural contract (route `GET .../snapshot`) representing one captured origin state — not a separate table in P0.3.

## Inventory (not Source)

| Artifact | Role | Reuse as Source? |
|----------|------|------------------|
| ProjectBrief materials_summary | Intake metadata | Candidate only (explicit mapping) |
| MarketingSkillRun | Skill output | No (conclusions) |
| Supervisor findings | Quality signals | No |
| LLM request/response | Model traffic | No |
| Publication assets | Publish artifacts | No |
| Product Alpha mock sources | UX preview | Mock/hybrid labelled only |

## Confirmations

No external fetch, file processing, Evidence, Agent Run, LLM, Verdict, Strategy. A7 / AI.592 / V2.2 paused.

## Docs

- [API](commercial_mvp_p0_3_source_api.md)
- [Provenance & reliability](commercial_mvp_p0_3_provenance_and_reliability.md)
- [Versioning & fingerprint](commercial_mvp_p0_3_versioning_and_fingerprint.md)
- [Investigation linkage](commercial_mvp_p0_3_investigation_linkage.md)
- [Materials mapping](commercial_mvp_p0_3_materials_mapping.md)
- [Migration](commercial_mvp_p0_3_migration_and_rollback.md)

## Tests

`uv run pytest tests/test_commercial_mvp_p0_3_source.py -q`
