# CPH.3 — Frontend auth

- Module: `web/src/lib/auth/`
- Login UI: `/login`
- Workspace layout wraps `WorkspaceAuthShell` (UX redirect only).
- `apiFetch` uses `credentials: "include"`.
- **No** `marketsynth.e2e.api_key.v1` localStorage.
- Optional `NEXT_PUBLIC_BOTFAZER_API_KEY` for non-browser tools only — leave unset for pilot browser.
