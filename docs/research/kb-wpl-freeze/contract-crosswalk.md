# Contract crosswalk

- Capability Model skill bindings → real `packages/skills/` packages or explicit gaps
- Pattern bindings → `KNOWN_PATTERN_IDS` (20 frozen WPL patterns)
- Discovery aliases → valid capability IDs in capability model
- Engineering Skills → valid pattern references in manifests
- Presentation Architecture → WPL pattern references only (no renderer)
- Discovery routes → Capability Model contracts; `runtime_authorized=false`

No stale IDs, hash drift, or orphan indexes detected in integrated audit.
