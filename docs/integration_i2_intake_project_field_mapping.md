# Integration I2 — Intake ↔ Project field mapping

Audited against live schemas (`app/schemas`, `POST/PATCH /projects`, frontend intake types).  
**Rule:** only persist where semantics match; never dump the full draft into generic JSON as “persistence.”

| Intake field / section | Backend field | Safe transform | Persist now | Keep local | Conflict risk |
|------------------------|---------------|----------------|-------------|------------|---------------|
| `projectBasics.name` | `Project.name` | trim; fallback “Untitled project” | **Yes** | — | Low |
| `projectBasics.ideaDescription` | `Project.description` (part) | truncate ≤4000 | **Yes** (condensed) | Full text also in draft | Low |
| `product.whatIsSold` / `valueProposition` | `Project.description` (hint lines) | short prefix lines | **Yes** (hint only) | Full product section | Medium if over-interpreted as product DB |
| `projectBasics.businessType` | — | — | No | Yes | — |
| `projectBasics.projectStage` | — (no Project status enum matching intake stage) | — | No | Yes | High if forced into wrong enum |
| `projectBasics.geography` | — | — | No | Yes | — |
| `projectBasics.interfaceLanguage` | — | — | No | Yes | — |
| `product.*` (price, delivery, problem, …) | — | — | No | Yes | High |
| `market.*` | — | — | No | Yes | High |
| `audience.*` | — | — | No | Yes | High |
| `economics.*` | — | — | No | Yes | High (finance) |
| `materials.*` / attachments | — | mock metadata only | No | Yes | Do not upload / encode files |
| `assumptions[]` | — | — | No | Yes | — |
| `missingData[]` | — | — | No | Yes | — |
| `readiness` | — | Product Alpha only | No | Yes | **Do not** map to Project lifecycle |
| `draft.id` | `config.marketsynth_i2.localDraftId` | correlation pointer | **Yes** (pointer only) | Yes | Low |
| submission fingerprint | `config.marketsynth_i2.submissionFingerprint` | hash of name+description+draftId | **Yes** | Yes | Low |
| `draft.updatedAt` | `config.marketsynth_i2.localDraftVersion` | ISO string | **Yes** | Yes | Low |
| Owner | `owner_id` from auth | — | Server-set | — | Never send from UI |
| Full `ProductIntakeDraft` | — | — | **No** | **Yes** | Dumping into `config` forbidden as “persisted brief” |

## Honest UI labels (Review)

- Project core: saved to backend (name + description + sync pointer).
- Full research brief: local draft only.
- Attachments: mock/local only.
- Investigation: not connected.
