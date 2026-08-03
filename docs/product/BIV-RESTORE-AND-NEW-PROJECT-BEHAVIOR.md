# BIV Restore and New Project Behavior

**Slice:** PRODUCT-01.3A

---

## Hydration (reload / return visit)

When `GET .../analysis-contexts/current` finds project brief or prior BIV data and no active context:

1. Creates context in `hydrated_unconfirmed`
2. Populates fields from brief + last user request text
3. Sets `data_source_label` (`saved_project` | `previous_session`)
4. **Does not** start analysis
5. **Does not** show verdict until user confirms

Frontend shows `HydrationRecoveryCard`.

---

## Continue with saved data

1. User clicks «Продолжить с этими данными»
2. `POST .../confirm` — specificity gate runs
3. If prior BIV run matches `input_snapshot_hash` → show completed report (no re-run)
4. Else → intake form in `confirmed` state; user starts analysis explicitly

---

## Edit description

1. User clicks «Изменить описание»
2. Intake form opens with hydrated values
3. `confirmed_by_user=false`, state `editing`
4. Prior hydrated snapshot preserved via `source_snapshot_id`
5. Analysis blocked until re-confirm

---

## Start new project

1. User clicks «Начать новый проект»
2. `POST .../start-new` deactivates active context on current project
3. Creates **new** `ProjectTable` row (non-destructive)
4. Creates empty context on new project
5. Historical projects, BIV runs, reports **unchanged**

---

## Forbidden

- Auto-run on mount
- Silent hydration to verdict phase
- Deleting historical reports or projects
- Showing internal IDs/hashes in UI
