# Backlog

> **Never mixed with [05_ROADMAP.md](05_ROADMAP.md).** Items here are NOT approved for implementation until promoted by owner.  
> **Last updated:** 2026-07-29

---

## Product ideas

| Idea | Notes | Class |
|------|-------|-------|
| Full Launch Pack skill wiring | icp_segmentation, positioning, copywriting, visual_brief | A (after P0) |
| Review queue + Channels UI completion | Blocks publication journey L | A |
| Content Factory on main path | Currently owner preview only | A |
| SWOT/PEST product surfacing | Frameworks in knowledge corpus | D |
| Website Builder domain | Platform map planned | D |
| Yandex Direct campaign mode | Architecture doc exists | D |
| Business Intelligence module | Long-term | D |

---

## Technical improvements

| Item | Area | Notes |
|------|------|-------|
| Consolidate legacy Alpha routes | Frontend | Parallel to CWF home |
| market_validation v0.1 vs v0.2 ambiguity | Skills | Frozen hash is 0.2.0 |
| Discovery routes vs product UI gap | Knowledge | KB-WPL discovery not in Home |
| Git workspace sync | DevOps | Ensure .git available in Cursor workspace |
| SoT auto-update Cursor rule | Tooling | Hook post-session updates |

---

## Technical debt

| Debt | Risk | Source |
|------|------|--------|
| BIV parallel to ms.skill.market_validation | Dual maintenance | CWF-SKILL-INTEGRATION-GAPS |
| Intent cards → generic assistant for B–J | Bypasses governed skills | CWF audit |
| Recovery preview R3 orphan | Dead UI path | CWF audit |
| Offer Builder not frozen | Drift from CWF spec | AGENTS.md |
| 651+ docs without SoT index | Context loss on chat reset | This SoT creation |

---

## Research backlog (SKILL-R0)

| Topic | Location |
|-------|----------|
| Skill/MCP audit matrix | [research/](research/) |
| Browser research comparison | docs/research/mcp/ |
| Adopt-adapt-reject matrix | docs/research/adopt-adapt-reject-matrix.md |
| Archive marketer audit | docs/research/archive-marketer/ |

**Gate:** No runtime, no new MCP, no CWF.1 changes until RFC acceptance.

---

## Explicitly deferred (owner/class D–E)

- Skill marketplace / MCP marketplace
- CRM integration as product
- Billing and subscription management
- Analytics dashboard
- Instagram/LinkedIn publishing
- Identity video / long-form / montage
- KB-WPL-02 until Product P0 accepted
- CMVP.2 abstract platform work

---

## Promotion criteria (backlog → roadmap)

1. Owner explicit approval
2. Answers commercial-product-directive eight questions
3. Class A, B, or C priority
4. Phase doc or RFC accepted
5. Entry added to [05_ROADMAP.md](05_ROADMAP.md) and optionally [milestones/](milestones/)
