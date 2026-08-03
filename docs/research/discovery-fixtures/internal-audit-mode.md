# Internal audit mode fixtures

**Phase:** KB-WPL-01.8

## Normal mode (default)

- Quarantined workflow templates: **hidden**
- Rejected artifact references: **hidden**
- Cross-tenant private Skills: **hidden**
- Hidden artifacts absent from counts

## Internal audit mode

Requires: `internal_audit_mode=true`

Optional: `include_quarantined=true` (required to show quarantine metadata)

May additionally return:
- `quarantined_workflow_template`
- `rejected_artifact_reference`
- `practice_record`
- `error_pattern`

## Tenant safety

Internal audit mode **does not bypass tenant boundaries**.

- Tenant A quarantine metadata visible only to Tenant A queries
- Tenant B cannot see Tenant A private Skills or quarantine records

## Generic not-found

Invisible artifact lookup returns generic not-found — no cross-tenant leakage signal.
