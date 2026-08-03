# H2.8 — Content Expertise, Evidence & Editorial Quality

Single-skill editorial pipeline for `content.telegram_post`. No new product skills, no publication, no multi-agent Runtime.

## Pipeline

1. **Domain classification** — `app/domain/content_domain_classifier.py` (deterministic RU/EN rules).
2. **Knowledge retrieval** — domain pack `content.domain.drilling_safety.v1` ranked above generic methodology when domain matches.
3. **Draft** — one LLM call (or mock).
4. **Claim verification** — `app/services/content_claim_verification.py` (internal skill).
5. **Editorial review** — `app/services/content_editorial_review.py` (internal skill).
6. **Strict quality gate** — `app/services/content_quality_gate.py`.
7. **Optional revision** — at most one extra LLM call when gate = `revise`.

## Quality gate

| Score | Decision | User copy |
|-------|----------|-----------|
| ≥ 0.85 | `pass` | «Готово…» |
| 0.70–0.84 | `revise` (once) | retry or «требует доработки» |
| &lt; 0.70 or critical | `block` | «Черновик сохранён, но не прошёл редакторскую проверку» |

Critical failures include duplicated CTA, unsupported exact statistics, generic filler dominance.

## Factuality default

`general_expert` — domain pack only. `source_backed` (explicit flag) may allow bounded web search in a later slice; default content path remains knowledge-only.

## Regression

```bash
uv run pytest tests/test_phase_h2_8_content_expertise.py -q
uv run pytest tests/test_phase_h2_7_specialist_execution.py -q
```

## UI

`SpecialistActivityCard` shows expertise labels, domain-aware materials counts, collapsed **«Основание текста»** from `text_foundation`, and blocked state when `gate_decision != pass`.
