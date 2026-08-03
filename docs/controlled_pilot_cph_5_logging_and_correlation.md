# CPH.5 — Logging and correlation

## Structured logs

`structlog` JSON (except interactive development console). Fields commonly present:

- timestamp, level, event
- `correlation_id` / `request_id` (bound per request)
- http_method, http_path
- safe user/project IDs when services log them

PII sanitizer remains enabled by default.

## Correlation IDs

- Accept `X-Request-ID` or `X-Correlation-ID`
- Sanitize (alnum + `._-`, max 128)
- Echo both response headers
- Bind into structlog contextvars

Not an authentication token.

## Forbidden in logs

Passwords, cookies, raw session tokens, API keys, full Brief/Evidence, DB URLs with passwords, provider payloads.
