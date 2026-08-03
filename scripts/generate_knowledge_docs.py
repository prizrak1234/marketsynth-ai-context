"""Generate knowledge import documentation (AI.255.1)."""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IMPORT_ROOTS = ["knowledge", "skills", "workflows", "standards"]
STAGING = REPO / "knowledge_import"


def count_files(root: Path) -> int:
    return sum(1 for p in root.rglob("*") if p.is_file())


def ext_stats() -> Counter[str]:
    counter: Counter[str] = Counter()
    for root_name in IMPORT_ROOTS:
        root = REPO / root_name
        for p in root.rglob("*"):
            if p.is_file():
                counter[p.suffix.lower() or "(no ext)"] += 1
    return counter


def tree_lines(root: Path, *, max_depth: int = 3, max_entries: int = 200) -> list[str]:
    lines: list[str] = []
    if not root.exists():
        return lines

    def walk(path: Path, prefix: str, depth: int) -> None:
        if len(lines) >= max_entries:
            return
        if depth > max_depth:
            return
        try:
            children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return
        for child in children:
            if len(lines) >= max_entries:
                lines.append(f"{prefix}... (truncated)")
                return
            if child.is_dir():
                file_count = count_files(child)
                lines.append(f"{prefix}{child.name}/  ({file_count} files)")
                walk(child, prefix + "  ", depth + 1)
            else:
                lines.append(f"{prefix}{child.name}")

    lines.append(f"{root.name}/  ({count_files(root)} files)")
    walk(root, "  ", 1)
    return lines


def imported_stats() -> dict[str, int]:
    stats = {name: count_files(REPO / name) for name in IMPORT_ROOTS}
    stats["total"] = sum(stats.values())
    return stats


