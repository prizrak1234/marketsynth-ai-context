# ERROR_HANDLING_MODEL.md

**Project:** Marketsynth  
**Document Type:** Error Handling Architecture Specification  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from SECURITY_MODEL.md, EXECUTION_MODEL.md, CONTRACT_GUIDELINES.md

---

# 1. Purpose

This document defines error handling for Marketsynth.

Errors must be safe, normalized, auditable, and useful.

# 2. Core Law

Errors MUST NOT leak secrets, credentials, raw provider dumps, unrelated tenant data, or unsafe internal implementation details.

# 3. Error Categories

Canonical categories:

- validation_error
- authentication_error
- authorization_error
- ownership_error
- tenant_boundary_error
- approval_required
- approval_invalid
- execution_not_ready
- invalid_state_transition
- provider_timeout
- provider_rate_limited
- provider_unavailable
- provider_bad_request
- provider_auth_failed
- secret_boundary_violation
- invariant_violation
- unknown_error

# 4. Public Error Shape

```yaml
code:
safe_message:
correlation_id:
details:
retryable:
severity:
```

# 5. Internal Error Shape

Internal errors MAY include original_error_type, component, stack_reference, provider, and raw_reference, but MUST remain safe.

# 6. Provider Error Normalization

Provider-specific failures SHOULD be mapped into domain-safe errors.

# 7. Retry Policy

Retry only safe transient failures: timeout, rate limit, temporary provider unavailable, transient network failure.

Do not retry authentication failure, authorization failure, approval invalid, tenant boundary violation, invalid contract, or bad request caused by system bug.

# 8. Execution Error Handling

Execution errors SHOULD preserve job state, record safe failure evidence, avoid duplicate external effect, permit explicit replay if valid, and emit audit event.

# 9. AI Error Rules

AI agents MUST NOT expose raw exceptions, remove error handling to pass tests, convert critical invariant errors into warnings, or retry unsafe operations blindly.

---

# Audit Status

PASSED.

This document is FROZEN v1.0.0.
