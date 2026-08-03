"""Organize knowledge_import staging into BotFazer knowledge layout (AI.255.1)."""

from __future__ import annotations

import re
import shutil
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STAGING = REPO / "knowledge_import"

TOPIC_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("knowledge/wordstat", re.compile(r"wordstat|seo|keyword|ключев", re.I)),
    ("knowledge/metrica", re.compile(r"metrica|analytics|метрик|traffic|трафик", re.I)),
    ("knowledge/audience", re.compile(r"audience|segment|сегмент|аудитор", re.I)),
    ("knowledge/offers", re.compile(r"offer|оффер|commercial|proposal|предложен", re.I)),
    ("knowledge/positioning", re.compile(r"position|позиц|meaning|смысл|brand|бренд", re.I)),
    ("knowledge/content", re.compile(r"content|контент|copy|instagram|tiktok|youtube|social|telegram|linkedin|reels|video", re.I)),
    ("knowledge/analytics", re.compile(r"report|отчет|dashboard|dataforseo|scrape", re.I)),
    ("knowledge/business", re.compile(r"business|бизнес|lead|лид|crm|sales|клиент", re.I)),
    ("knowledge/marketing", re.compile(r"market|маркет|campaign|кампан|funnel|ворон", re.I)),
]

SKILL_DEFS: list[tuple[str, re.Pattern[str]]] = [
    ("segment-research", re.compile(r"segment|сегмент|audience|аудитор", re.I)),
    ("wordstat-research", re.compile(r"wordstat|keyword|ключев|seo", re.I)),
    ("metrica-analysis", re.compile(r"metrica|analytics|метрик|traffic", re.I)),
    ("offer-packaging", re.compile(r"offer|оффер|commercial|proposal|предложен", re.I)),
    ("content-production", re.compile(r"content|контент|copy|instagram|tiktok|youtube|social", re.I)),
    ("visual-report", re.compile(r"visual|image|video|media|nano|banana|render", re.I)),
    ("lead-generation", re.compile(r"lead|лид|crm|sales", re.I)),
    ("supervisor-quality", re.compile(r"supervisor|quality|контрол|checklist|чек", re.I)),
]

STANDARD_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("standards/skills", re.compile(r"skill|навык|claudeclaw|агент", re.I)),
    ("standards/workflows", re.compile(r"workflow|процесс|make|n8n", re.I)),
    ("standards/tools", re.compile(r"tool|metrica|wordstat|api", re.I)),
    ("standards/memory", re.compile(r"memory|obsidian|sync", re.I)),
    ("standards/commands", re.compile(r"command|slash", re.I)),
    ("standards/supervisor", re.compile(r"supervisor|quality|контрол", re.I)),
]


def ensure_dirs() -> None:
    dirs = [
        "knowledge/marketing",
        "knowledge/business",
        "knowledge/wordstat",
        "knowledge/metrica",
        "knowledge/audience",
        "knowledge/offers",
        "knowledge/positioning",
        "knowledge/content",
        "knowledge/analytics",
        "knowledge/misc",
        "knowledge/prompts",
        "knowledge/manuals",
        "workflows/raw",
        "workflows/mapped",
        "standards/memory",
        "standards/skills",
        "standards/tools",
        "standards/commands",
        "standards/supervisor",
        "standards/workflows",
        "standards/misc",
    ]
    for rel in dirs:
        (REPO / rel).mkdir(parents=True, exist_ok=True)


def copy_tree_unique(src_root: Path, dest_root: Path, *, patterns: tuple[str, ...] = ("*",)) -> int:
    copied = 0
    if not src_root.exists():
        return 0
    for pattern in patterns:
        for src in src_root.rglob(pattern):
            if not src.is_file():
                continue
            rel = src.relative_to(src_root)
            dest = dest_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                continue
            shutil.copy2(src, dest)
            copied += 1
    return copied


def classify_standard(path: Path) -> str:
    text = path.name
    for dest, pattern in STANDARD_RULES:
        if pattern.search(text):
            return dest
    return "standards/misc"


def classify_topic(path: Path) -> str:
    text = f"{path.name} {path.parent.name}"
    for dest, pattern in TOPIC_RULES:
        if pattern.search(text):
            return dest
    return "knowledge/misc"


