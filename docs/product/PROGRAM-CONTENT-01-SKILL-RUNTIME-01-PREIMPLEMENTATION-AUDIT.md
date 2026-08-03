# PROGRAM-CONTENT-01-SKILL-RUNTIME-01 — Pre-implementation Audit

> Status: **docs_verified** · 2026-08-02  
> Task: Marketsynth Product Skill Runtime MVP  
> Archives audited under `.tmp_skill_runtime_audit/` (no script execution)

## Pre-implementation check

1. **Task ID:** PROGRAM-CONTENT-01-SKILL-RUNTIME-01 · **Priority:** P0 sole active  
2. **Inspect/change:** `app/schemas/contracts.py`, new `app/product_skills/`, alembic `0067`, Content Director adapter wire, settings Skills UI, tests  
3. **Current:** MSP `SkillManifest` + quarantine validator = catalog only; marketing skills = campaign parallel; Content Director uses thin LLM adapter; XMLRiver search tool exists; Avito **missing**  
4. **Target:** Import → validate → version → permissioned run → Copywriter/XMLRiver/Avito product skills  
5. **In/out:** Per owner TZ §18 — no marketplace, no ZIP sandbox, no Avito write, no Image Runtime  
6. **Invariants:** default deny · no secret in package · no subprocess from ZIP · tenant isolation · ContentAsset SoT for text  
7. **Migrations:** Yes (`product_skill_*` tables)  
8. **Tests:** importer/router/runtime/copywriter/xmlriver/avito oracles + Playwright skills list  
9. **Verify:** pytest · typecheck · build · e2e  
10. **Contradictions:** Existing MSP lifecycle ≠ commercial install statuses — **adapter mapping** (B), not second registry of truth for MSP research packages  
11. **Owner decision:** none blocking — TZ locks no-script-exec, secret aliases, Avito unconfigured, Settings→Skills surface

## Archive inventory (sanitized)

| Package | Size (zip) | Content | Scripts | Secrets in package | Runtime class |
|---------|------------|---------|---------|-------------------|---------------|
| Copywriter | 36 KB | `SKILL.md`, `system_prompt.md`, `rag_examples.json` | **0** | none | instruction |
| XMLRiver Wordstat | 28 KB | `SKILL.md`, refs, `scripts/*.py` | **8** (reference only) | documents `XML_RIVER_*` aliases | integration → registered tools |
| Avito | 9.1 MB | docs/OpenAPI archive + `SKILL.md` + doc sync scripts | **6** (doc tooling) | none in package | integration · install unconfigured |

Removed from import composition: `__MACOSX`, `._*`, `.DS_Store`.

**XMLRiver note:** package scripts read `.env` and call `http://xmlriver.com/...` — **forbidden as commercial exec**. Logic ported to audited backend tools using existing `XMLRIVER_USER_ID` / `XMLRIVER_API_KEY` via secret alias binding.

**Avito note:** package is documentation research skill for Cursor-style agents, not a live client. MVP: install docs provenance + `installed_unconfigured`; read tools stubbed until credentials.

## Reuse map

| Element | Class | Action |
|---------|-------|--------|
| `SkillManifest` / package_validator / quarantine | **B** | Inspiration + path/secret/exec checks; Product Runtime has own manifest + install statuses |
| ToolRegistry + permissions | **A** | Register wordstat.* tools |
| Content Director + ContentRun | **A/B** | Domain SoT for text; SkillRun lineage |
| `resolve_llm_config` / LLM adapters | **A** | Copywriter instruction path |
| XMLRiver settings + XmlRiverSearchTool | **B** | Wordstat endpoints as new tools; bind existing secrets |
| Marketing skill executors | **D** | Not Creative Platform path |
| Cursor/Claude ZIP format | **E** | Import format only |
| Unified CapabilityRun / ApprovalRecord | **F** | SkillRun mirrors Fabric statuses locally |
| AVITO config | **F** | Add optional SecretStr fields; unconfigured until set |
| Settings UI | **C** | Replace legacy diagnostics with commercial Skills panel |
| Subprocess sandbox | **E/F** | Explicitly out of MVP |

## Locked architecture (from TZ)

- ZIP/SKILL.md = import format; **ProductSkillManifest** = runtime SoT  
- No arbitrary Python/shell from package  
- Integration skills call registered ports only  
- Secret aliases only in packages  
- Router uses compact index, not full corpus  
- Fallback: no hidden mock; unconfigured ≠ available  

## STOP conditions

None for this TZ. Proceed to implementation.
