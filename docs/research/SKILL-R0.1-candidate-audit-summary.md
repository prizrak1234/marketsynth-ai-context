# SKILL-R0.1 — Candidate Audit Summary

**Phase:** SKILL-R0.1 — Candidate Audit Pack  
**Date:** 2026-07-23  
**Status:** Complete (documentation only)  
**Product track:** CWF.1 **unchanged**

---

## 1. Executive verdict

SKILL-R0.1 confirms the owner hypothesis: **Marketing Skills and MCP connectors must remain separate trusted contours.** No external Skill or MCP candidate is approved for direct production installation in this phase.

| Contour | Verdict |
|---------|---------|
| **P0 Skills (MS-SKILL-001..007)** | **Adapt** — internalize methodology with Evidence, Approval, tenant contracts |
| **P0 Connectors** | XmlRiver/Firecrawl **Adapt** (baseline); Higgsfield **Adapt** (gateway pilot); Playwright **Defer**; Telegram MCP **Reject** |
| **Agent Skills spec (Anthropic/agentskills.io)** | **Adopt** for package format only |
| **marketingskills repo** | **Adapt** methodology + quality patterns — **Reject** drop-in install |
| **MCP Registry / Smithery** | Registry = discovery only; Smithery = **Reject** for production trust |

**Quality rule applied:** Cards with explicit **Unknown / Defer** preferred over unsupported Adopt claims.

---

## 2. Scope completed

| Deliverable | Count | Location |
|-------------|-------|----------|
| Skill audit cards | 16 | `docs/research/skills/candidates/01–16` |
| MCP audit cards | 16 | `docs/research/mcp/candidates/01–16` |
| Browser research comparison | 1 | `docs/research/mcp/browser-research-comparison.md` |
| Skill ecosystem comparison | 1 | `docs/research/skills/source-ecosystem-comparison.md` |
| Matrix update (all candidates) | 32 rows + meta | `docs/research/adopt-adapt-reject-matrix.md` |

---

## 3. Sources reviewed

### Primary (source-verified)

