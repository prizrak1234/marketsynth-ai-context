# Error Handling

Status: ACTIVE

Errors must:

- never leak secrets;
- use domain-specific codes;
- normalize provider failures;
- preserve auditability.

Log metadata, not credentials.
