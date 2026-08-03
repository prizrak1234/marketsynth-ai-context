# CPH.5 — Post-deploy smoke

```powershell
$env:CPH3_E2E_EMAIL = "<pilot-a>"
$env:CPH3_E2E_PASSWORD = "<secret>"
uv run python -m scripts.cph5_post_deploy_smoke --base-url http://127.0.0.1:8000
```

Checks:

1. `/health/live`
2. `/health/ready`
3. Login
4. List/open project
5. MarketingPlan remains draft
6. Create labelled smoke Project
7. Logout invalidates session
8. Capture correlation IDs

No MarketingPlan approval / Agent Run / Campaign / execution / publication / provider / budget.
