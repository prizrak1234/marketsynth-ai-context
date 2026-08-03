# Workspace locale policy

## Priority

1. User preference in `localStorage` (`marketsynth.ui.locale.v1`)
2. Browser `navigator.language` (when no stored preference)
3. Default: **`ru`**

Do **not** infer locale from email or IP.

## Persistence gap

Backend user-profile locale field is not wired yet. Preference is local-only until a suitable profile/config API exists. Documented honestly in Settings UI.

## Supported now

- `ru`
- `en`

## Planned additions

`az`, `tr`, `de`, `fr`, `es`, `ar` — add dictionary files under `web/src/lib/i18n/translations/` and register in `DICTS`.

## Rules

- One i18n layer only (`web/src/lib/i18n/`)
- Domain values map via helpers (`labelTaskStatus`, `labelVerdictType`, …) — never hardcode enum→string in components
- Switching locale must update nav, headings, statuses, empty states, and errors without a mixed-language state
