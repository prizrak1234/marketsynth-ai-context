# Architecture (High Level)

> **No implementation detail.** For code boundaries see [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md).  
> **Operating model:** [docs/MARKETSYNTH-OPERATING-MODEL.md](../docs/MARKETSYNTH-OPERATING-MODEL.md)

---

## System definition

Marketsynth = **AI Business OS** running a unified loop:

```
observe → decide with evidence → approve → execute → measure → learn
```

Hosted in **Workspace** (projects), governed by **Human Approval**, recorded in **Knowledge**, executed via **Execution Layer**.

---

## Agent OS equation

```
Agent = Instructions + Knowledge + Skills + Tools + Memory + Workflows + Commands + Supervisor
```

See [docs/AGENT_OS_ARCHITECTURE.md](../docs/AGENT_OS_ARCHITECTURE.md).

---

## Major components

| Component | Responsibility |
|-----------|----------------|
| **FastAPI app** (`app/`) | HTTP API, thin handlers |
| **Contracts** (`app/schemas/contracts.py`) | Pydantic types — schema SoT |
| **Domain** (`app/domain/`) | Business rules |
| **Services** (`app/services/`) | LLM, Telegram, Redis, external systems |
| **DB** (`app/db/`) | Persistence (SQLAlchemy) |
| **Core** (`app/core/`) | Config, logging, security |
| **Commercial workflow** (`app/commercial_workflow/`) | CWF.1 decision branches, launch pack |
| **BIV** (`app/business_idea_validation/`) | Idea validation runtime |
| **Marketing** (`app/marketing/`) | Plans, scenarios, skills, campaigns |
| **Identity** (`app/identity_generation/`) | H2.8E subsystem (gated) |
| **Knowledge runtime** (`app/knowledge/`) | Discovery, catalog, patterns, linking |
| **Frontend** (`frontend/` or workspace UI) | Commercial Home, workspace routes |

**Invariant:** No second Runtime or Agent Registry. Subsystems follow [Subsystem Standard](../docs/architecture/marketsynth_subsystem_standard.md).

---

## Runtime model

- **Explicit execution only** — skills, tools, publishing, paid media require user/action-center trigger.
- **No background workers** for campaign progression (scheduler = explicit due scan + dispatch).
- **Dry-run vs real** — publication jobs distinguish modes; real Telegram requires approval + config.
- **Sanitization** — inbound text via `app/core/security.sanitize_payload` before processing/logging.

---

## Module dependency direction

```
Knowledge → informs → Skill → may use → Tool
                ↓
         Workflow (checklist)
                ↓
           Campaign
                ↓
      Business Operator
```

Supervisor is **read-only** — reports gaps, never executes.

---

## Subsystems (governed capabilities)

| Subsystem | Phase | Status |
|-----------|-------|--------|
| Business Idea Validation | CMVP.1 | Accepted |
| Commercial Workflow / Launch Pack | CWF.1 | Active |
| Marketing Department v2 | AI.119 | Frozen |
| Campaign Layer + Operator | AI.185–205 | Frozen |
| Publishing (Telegram) | AI.75 | Frozen |
| Video Studio | VS.2A | Frozen |
| Identity Generation | H2.8E | Gated |
| Knowledge Governance | KG.1–2 | Architecture + partial ops |
| KB-WPL Program | KB-WPL-01 | Closed (2026-07-24) |

Compliance matrix: [docs/architecture/subsystem_compliance_matrix.md](../docs/architecture/subsystem_compliance_matrix.md)

---

## Integration boundaries

| Integration | Role | Gate |
|-------------|------|------|
| **Telegram** | Real publication | Bot token, human approval |
| **OpenAI / LLM** | Analysis, content | Config via `.env` |
| **Wordstat / Metrica** | Marketing tools | Explicit tool calls |
| **Higgsfield MCP** | Media generation | CONN-HF-01.1L owner token gates |
| **n8n workflows** | Reference library | Download only, no execution |

---

## Frontend architecture (conceptual)

- **Commercial Home** — intent cards → governed routes (CWF.1a)
- **Workspace** — project-scoped artifacts, BIV, launch pack, campaigns
- **Owner preview** — gated features (`?owner_preview=video`, content factory)
- **Legacy Alpha routes** — frozen parallel paths (do not extend)

---

## What architecture explicitly rejects

- LangGraph marketing orchestration (unless explicit phase)
- Parallel specialist auto-execution
- Auto ContentAsset creation from chat
- VectorDB as hallucination layer for KG v1
- Make/n8n as default runtime execution engine
