# Controlled pilot operator checklist

## Daily

- [ ] `/health/live` → 200
- [ ] `/health/ready` → ready; revision matches code head
- [ ] Backup age within policy (or warn)
- [ ] Skim structlog for `login_failure`, `csrf_failed`, unexpected errors

## Before inviting a user

- [ ] Provision unique account on `botfazer_cph1`
- [ ] Confirm HTTPS + Secure cookie if remote
- [ ] Confirm origins match frontend URL
- [ ] Send disclaimer + credentials out-of-band
- [ ] Verify user can login on canonical host

## Weekly

- [ ] Full backup + checksum verify
- [ ] Optional restore drill on disposable DB
- [ ] Review isolation / support issues

## On incident

- [ ] Apply stop conditions
- [ ] Capture correlation IDs
- [ ] Revoke sessions
- [ ] Follow rollback / restore runbooks (CPH.4 / CPH.5)

## Commands (sanitized)

```powershell
uv run python scripts/cph1_db_tools.py check-revision
uv run python -m scripts.cph5_validate_config
uv run python -m scripts.cph4_backup_pilot_db --require-db botfazer_cph1
uv run python -m scripts.cph5_post_deploy_smoke --base-url https://<api>
```
