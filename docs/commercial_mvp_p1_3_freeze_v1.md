# Marketsynth Commercial MVP Backend Baseline v1.0

Frozen after P1.3 audit.

## Includes

- Domain boundaries for ProjectBrief → … → ImplementationPlan → Handoff → MarketingPlan draft
- Canonical lineage + version pins
- Lifecycle rules (no silent auto-downstream except explicit handoff confirm → draft)
- Ownership via project owner auth
- Immutability of approved/accepted commercial records
- Draft-only handoff semantics + execution firewall
- Frontend integration contracts (mock/backend/hybrid honesty)

## Allowed post-freeze

- Correctness/security patches
- Browser E2E
- Performance / observability
- Controlled pilot hardening
- Future V2.2 implementation under architecture decision

## Forbidden without architecture decision

- Collapsing domains
- Bypassing lineage / floating parents on write
- Automatic downstream creation beyond documented handoff
- Automatic execution
- Replacing MarketingPlan or Product Alpha UX baseline
