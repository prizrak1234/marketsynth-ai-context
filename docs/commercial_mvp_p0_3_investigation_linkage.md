# Commercial MVP P0.3 — Investigation linkage

`InvestigationSourceLink`:

- investigation_id + source_id (unique)
- purpose, investigation_area, notes
- status: proposed \| accepted \| rejected \| excluded
- added_by, timestamps

Rules:

- Source and Investigation must share Project and owner
- Attach does not clone Source
- Soft detach excludes link; Source remains Project-reusable
- Link does not store Evidence state
