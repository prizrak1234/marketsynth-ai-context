# Settings v2

Sections on `/workspace/settings`:

1. **Profile** — email, display name, role (read-only)
2. **Language and region** — interface language (`ru`/`en` active; `tr`/`de`/`es`/`fr`/`ar` listed as soon), timezone via full IANA list (`Intl.supportedValuesOf("timeZone")` + fallback), date/time format (local persistence)
3. **Security** — change password (reset flow link), active sessions hint, logout
4. **Notifications** — email / project / verdict / security toggles; delivery marked “coming soon” when backend absent
5. **Workspace preferences** — default landing, density; integration mode only for owner/admin in non-prod
6. **Account** — signup/invite honesty; deletion placeholder only

Persistence:

- Locale: `marketsynth.ui.locale.v1`
- Prefs: `marketsynth.ui.prefs.v1`

Do not expose API keys or provider credentials.
