# Marketsynth Subsystem Standard

**Status:** canonical Source of Truth for designing any substantial Marketsynth capability  
**Phase introduced:** H2.8E Slice 0  
**Related:** [adr_subsystem_standard.md](adr_subsystem_standard.md) · [subsystem_compliance_matrix.md](subsystem_compliance_matrix.md)

---

## 1. Purpose

This standard prevents isolated “feature scripts” and incomplete product slices.

A capability is **not complete** merely because a Python service, UI component, or API endpoint works.

New domains, skills, integrations, and execution paths **must be evaluated against this standard before implementation**.

Applies to image generation, content, research, Make/n8n, Telegram, YouTube, sites, advertising, and future HR/legal modules.

---

## 2. Mandatory subsystem lifecycle

```
Discovery
→ Setup
→ Configuration
→ Verification
→ Readiness
→ Operation
→ Review
→ Maintenance
→ Deprecation
```

| Stage | Meaning |
|-------|---------|
| Discovery | What capability is needed; what is out of scope |
| Setup | Credentials, migrations, provider connection (never silent in user requests) |
| Configuration | Flags, quotas, tool profiles, policy versions |
| Verification | Prove connection/capability without claiming product success |
| Readiness | Typed preflight; blocking conditions; user-facing messages |
| Operation | Governed execution against frozen inputs |
| Review | Owner/human or policy review; quality gate outcomes |
| Maintenance | Runbook, health, cost control, recovery |
| Deprecation | Migration / replacement policy |

---

## 3. Subsystem definition

A **Marketsynth Subsystem** is a bounded product capability that includes:

| Element | Required |
|---------|----------|
| Domain boundary | Yes |
| Contracts (`contracts.py` first) | Yes |
| Configuration | Yes |
| Integration dependencies | When external |
| Credentials boundary | When secrets exist |
| Capability registry | When providers/tools vary |
| Admission policy | When inputs are admitted to execution |
| Source-of-Truth manifest or durable state | Yes for governed execution |
| Operator / orchestration | When multi-stage workflow |
| Tool profile | When tools participate |
| Knowledge pack | Where applicable |
| Prompt package | Where applicable |
| Quality gate | Yes for user-facing results |
| Approval boundary | When paid/write/risky actions |
| Review lifecycle | Yes for identity / publish / verdict-class outputs |
| Lineage | Yes |
| Readiness | Yes |
| Health diagnostics | Yes |
| Cost / quota policy | When paid or limited |
| Recipes | Recommended |
| Runbook | Yes for operators |
| Security and retention policy | Yes |
| Tests and invariants | Yes |
| Deprecation / migration policy | Yes |

A single Python service, UI component, or skill is **not** a complete subsystem.

---

## 4. Canonical logical structure

Logical responsibilities (folder layout may follow existing repo architecture):

```
Subsystem
├── contracts
├── registry
├── admission
├── manifest / durable SoT
├── operator
├── adapters
├── policies
├── readiness
├── quality
├── review
├── lineage
├── recipes
├── runbook
└── tests
```

Do **not** invent a second Runtime, second Agent Registry, or parallel Asset store to satisfy this structure.

---

## 5. Setup vs Operation

### Setup

- credentials;
- configuration;
- migrations;
- provider connection;
- verification;
- capability discovery.

### Operation

- user request;
- governed execution;
- result;
- quality gate;
- review;
- lineage.

**Rules:**

- No setup action may happen silently during user execution.
- No provider credential or migration may be repaired automatically during an ordinary product request.

---

## 6. Operator pattern

An **Operator** is a deterministic, resumable, and auditable orchestration service for a bounded workflow.

An Operator is **not**:

- an AgentType;
- an autonomous planner;
- a parallel Runtime;
- an unrestricted background worker.

Every Operator must define:

- inputs;
- stages;
- state;
- retries;
- idempotency;
- stop conditions;
- approvals;
- outputs;
- lineage;
- recovery procedure.

---

