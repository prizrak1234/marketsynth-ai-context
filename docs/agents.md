# Agents (placeholder)

**Do not implement LangGraph agents in the foundation phase.**

Future agents will:

- Consume `app/schemas/contracts.py` models only
- Run behind `app/domain/agents/` and `app/services/llm/`
- Never bypass PII sanitization or logging rules in `app/core/security.py`

Agent registry and n8n bridge will be documented here in phase 3.
