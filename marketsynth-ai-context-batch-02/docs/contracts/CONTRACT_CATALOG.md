# Contract Catalog

Status: ACTIVE

## Rule

Contracts define public semantics. Implementation must conform to contracts.

## Core Contract Families

- Agent
- AgentRun
- LLMRequest
- LLMResponse
- Task
- Project
- MemoryItem
- ExecutionApproval
- PublicationPackage
- PublicationJob
- Evidence
- Outcome
- KnowledgeCandidate

## Every Contract Should Define

- identity;
- tenant / owner scope;
- status enum;
- input payload;
- output payload;
- metadata;
- timestamps;
- error model;
- allowed transitions.

## Ownership Rule

Any object linked to a tenant, owner or project must carry enough ownership context to enforce isolation.