## 7. Manifest / Source of Truth pattern

Borrowed idea: explicit immutable index / manifest.

**Implementation in Marketsynth:** PostgreSQL + typed JSON + versioning + lineage — **not CSV as primary storage**.

A manifest freezes exact execution inputs:

- versions;
- selected materials;
- excluded materials and reasons;
- configuration;
- policy version;
- hashes;
- provider capability;
- execution mode.

Examples:

- `IdentityReferenceManifest`
- `KnowledgeSnapshot`
- `EvidenceSnapshot`
- `PublicationPackage`
- `ResearchSourceManifest`
- `CampaignExecutionManifest`

---

## 8. Recipe pattern

A **Recipe** is a governed reusable scenario.

It declares:

- user goal;
- required inputs;
- participating subsystem;
- skill / operator;
- tools;
- knowledge;
- provider capability;
- approvals;
- quality gate;
- review;
- prohibited actions;
- output contract.

A Recipe is **not** a new product skill and is not executable outside subsystem policies.

---

## 9. Integration package standard

Every external integration must expose:

- registry entry;
- configuration contract;
- credential boundary;
- supported capabilities;
- allowed read actions;
- allowed write actions;
- approval requirements;
- health state;
- quotas / limits;
- cost policy;
- known limitations;
- operator / runbook;
- safe errors.

Later apply to: OpenAI, OpenRouter, Firecrawl, XMLRiver, Make, n8n, Telegram, YouTube, WordPress, advertising, analytics.

This slice creates the standard and identifies gaps — **no mass integration refactor**.

---

## 10. Ephemeral processing policy

```
download or receive
→ validate
→ process
→ persist approved durable result
→ delete temporary copy
```

Temporary provider/input files:

- are not a second Asset store;
- have bounded lifetime;
- must not contain credentials;
- must be removed after success or failure;
- must be covered by recovery cleanup.

---

## 11. Honest capability policy

Forbidden:

- claiming multiple references were transmitted when only one was sent;
- calling style guidance “identity preservation”;
- calling advisory output “evidence”;
- calling draft approval “execution approval”;
- silent provider fallback;
- silent mock success;
- unsupported write operations.

Required capability states (where applicable):

- `supported`
- `partially_supported`
- `unsupported`
- `unverified`
- `unavailable`

(Subsystem-specific enums may map to these concepts.)

---

## 12. One Runtime rule

Marketsynth keeps **one** product Runtime / Agent OS.

Subsystems extend that Runtime. They do not fork:

- a second Agent Registry;
- a second Task engine;
- a second Approval engine (unless explicitly phased);
- a parallel Asset store;
- a folder/CLI-driven alternate runtime.

---

## 13. Evaluation checklist (before coding)

1. What is the domain boundary?
2. What contracts are new vs reused?
3. Setup vs Operation separation clear?
4. What is the SoT / manifest?
5. What is the Operator (if multi-stage)?
6. What readiness / quality / approval / review exist?
7. What recipes and runbook will ship?
8. What honest capability claims are allowed?
9. What must **not** be auto-run or silently repaired?
10. Tests / invariants defined?

---

## 14. Reference implementation

H2.8E Identity Generation maps to this standard:

| Standard element | H2.8E realization |
|------------------|-------------------|
| Registry | Identity Provider Registry |
| Admission | Identity Reference Admission |
| Manifest | `IdentityReferenceManifest` |
| Operator | `IdentityQualificationOperator` |
| Readiness | Identity Generation Readiness |
| Approval | Paid A/B Call Approval |
| Quality | Visual Consistency Assistance |
| Review | Owner Identity Review |
| Recipes | creative / style / identity / logo / qualification |
| Runbook | [identity_generation_operator_runbook.md](../identity_generation_operator_runbook.md) |
| Lineage | UserRequest → Manifest → Qualification Run → Provider Call → Asset → Review → Capability Decision |

See [h2_8e_identity_subsystem.md](../h2_8e_identity_subsystem.md).
