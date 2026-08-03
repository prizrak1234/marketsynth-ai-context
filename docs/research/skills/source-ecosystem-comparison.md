# Skill Source Ecosystem Comparison

**Phase:** SKILL-R0.1  
**Date:** 2026-07-23  
**Compared:** Corey Haines marketingskills · Anthropic skills · VoltAgent awesome-agent-skills · Marketsynth internal methodology

---

## Executive comparison

| Criterion | marketingskills | Anthropic skills | VoltAgent awesome-agent-skills | Marketsynth internal |
|-----------|-----------------|------------------|-------------------------------|----------------------|
| **Package format** | Agent Skills spec (`SKILL.md` + folders) | Same + `spec/` + template | Catalog links — **not a single format** | Python registry + contracts + operators |
| **Activation model** | Agent auto-select via description | Progressive disclosure (metadata → SKILL.md → resources) | Discovery only | Explicit specialist / operator execution |
| **Portability** | High across Claude Code/Cursor | High | N/A (index) | N/A — product-bound |
| **Test coverage** | Claims 40+ skills / 251+ eval cases (v2.0.0 release notes) — **Requires technical validation** | Example vs production separation; validation via `skills-ref` | None — catalog | Pytest phase suites (BIV, CWF, marketing frozen phases) |
| **Eval support** | First-class in repo history | Patterns in skill-creator | None | Partial — domain tests, not skill eval harness |
| **Resource bundling** | `references/`, optional scripts | `scripts/`, `references/`, `assets/` | Links only | DB + knowledge snapshots + contracts |
| **Scripts** | Some skills — **must not run in production path** | Document production skills include scripts | Unknown per entry | Python services only |
| **Security** | Markdown + optional scripts — supply chain if installed wholesale | Same + MCP examples separated | **High discovery risk** — unvetted links | Sanitize + gateway + approval gates |
| **Licensing** | MIT (verified LICENSE) | Apache-2.0 / mixed — verify per skill | Mixed — per upstream repo | Proprietary product |
| **Marketing depth** | **High** — 40+ marketing skills | Broad (docs, design, MCP examples) | Broad catalog | CWF.1 commercial workflow |
| **Production readiness** | **Not production dependency** | Format reference, not wholesale import | **Reject as trust root** | Production path |
| **Adaptation cost** | Medium — rewrite to contracts/Evidence | Low for format; medium per skill | N/A | Baseline |
| **Maintenance risk** | External repo drift | Spec drift low | Catalog rot / link breakage | Internal ownership |

---

## Decision posture per source

### Corey Haines marketingskills

| Aspect | Decision |
|--------|----------|
| Methodology | **Adapt** (P0/P1 skills) |
| Package structure | **Adapt** (align MS skills to agentskills.io) |
| Eval/test patterns | **Adapt** as reference for MS skill quality system |
| Direct installation | **Reject** in SKILL-R0 / production |

**Rationale:** Strongest marketing methodology corpus found; MIT license; integrates product-marketing context pattern compatible with Marketsynth governed context — but filesystem activation and missing Evidence/Approval gates forbid drop-in.

### Anthropic skills repository

| Aspect | Decision |
|--------|----------|
| Agent Skills specification | **Adopt** (format/spec patterns) |
| skill-creator / document-production patterns | **Adapt** selectively |
| Bundled example skills | **Defer** — evaluate individually |
| Direct production install | **Reject** |

**Rationale:** Architectural reference per [agentskills.io/specification](https://agentskills.io/specification) — not automatic approval of every included skill.

### VoltAgent awesome-agent-skills

| Aspect | Decision |
|--------|----------|
| Catalog use | **Research / discovery only** |
| Trust root | **Reject** |
| Auto-install | **Reject** |

**Rationale:** Discovery catalog, not vetted production source — same class as MCP Registry (find candidates, then audit).

### Marketsynth internal methodology

| Aspect | Decision |
|--------|----------|
| CWF.1 / BIV / Launch Pack | **Continue** — primary SoT |
| Specialist skills registry | **Adapt** — ingest external methodology as internal subskills |
| External skill marketplace UI | **Reject** |

---

## Quality system implications (architecture inference)

Marketsynth should **Adapt** from marketingskills:

1. Per-skill eval cases tied to MS-SKILL IDs.
2. Version metadata in skill manifests.
3. Separation of **production** vs **example** skills (Anthropic pattern).
4. Progressive disclosure — metadata for routing, full instructions on activation.

Must **not** copy blindly:

- `.agents/` workspace files as SoT.
- OAuth/integration layers without Connector Gateway.
- Auto-activation without explicit operator run + audit log.

---

## Licensing summary

| Source | License | Marketsynth use |
|--------|---------|-----------------|
| marketingskills | MIT (verified) | Adapt methodology with attribution |
| Anthropic skills | Mixed — check per skill | Adopt spec; Adapt skills individually |
| VoltAgent catalog | N/A | No redistribution |
| Internal | Proprietary | SoT |

**Requires legal review:** Higgsfield/generative outputs (separate MCP card), commercial API ToS (XmlRiver, Firecrawl).

---

## Sources

- https://github.com/coreyhaines31/marketingskills
- https://raw.githubusercontent.com/coreyhaines31/marketingskills/main/LICENSE
- https://github.com/anthropics/skills
- https://agentskills.io/specification
- VoltAgent awesome-agent-skills — discovery catalog (**specific URL not pinned in this audit — Requires verification**)
- `app/specialist_skills/`, `docs/PRODUCT_CONSTITUTION.md`, CWF.1 rules