def write_skill(skill_id: str, references: list[Path]) -> None:
    skill_dir = REPO / "skills" / skill_id
    for sub in ("references", "examples", "templates"):
        (skill_dir / sub).mkdir(parents=True, exist_ok=True)
    ref_lines = "\n".join(f"- `{p.name}`" for p in references[:12]) or "- _(none matched during import)_"
    content = f"""# {skill_id}

Imported skill knowledge bundle (AI.255.1). Read-only reference — not executable in BotFazer runtime.

## Purpose

Collects legacy prompts, standards, and workflow references related to **{skill_id}**.

## References

{ref_lines}

## Out of scope (v1 import)

- Auto-execution
- n8n/Make direct import
- Product code changes

## BotFazer mapping (future)

Map to `MarketingSkillType` / `CampaignWorkflowTemplate` during Skill Registry and Workflow Layer expansion.
"""
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def main() -> None:
    ensure_dirs()

    wf_sources = [
        STAGING / "knowledge_base" / "workflows",
        STAGING / "extracted_workflows_sync",
        STAGING / "extracted_knowledge_base_sync",
    ]
    wf_sources.extend(sorted(STAGING.glob("extra_*_workflows")))
    raw = REPO / "workflows" / "raw"
    wf_copied = 0
    for src in wf_sources:
        wf_copied += copy_tree_unique(src, raw, patterns=("*.json", "*.csv", "*.xlsx"))

    copy_tree_unique(STAGING / "knowledge_base" / "prompts", REPO / "knowledge" / "prompts")
    copy_tree_unique(STAGING / "extracted_prompts_sync", REPO / "knowledge" / "prompts")
    copy_tree_unique(STAGING / "knowledge_base" / "manuals", REPO / "knowledge" / "manuals")
    copy_tree_unique(STAGING / "extra_0_manuals", REPO / "knowledge" / "manuals")
    for prompts_src in sorted(STAGING.glob("extra_*_prompts")):
        copy_tree_unique(prompts_src, REPO / "knowledge" / "prompts")

    std_src = STAGING / "knowledge_base" / "standards"
    std_sources = [std_src, STAGING / "extra_2_standards"]
    std_sources.extend(p for p in STAGING.glob("extra_*_standards") if p != STAGING / "extra_2_standards")
    for src_root in std_sources:
        if not src_root.exists():
            continue
        for src in src_root.rglob("*"):
            if not src.is_file():
                continue
            dest_dir = REPO / classify_standard(src)
            dest = dest_dir / src.name
            if not dest.exists():
                shutil.copy2(src, dest)

    # Stage "Боты в базу знаний" subtree (knowledge-only files)
    bots_roots = []
    proj = STAGING.parent
    desktop_proj = next(Path(r"C:/Users/User/Desktop").rglob("knowledge_base_deploy.zip")).parent.parent
    for p in desktop_proj.iterdir():
        if p.is_dir() and not p.name.startswith("."):
            bots_roots.append(p)
    bots_staging = STAGING / "bots_v_bazu_znaniy"
    bots_staging.mkdir(parents=True, exist_ok=True)
    for root in bots_roots:
        for src in root.rglob("*"):
            if not src.is_file():
                continue
            if src.suffix.lower() not in {".md", ".json", ".csv", ".xlsx", ".pdf", ".txt", ".docx"}:
                continue
            parts = {part.lower() for part in src.parts}
            if parts & {"app", "tests", "alembic", "web", ".venv", "node_modules", ".next"}:
                continue
            rel = src.relative_to(root)
            dest = bots_staging / root.name / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(src, dest)

    bots_docs = STAGING / "bots_v_bazu_znaniy"
    if bots_docs.exists():
        for src in bots_docs.rglob("*"):
            if not src.is_file():
                continue
            if src.suffix.lower() == ".md":
                dest = REPO / "knowledge" / "business" / src.name
                if not dest.exists():
                    shutil.copy2(src, dest)
            elif src.suffix.lower() in {".json", ".csv", ".xlsx"}:
                dest = raw / "bots_import" / src.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(src, dest)

    report = STAGING / "BOTFAZER_KNOWLEDGE_BASE_ANALYSIS_REPORT.md"
    if report.exists():
        dest = REPO / "knowledge" / "misc" / report.name
        if not dest.exists():
            shutil.copy2(report, dest)

    for wf in raw.rglob("*.json"):
        dest_dir = REPO / classify_topic(wf)
        dest = dest_dir / wf.name
        if not dest.exists():
            shutil.copy2(wf, dest)

    search_roots = [REPO / "knowledge", REPO / "standards", raw]
    for skill_id, pattern in SKILL_DEFS:
        refs: list[Path] = []
        skill_dir = REPO / "skills" / skill_id
        for root in search_roots:
            for src in root.rglob("*"):
                if not src.is_file() or src.name == "SKILL.md":
                    continue
                if not pattern.search(f"{src.name} {src.parent.name}"):
                    continue
                dest = skill_dir / "references" / src.name
                if dest.exists():
                    refs.append(dest)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                refs.append(dest)
                if len(refs) >= 8:
                    break
            if len(refs) >= 8:
                break
        write_skill(skill_id, refs)

    mapped_readme = REPO / "workflows" / "mapped" / "README.md"
    mapped_readme.write_text(
        "# Mapped workflows (future)\n\n"
        "BotFazer-native mappings from `workflows/raw/` to `CampaignWorkflowTemplate` "
        "will live here.\n\n"
        "v1 import keeps all originals in `workflows/raw/` unchanged.\n",
        encoding="utf-8",
    )

    print(f"Workflow files copied to raw: {wf_copied}")
    for name in ("knowledge", "skills", "workflows", "standards", "knowledge_import"):
        root = REPO / name
        if root.exists():
            count = sum(1 for _ in root.rglob("*") if _.is_file())
            print(f"{name}: {count} files")


if __name__ == "__main__":
    main()