- [Corey Haines marketingskills](https://github.com/coreyhaines31/marketingskills) — MIT LICENSE, SKILL.md samples (product-marketing, customer-research, offers)
- [Agent Skills specification](https://agentskills.io/specification)
- [Anthropic skills repository](https://github.com/anthropics/skills) (structure/spec reference)
- [Higgsfield MCP official page](https://higgsfield.ai/mcp) — endpoint, OAuth, models, credits FAQ
- [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) README — tool names
- Marketsynth internal: `app/mcp/registry.py`, XmlRiver/Firecrawl adapters, `docs/phase_ai_75_telegram_publishing_readiness_audit.md`

### Secondary (risk / ecosystem)

- Smithery supply-chain incident (GitGuardian, Jun 2025) — cited in owner research; **Requires security review** for any hosted proxy use
- MCP ecosystem OAuth misconfiguration research (2026) — architecture inference for deny-by-default gateway

### Not verified in this phase

- Higgsfield MCP `tools/list` JSON schemas
- VoltAgent awesome-agent-skills exact repo URL pinned
- Official Ahrefs / Google Ads / Meta MCP server identities
- marketingskills per-skill eval counts (repo release notes claim 251+ cases — **Requires technical validation**)

---

## 4. P0 Skill candidates (recommended next RFC inputs)

| ID | Candidate | Decision | RFC readiness |
|----|-----------|----------|---------------|
| MS-SKILL-001 | Product Marketing Context | Adapt | **Ready** — after context contract defined |
| MS-SKILL-002 | Market Research | Adapt | **Ready** — map to research_source_collection |
| MS-SKILL-003 | Competitor Analysis | Adapt | **Ready** |
| MS-SKILL-004 | ICP & Segmentation | Adapt | **Ready** — evidence threshold rules |
| MS-SKILL-005 | Market Validation | Adapt | **Ready** — extend BIV (already core) |
| MS-SKILL-006 | Positioning | Adapt | **Ready** |
| MS-SKILL-007 | Offer Builder | Adapt | **Ready** — Launch Pack mapping |

**Recommended RFC drafting order:** RFC-SKILL-002 (package format) → RFC-SKILL-001 (registry) → skill-specific RFCs for MS-SKILL-001 + MS-SKILL-005 integration.

---

## 5. P0 Connector candidates

| ID | Connector | Decision | Notes |
|----|-----------|----------|-------|
| MCP-001 | XmlRiver | Adapt | Existing baseline — document + tenant creds RFC |
| MCP-002 | Firecrawl | Adapt | Existing baseline — SSRF/pricing benchmark |
| MCP-003 | Higgsfield | Adapt | **Pilot only** — mandatory gateway; tool schema unknown |
| MCP-004 | Playwright | Defer | Benchmark vs Firecrawl; sandbox required |
| MCP-005 | Telegram MCP | **Reject** | Duplicates frozen native publish; bypasses approval |

**Recommended RFC:** RFC-CONN-001 (Connector Gateway + private registry) before Higgsfield pilot.

---

## 6. Adopt / Adapt / Reject / Defer totals

| Decision | Skills | MCP/Connectors | Meta |
|----------|--------|----------------|------|
| **Adopt** | 0 | 0 | 1 (Agent Skills **format spec** only) |
| **Adapt** | 13 | 3 | 1 (MCP Registry as discovery) |
| **Reject** | 0 | 4 | 1 (Smithery production trust) |
| **Defer** | 3 | 9 | — |

**Skills Defer:** MS-SKILL-013 (AI SEO), MS-SKILL-016 (Ad Creative — pending ad connectors)  
**Skills Adapt includes P1:** CRO, copywriting, SEO audit, content/social/visual/video briefs

---

## 7. Critical security findings

1. **MCP ecosystem immaturity** — deny-by-default; tool-level allowlist mandatory (not server-level).
2. **Telegram userbot MCPs** — full account access; **hard reject** vs native PublicationPackageJob path (AI.70–75).
3. **Higgsfield** — billing-sensitive async generation; OAuth token storage; **unknown tool surface** until sandbox `tools/list`.
4. **Playwright MCP** — write-capable browser automation; credential exfiltration risk if login allowed.
5. **Ad platform MCPs (Google/Meta/Yandex)** — uncontrolled spend — **Reject** direct MCP install.
6. **Smithery / hosted MCP proxies** — supply-chain incident history — **Reject** for production secrets/tenants.

**Mandatory architecture (confirmed):**

```
External MCP → Connector Gateway → server allowlist → tool allowlist
→ tenant credentials → budget/rate limits → human approval (writes)
→ evidence + audit log
```

---

## 8. Licensing findings

| Asset | Status |
|-------|--------|
| marketingskills | **MIT verified** — Adapt with attribution |
| Agent Skills spec | Open specification — **Adopt** patterns |
| Anthropic bundled skills | **Verify per skill** before any code reuse |
| XmlRiver / Firecrawl | Commercial API — **Requires legal review** for customer-facing use |
| Higgsfield generated content | **Requires legal review** — commercial use terms not verified |
| Community Telegram MCP | MIT (example repo) — irrelevant due to **Reject** |

---

## 9. Architecture implications

1. **Two registries:** Skill registry (`app/specialist_skills/` evolution) ≠ Connector registry (`app/mcp/` + gateway).
2. **Methodology ≠ installation:** All external marketing skills → internal subskills with contracts first.
3. **Native adapters preferred** over marketplace MCP bundles (XmlRiver/Firecrawl pattern).
4. **Quality system:** Adapt eval/version patterns from marketingskills; production vs example separation from Anthropic.
5. **Browser research:** Hybrid XmlRiver → Firecrawl default; Playwright deferred (see comparison doc).

---

## 10. CWF.1 impact

**None.** No runtime, API, migration, UI, or CWF.1 behavior changes in SKILL-R0.1.

Research informs future slices only:

- Launch Pack → Offer Builder (MS-SKILL-007)
- Content assets → copywriting/social skills
- Optional visuals → visual brief + Higgsfield gateway (post-RFC)
- Telegram publish → **native frozen path only**

---

## 11. Candidates ready for RFC

**Skills (commercial fit High, Adapt path clear):**

- MS-SKILL-001, 002, 003, 004, 005, 006, 007

**Connectors:**

- MCP-001, MCP-002 (hardening RFC)
- MCP-003 (pilot RFC after tool schema + legal)

**Meta:**

- RFC-SKILL-002 (Agent Skills package format — **Adopt** spec)
- RFC-CONN-001 (Connector Gateway + private registry)

---

## 12. Candidates blocked

| Candidate | Blocker |
|-----------|---------|
| MCP-005 Telegram MCP | Hard reject — duplicates native publish |
| MCP-009/010/011 Ad MCPs | Hard reject — ungated spend |
| Smithery production | Security supply-chain |
| Higgsfield production | Unknown tools + OAuth vault + content rights |
| Playwright production | Defer — benchmark + sandbox |
| MS-SKILL-013 AI SEO | Defer — unproven KPI/demand |

---

## 13. Recommended next phase

1. **Owner review** SKILL-R0.1 P0 cards (quality gate before P1 depth iteration sign-off).
2. **Draft RFC-SKILL-002 + RFC-CONN-001** (no implementation).
3. **Sandbox:** Higgsfield `tools/list` + single dry-run with audit log template.
4. **Benchmark:** Firecrawl vs Playwright on 5 URLs (document only).
5. **CWF.1a** owner browser acceptance (separate track — blocks CWF.1b).

Do **not** create RFC-SKILL-001/002/003 or RFC-CONN-001 files until owner accepts this audit pack.

---

## 14. Runtime unchanged confirmation

| Check | Result |
|-------|--------|
| Production code modified | **No** |
| CWF.1 behavior modified | **No** |
| External MCP installed | **No** |
| Executable Skill added | **No** |
| Database migrations | **No** |
| pyproject.toml / deps | **No** |
| API routes | **No** |

SKILL-R0.1 is **documentation-only**.

---

## Verification

```bash
# File counts
ls docs/research/skills/candidates/*.md | wc -l   # expect 16
ls docs/research/mcp/candidates/*.md | wc -l      # expect 16

# Docs-only diff
git diff --name-only
```

Manual checks performed:

- [x] All 32 candidate cards exist
- [x] Each card has Sources section and proposed decision
- [x] Matrix contains all candidates
- [x] Comparison docs created
- [x] Defer/Reject entries include blocking unknowns / hard reasons
