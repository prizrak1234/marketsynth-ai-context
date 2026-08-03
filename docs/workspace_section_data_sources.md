# Workspace section data sources

| Section | Adapter | Backend lists used | Mock policy |
|---------|---------|--------------------|-------------|
| Tasks | `workspace-task-index-adapter.ts` | local_draft (+ future) | no fake tasks |
| Projects | existing `load-workspace` + dashboard | `GET /projects` | mock only if mode=mock (owner/dev) |
| Investigations | `investigation-index-adapter.ts` | `/projects` + `/investigations` | no fixtures |
| Verdicts | `verdict-index-adapter.ts` | `/business-verdicts` | no fixtures |
| Strategies | `strategy-index-adapter.ts` | `/marketing-strategies` | no fixtures |
| Implementation | `implementation-index-adapter.ts` | `/implementation-plans` (+ optional marketing-plans) | no fixtures |
| Assets | `assets-index-adapter.ts` | `/content-assets` if available | honest empty |
| Knowledge | `knowledge-index-adapter.ts` | none (no SoT) | honest empty |
| Settings | local auth session | `/auth/me` via context | — |

## N+1

Index pages: one `/projects` then per-project list call. Documented in adapters. No new aggregate table.

Default integration mode: **backend** (`mode.ts`). Mode switcher hidden for non-owner/non-admin; sticky mock cleared for members on projects dashboard load.
