# BotFazer / Marketsynth — Project Vision

> **Positioning (2026-07):** Marketsynth is an **AI Business Operating System** — a platform to create, launch, and grow a business from idea to scale. Marketing is one subsystem, not the whole product.  
> **Trilogy:** [Platform Map](product/MARKETSYNTH-PLATFORM-MAP.md) (what) · **[Operating Model](MARKETSYNTH-OPERATING-MODEL.md)** (how it works together)

## Final goal

**Marketsynth must help an entrepreneur pass the full path from idea to scaling** — with marketing production as a major capability, not the only one.

The near-term commercial wedge remains: **validate before spend, then launch with evidence** (BIV → Strategy → Readiness → Campaign → Execution).

Historically: *replace a marketing agency* — still true for the marketing conveyor, now nested inside a broader Business OS.

## What BotFazer is not

- **Not a chatbot** — conversation is an interface, not the product.
- **Not an agent builder** — users do not pick agents, wire nodes, or design LangGraph flows.
- **Not a Make/n8n clone** — legacy workflows are reference material, not runtime.

## What BotFazer is

A **business operating system for marketing** (Agent OS):

- The user describes a **business goal** (leads, launch, content engine, traffic diagnostics).
- The system proposes **scenarios, campaigns, skills, workflows, and next actions**.
- The user **confirms** critical steps; nothing auto-runs skills, tools, publishing, or background workers unless an explicit phase allows it.

## Primary user journey

```
Business Operator
  → Campaign
  → Brief
  → Skills
  → Tools
  → Workflow (checklist)
  → Content
  → Media
  → Publishing
```

| Stage | User expectation |
|-------|------------------|
| **Business Operator** | "I need dental leads" — not "run Wordstat node 3" |
| **Campaign** | One container for goal, scenario, artifacts, health |
| **Brief** | Structured business inputs before execution |
| **Skills** | Professional processes (segment research, offer packaging…) |
| **Tools** | Atomic capabilities (Wordstat, Metrica, image gen) invoked by skills or actions |
| **Workflow** | Reusable business process template inside a campaign — checklist, not auto-execution |
| **Content / Media / Publishing** | Production conveyor with review and approval |

## How the marketing agent must think

**Business-first, not tool-first.**

1. Understand goal, audience, offer, and success metric.
2. Identify gaps (supervisor) and recommend the next professional step.
3. Use tools only when they answer a business question.
4. Output conclusions and prioritized recommendations — never raw provider dumps.
5. Never invent data; never call a tool because it exists.

## Success criteria (product)

- A non-marketer can run a campaign end-to-end from Control Center.
- Every executable step is explicit (Action Center, skill run, approval).
- Quality gaps are visible before spend scales (supervisor).
- The architecture scales from rule-based v1 to LLM-assisted layers without breaking contracts.

## Strategic invariant

Every feature must move Marketsynth closer to **evidence-backed business operations** (validate → decide → approve → execute → learn) — not toward a generic AI chat, agent marketplace, or isolated feature island. See [MARKETSYNTH-OPERATING-MODEL.md](MARKETSYNTH-OPERATING-MODEL.md).
