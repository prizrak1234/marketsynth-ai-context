# Blocked actions fixtures

**Phase:** KB-WPL-01.8

## Forbidden recommended actions

Discovery must never recommend:

- `install_skill`
- `activate_skill`
- `execute_skill`
- `deploy_workflow`
- `activate_connector`
- `grant_permission`
- `publish`
- `spend`

## Billing sensitivity

Task: «Запустить рекламу» with `execution_sensitivity=billing`

Expected:
- `request_human_review` in safe_next_actions
- Deny-by-default blockers
- `runtime_authorized=false`

## Publication sensitivity

Task: «Опубликовать пост» with `execution_sensitivity=publication`

Expected:
- Approval requirements surfaced
- `runtime_available=false` in readiness_summary
- No execution-ready recommendation

## Validation

`validate_recommended_action()` rejects any forbidden action token at contract boundary.
