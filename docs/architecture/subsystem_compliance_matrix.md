# Subsystem Compliance Matrix

**Companion to:** [marketsynth_subsystem_standard.md](marketsynth_subsystem_standard.md)  
**Audit mode:** gap identification only — **no mass refactor** in H2.8E Slice 0.

## Legend

| Status | Meaning |
|--------|---------|
| `compliant` | Lifecycle + core elements present and honest |
| `partial` | Important pieces exist; gaps remain |
| `missing` | Substantial capability without subsystem framing |
| `not_applicable` | Does not require full subsystem shape |

Columns: boundary · registry · manifest/SoT · operator · readiness · quality · approval · review · lineage · recipes · runbook · **status** · gaps · recommended phase

---

## Matrix

| Subsystem / domain | boundary | registry | manifest/SoT | operator | readiness | quality | approval | review | lineage | recipes | runbook | status | gaps | recommended phase |
|--------------------|----------|----------|--------------|----------|-----------|---------|----------|--------|---------|---------|---------|--------|------|-------------------|
| Commercial Investigation | yes | partial (tools) | partial (Evidence) | partial (wizard/runs) | partial | partial | yes (explicit) | partial | yes | missing | partial | **partial** | no unified admission/manifest/recipes | dedicated investigation subsystem phase |
| BusinessVerdict | yes | n/a | yes (entity) | missing | partial | partial | yes | partial | yes | missing | missing | **partial** | operator + runbook + recipes | verdict subsystem polish |
| MarketingStrategy | yes | specialist registry | partial | dry-run exec | partial | partial | plan approve | partial | yes | missing | partial | **partial** | immutable strategy manifest | strategy packaging phase |
| ImplementationPlan | yes | n/a | maps_multiple | missing | missing | partial | handoff gates | partial | partial | missing | missing | **partial** | SoT clarity vs MarketingPlan | handoff hardening |
| MarketingPlan handoff | yes | plan versions | plan versions | execution runs | partial | specialist QC | approve + execute | yes | yes | scenarios | partial | **partial** | recipe catalog; readiness API | conveyor freeze + recipes |
| Knowledge Foundation | yes | knowledge types | KnowledgeSnapshot | missing | partial | governance | publish gates | yes | yes | missing | partial | **partial** | operator for import staging | knowledge ops phase |
| Knowledge Governance | yes | types+domains | KnowledgeGovernanceManifest + Object | planned (pipeline) | architecture | Benchmark + Citation | Human Review→Publication | yes | EvidenceChain+DecisionChain | deferred | developer guide + invariants | **partial** (contracts) | persistence/API/Operator not built; no VectorDB by design this phase | after Identity H2.8E diagnostic; KG persistence phase |
| Specialist Skills | yes | skill registry | skill run records | skill runs | partial | skill QC | explicit run | partial | yes | missing | partial | **partial** | recipes vs skills clarity | skills v2 recipes |
| Image Generation / Identity | yes | Identity Provider Registry | IdentityReferenceManifest | IdentityQualificationOperator | yes | visual consistency | paid call approval | owner identity review | yes | yes | yes | **partial→compliant target** | paid diagnostic not yet owner-run; Gate not accepted | finish H2.8E qualification |
| Authentication | yes | n/a | sessions/tokens | n/a | health | n/a | n/a | n/a | audit | n/a | partial | **partial** | runbook for ops recovery | security ops doc |
| Backup / Restore | yes | n/a | snapshots | ops scripts | partial | verify | admin | n/a | yes | n/a | partial | **partial** | formal operator stages | ops runbook phase |
| Make / n8n integrations | yes (blocked) | integration registry partial | n/a | blocked | flags | n/a | approval boundaries | n/a | n/a | n/a | external_execution_boundaries | **partial** | full integration package standard | only after explicit write-enable phase |
| Telegram publishing | yes | channel registry | PublicationPackage | job execute | flags | delivery logs | package approve | yes | yes | missing | yes (phase docs) | **partial** | recipes; ephemeral cleanup formalized | publishing recipes |
| Media generation (AI.56+) | yes | media providers | MediaBrief/Job | jobs | flags | safety | brief approve | partial | yes | missing | phase docs | **partial** | identity vs media boundary | keep frozen; identity via H2.8E |
| Campaign Control / Action | yes | actions | campaign state | action execute | control-center | supervisor | explicit actions | yes | yes | scenarios | phase docs | **partial** | CampaignExecutionManifest | campaign manifest phase |
| Business Operator | yes | intent→scenario | preview | assist/confirm | confidence gate | n/a | confirm | n/a | audit | scenarios | phase docs | **partial** | not a second Runtime (OK) | keep rule-first |

---

## Honest capability notes

- **Image / Identity:** OpenAI adapter is primary-only; must not claim multi-ref transmit.
- **Make / n8n:** write execution remains blocked behind approval boundaries.
- **Unit tests** must never mark identity provider `suitable_for_identity`.

## Intentionally not refactored in Slice 0

- No rewrite of Investigation / Verdict / Strategy / Plan domains.
- No mass Integration Registry HTTP surface.
- No second Runtime or Agent Registry.
- No paid identity diagnostic calls.
- No Campaign / publication / advertising write enablement.

## Next compliance moves (suggested order)

1. Complete H2.8E Identity qualification (owner diagnostic) under the standard.
2. Add CampaignExecutionManifest when campaign auto-orchestration expands.
3. Apply Integration Package Standard incrementally per provider (OpenAI first, then research adapters).
4. Recipe catalogs for MarketingPlan scenarios and Telegram publishing.
