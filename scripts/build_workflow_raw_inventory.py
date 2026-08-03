"""Build read-only inventory index for workflows/raw (Phase AI.257)."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "workflows" / "raw"
MAPPED = REPO / "workflows" / "mapped"
DOC = REPO / "docs" / "WORKFLOW_RAW_INVENTORY.md"

CATEGORIES: list[tuple[str, re.Pattern[str]]] = [
    ("lead_generation", re.compile(r"lead|лид|crm|client|клиент|proposal|предложен", re.I)),
    ("content_social", re.compile(r"content|контент|instagram|tiktok|youtube|linkedin|reels|social|telegram", re.I)),
    ("seo_wordstat", re.compile(r"wordstat|seo|keyword|ключев|search|поиск", re.I)),
    ("analytics_metrica", re.compile(r"metrica|analytics|метрик|traffic|трафик|dashboard", re.I)),
    ("offer_sales", re.compile(r"offer|оффер|sales|продаж|commercial|коммерч", re.I)),
    ("publishing", re.compile(r"publish|публикац|schedule|распис", re.I)),
    ("scraping_data", re.compile(r"scrape|scrap|parse|парс|crawl", re.I)),
    ("misc", re.compile(r".*", re.I)),
]


def categorize(name: str) -> str:
    for category, pattern in CATEGORIES:
        if category == "misc":
            continue
        if pattern.search(name):
            return category
    return "misc"


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"Missing raw workflows directory: {RAW}")

    files = sorted(p for p in RAW.rglob("*") if p.is_file())
    by_category: dict[str, list[str]] = defaultdict(list)
    ext_counts: Counter[str] = Counter()

    for path in files:
        rel = path.relative_to(RAW).as_posix()
        ext_counts[path.suffix.lower() or "(no ext)"] += 1
        by_category[categorize(path.name)].append(rel)

    index = {
        "generated_at": date.today().isoformat(),
        "raw_root": "workflows/raw",
        "total_files": len(files),
        "extensions": dict(ext_counts),
        "categories": {
            key: {
                "count": len(values),
                "sample_files": values[:15],
            }
            for key, values in sorted(by_category.items(), key=lambda item: (-len(item[1]), item[0]))
        },
        "notes": [
            "Archive only — no n8n execution from this index.",
            "Curated product templates live in app/marketing/workflows/registry.py and workflows/mapped/.",
        ],
    }

    MAPPED.mkdir(parents=True, exist_ok=True)
    (MAPPED / "raw_inventory_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Workflow Raw Inventory Index",
        "",
        f"**Phase:** AI.257  ",
        f"**Generated:** {date.today().isoformat()}  ",
        f"**Source:** `workflows/raw/` (archive only — **no execution**)",
        "",
        "---",
        "",
        "## Statistics",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Total files | {len(files)} |",
    ]
    for ext, count in ext_counts.most_common():
        lines.append(f"| `{ext}` | {count} |")

    lines.extend(
        [
            "",
            "## Categories",
            "",
            "Keyword-based classification for curation into `CampaignWorkflowTemplate`.",
            "",
        ]
    )

    for category, values in sorted(by_category.items(), key=lambda item: (-len(item[1]), item[0])):
        lines.append(f"### `{category}` — {len(values)} files")
        lines.append("")
        for sample in values[:10]:
            lines.append(f"- `{sample}`")
        if len(values) > 10:
            lines.append(f"- … and {len(values) - 10} more")
        lines.append("")

    lines.extend(
        [
            "## Usage rules",
            "",
            "1. **Do not** import JSON into app runtime automatically.",
            "2. Pick representative flows per category → map in `workflows/mapped/curated_templates.json`.",
            "3. Promote to product only via `app/marketing/workflows/registry.py` + contracts + tests.",
            "",
            "## Machine-readable index",
            "",
            "`workflows/mapped/raw_inventory_index.json`",
            "",
            "## Related",
            "",
            "- [phase_ai_256_campaign_workflow_roadmap.md](phase_ai_256_campaign_workflow_roadmap.md)",
            "- [KNOWLEDGE_IMPORT_PLAN.md](KNOWLEDGE_IMPORT_PLAN.md)",
            "- [phase_ai_265_campaign_workflow_layer_readiness_audit.md](phase_ai_265_campaign_workflow_layer_readiness_audit.md)",
        ]
    )

    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {DOC}")
    print(f"Wrote {MAPPED / 'raw_inventory_index.json'}")
    print(f"Total files indexed: {len(files)}")


if __name__ == "__main__":
    main()
