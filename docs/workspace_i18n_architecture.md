# Workspace i18n architecture

## Structure

```
web/src/lib/i18n/
  config.ts              # locales, defaults, storage keys
  lookup.ts              # nested key + {param} interpolation
  domain-labels.ts       # t() + enum→label helpers
  formatters.ts          # date/time/money/relative
  locale-context.tsx     # LocaleProvider / useLocale
  translations/ru.ts
  translations/en.ts
  index.ts
```

## Usage

```ts
const { t, locale } = useLocale();
t("task.status.routed");
labelTaskType(locale, "telegram_bot");
```

Never branch on raw enums in components for display.

## Locale resolution

1. `localStorage` `marketsynth.ui.locale.v1`
2. browser `navigator.language`
3. default `ru`

**Gap:** backend user-profile locale field not wired yet — local preference is labelled.

## Extending locales

Add `az.ts` / `tr.ts` …, register in `DICTS`, extend `SUPPORTED_LOCALES`.