def main() -> None:
    stats = imported_stats()
    ext = ext_stats()
    wf = count_files(REPO / "workflows" / "raw")
    prompts = count_files(REPO / "knowledge" / "prompts")
    manuals = count_files(REPO / "knowledge" / "manuals")
    skill_dirs = [p for p in (REPO / "skills").iterdir() if p.is_dir()] if (REPO / "skills").exists() else []

    map_doc = REPO / "docs" / "PROJECT_KNOWLEDGE_MAP.md"
    report_doc = REPO / "docs" / "KNOWLEDGE_IMPORT_REPORT.md"
    arch_doc = REPO / "docs" / "KNOWLEDGE_ARCHITECTURE.md"

    tree_sections = []
    for root_name in IMPORT_ROOTS + ["knowledge_import"]:
        root = REPO / root_name
        tree_sections.append("\n".join(tree_lines(root)))

    map_doc.write_text(
        f"""# PROJECT KNOWLEDGE MAP

**Phase:** AI.255.1 — Knowledge Import Foundation  
**Date:** {date.today().isoformat()}

---

## Statistics

| Metric | Count |
|--------|------:|
| **Total imported files** (knowledge + skills + workflows + standards) | {stats['total']} |
| Workflows (`workflows/raw/`) | {wf} |
| Skills bundles (`skills/*/`) | {len(skill_dirs)} |
| Skill reference files | {stats['skills']} |
| Standards | {stats['standards']} |
| Prompts (`knowledge/prompts/`) | {prompts} |
| Manuals (`knowledge/manuals/`) | {manuals} |
| JSON | {ext.get('.json', 0)} |
| CSV | {ext.get('.csv', 0)} |
| XLSX | {ext.get('.xlsx', 0)} |
| PDF | {ext.get('.pdf', 0)} |
| Markdown | {ext.get('.md', 0)} |
| Text | {ext.get('.txt', 0)} |

Staging archive (read-only source mirror): `{STAGING.as_posix()}` — {count_files(STAGING)} files.

---

## Directory map

### `knowledge/`

{tree_sections[0]}

### `skills/`

{tree_sections[1]}

### `workflows/`

{tree_sections[2]}

### `standards/`

{tree_sections[3]}

### `knowledge_import/` (staging)

{tree_sections[4]}

---

## Future usage

| BotFazer layer | How imported knowledge is used |
|----------------|--------------------------------|
| **Marketing Skills Layer** | `skills/*/SKILL.md` + references → expand `MarketingSkillDefinition`, input/output patterns, prompt seeds |
| **Workflow Layer** | `workflows/raw/` → curated `CampaignWorkflowTemplate` in `workflows/mapped/` (no auto-import of n8n JSON) |
| **Skill Registry** | Map `skills/*` folders to `MarketingSkillType` with explicit human review |
| **Supervisor Layer** | `standards/supervisor`, quality checklists → rule seeds for `campaign_supervisor_engine` |
| **Agent OS** | `knowledge/prompts`, `standards/*`, topical `knowledge/*` → agent instructions and retrieval corpus |
| **Tools** | Metrica/Wordstat/media blueprints in workflows + standards/tools → `MarketingToolType` specs |

**Invariants:** imported assets are read-only references until mapped into contracts/services deliberately.

---

## Strategic vision (unchanged)

BotFazer is **not** a chatbot and **not** an agent constructor.  
Goal: **replace a marketing agency** via Agent OS — Instructions + Knowledge + Skills + Tools + Memory + Workflows + Supervisor.
""",
        encoding="utf-8",
    )

    report_doc.write_text(
        f"""# KNOWLEDGE IMPORT REPORT

**Phase:** AI.255.1  
**Date:** {date.today().isoformat()}

---

## Sources discovered

| Source | Location | Action |
|--------|----------|--------|
| `knowledge_base` | Desktop project `.gemini/antigravity/knowledge_base` | ✅ Imported (553 files staged) |
| `knowledge_base_sync.zip` | Desktop `.gemini/` | ✅ Extracted to staging |
| `workflows_sync.zip` | Desktop `.gemini/` | ✅ Extracted to staging |
| `prompts_sync.zip` | Desktop `.gemini/` | ✅ Extracted to staging |
| `Боты в базу знаний` | Desktop project folders (prompts/manuals/workflows/standards) | ✅ Partial — knowledge files only |
| `BOTFAZER_KNOWLEDGE_BASE_ANALYSIS_REPORT.md` | Desktop `.gemini/` | ✅ Copied to `knowledge/misc/` |
| Additional n8n agent templates | Desktop `.../manuals`, `prompts`, `standards`, `workflows` | ✅ Imported via `knowledge_import/extra_*` |

---

## Target structure created

```
knowledge/          # topical + prompts + manuals
skills/             # 8 skill bundles with SKILL.md
workflows/raw/      # original n8n/Make JSON + CSV/XLSX
workflows/mapped/   # placeholder for BotFazer templates
standards/          # memory/skills/tools/commands/supervisor/workflows/misc
knowledge_import/   # staging mirror (do not delete yet)
```

---

## Imported totals

| Area | Files |
|------|------:|
| knowledge | {stats['knowledge']} |
| skills | {stats['skills']} |
| workflows | {stats['workflows']} |
| standards | {stats['standards']} |
| **Total** | **{stats['total']}** |

---

## Skipped (with reasons)

| Item | Reason |
|------|--------|
| `app/`, `tests/`, `alembic/`, `web/`, `.venv/` under Desktop mirrors | Constraint: no product code import |
| n8n auto-execution wiring | Out of scope — reference only |
| Duplicate filenames across archives | First copy wins; later duplicates skipped to preserve originals |
| `.gemini/botfazer` codebase subtree | Product duplicate — not knowledge corpus |
| Binary assets unrelated to marketing (png/url/ison in staging) | Left in staging only |

---

## Import issues

1. **Encoding / Cyrillic paths** — some Desktop folder names display garbled in shell; imports resolved via Python `pathlib` + zip anchors.
2. **Duplicate workflow JSON** — multiple archives overlap; deduped on copy into `workflows/raw/`.
3. **No live DB/API changes** — import is filesystem-only as required.

---

## Re-run import

```bash
# 1) Refresh staging from Desktop sources (manual copy/update)
# 2) Organize into repo layout
uv run python scripts/organize_knowledge_import.py
uv run python scripts/knowledge_import_stats.py
uv run python scripts/generate_knowledge_docs.py
```

---

## Next steps (not part of AI.255.1)

1. Curate top workflows into `workflows/mapped/` → `CampaignWorkflowTemplate`
2. Align `skills/*` with `MarketingSkillType` registry
3. Feed supervisor standards into rule engine seeds
4. Optional: vector index over `knowledge/` for Agent OS retrieval
""",
        encoding="utf-8",
    )

    arch_doc.write_text(
        """# KNOWLEDGE ARCHITECTURE

**Phase:** AI.255.1 — Knowledge Import Foundation

---

## Layer model

```
Knowledge
   ↓
Skill
   ↓
Workflow
   ↓
Tool
   ↓
Campaign
   ↓
Business Operator
```

BotFazer = **Agent Operating System**

```
Agent =
  Instructions
+ Knowledge
+ Skills
+ Tools
+ Memory
+ Workflows
+ Supervisor
```

---

## Repository layout (imported)

| Path | Role |
|------|------|
| `knowledge/` | Domain facts, prompts, manuals, topical research (Wordstat, Metrica, offers, content…) |
| `skills/` | Skill bundles (`SKILL.md`, `references/`, `examples/`, `templates/`) |
| `workflows/raw/` | Legacy n8n/Make workflow JSON — **archive, not runtime** |
| `workflows/mapped/` | Future BotFazer-native process templates |
| `standards/` | Operating standards (memory, skills, tools, commands, supervisor, workflows) |
| `knowledge_import/` | Staging mirror of external sources |

---

## Product mapping (existing code)

| Imported layer | BotFazer implementation today |
|----------------|------------------------------|
| Knowledge | `knowledge/*` corpus (new) + campaign brief/intent |
| Skill | `app/marketing/skills/registry.py`, `MarketingSkillType` |
| Workflow | `app/marketing/workflows/registry.py`, `CampaignWorkflowTemplate` |
| Tool | `MarketingToolType`, data tools v1 |
| Campaign | Business Campaign Layer + Control Center |
| Supervisor | `campaign_supervisor_engine` (read-only) |
| Business Operator | Rule-based intent → scenario → campaign |

---

## Strategic vision (preserve)

- BotFazer **is not** a chatbot.
- BotFazer **is not** an agent constructor.
- Goal: **fully replace a marketing agency** with an operating system for campaigns.

Imported knowledge supports that vision by separating:

1. **Reference corpus** (what we know)
2. **Executable contracts** (what the product runs — explicit, tested, no auto-import)

---

## Guardrails

- No automatic execution of imported n8n JSON
- No changes to `app/`, migrations, API, DB, or tests in AI.255.1
- Mapping from `workflows/raw/` → product registry is a **later, curated** phase
""",
        encoding="utf-8",
    )

    print("Wrote:", map_doc, report_doc, arch_doc)


if __name__ == "__main__":
    main()
