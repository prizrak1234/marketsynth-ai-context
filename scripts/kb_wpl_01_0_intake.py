#!/usr/bin/env python3
# ruff: noqa: E501
"""KB-WPL-01.0 — Archive intake freeze (documentation + static inventory only)."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
INTAKE = REPO / ".tmp_archive_intake"
OUT = REPO / "docs" / "research" / "archive-intake"

ARCHIVES = {
    "skills.zip": {
        "archive_id": "arc-skills-zip",
        "extracted": INTAKE / "skills",
        "source_path": r"f:\Мой проект\skills.zip",
        "description": "External Cursor Skill marp-slide — presentation templates and themes",
    },
    "obsidian-vault-linking.zip": {
        "archive_id": "arc-obsidian-vault-linking",
        "extracted": INTAKE / "obsidian-vault-linking",
        "source_path": r"f:\Мой проект\obsidian-vault-linking.zip",
        "description": "External Cursor Skill — Obsidian wiki-link methodology",
    },
    "_Скиллы для передачи.zip": {
        "archive_id": "arc-skills-dlya-peredachi",
        "extracted": INTAKE / "skills-dlya-peredachi",
        "source_path": r"f:\Мой проект\_Скиллы для передачи.zip",
        "description": "External Cursor Skill n8n-knowledge-base — engineering methodology",
    },
    "Боты в базу знаний.rar": {
        "archive_id": "arc-bots-knowledge-rar",
        "extracted": INTAKE / "bots-knowledge",
        "source_path": r"f:\Мой проект\Боты в базу знаний.rar",
        "description": "249 n8n workflow JSON + 58 MD standards — NOT Make blueprints",
    },
}

EXECUTABLE_EXT = {".py", ".sh", ".ps1", ".bat", ".skill"}
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{20,}", "api_key_openai"),
    (r"Bearer\s+[a-zA-Z0-9._\-]{10,}", "bearer_token"),
    (r"api[_-]?key\s*[:=]", "api_key_marker"),
    (r"password\s*[:=]\s*['\"][^'\"]{3,}['\"]", "password_marker"),
    (r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----", "private_key"),
    (r"@\w+\.\w+", "email_address"),
    (r"\+?\d{10,15}", "phone_number"),
]
PUBLICATION_NODES = (
    "telegram", "instagram", "facebook", "linkedin", "wordpress", "gmail", "twitter", "slack"
)
BILLING_MARKERS = ("stripe", "payment", "billing", "invoice", "paypal")
DESTRUCTIVE_SQL = re.compile(r"\b(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE)\b", re.I)
NETWORK_MARKERS = ("http://", "https://", "fetch(", "axios", "requests.", "api.telegram", "graph.facebook")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def scan_secrets(text: str) -> list[str]:
    findings: list[str] = []
    for pattern, label in SECRET_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append(label)
    return sorted(set(findings))


def is_n8n_workflow(data: Any) -> bool:
    return isinstance(data, dict) and isinstance(data.get("nodes"), list)


def analyze_workflow_json(text: str, data: dict[str, Any]) -> dict[str, Any]:
    nodes = data.get("nodes") or []
    node_types = [
        str(n.get("type", "")) for n in nodes if isinstance(n, dict)
    ]
    node_types_lower = [t.lower() for t in node_types]
    providers: list[str] = []
    for t in node_types:
        if "n8n-nodes-base." in t:
            providers.append(t.split(".")[-1])
        elif "langchain" in t.lower():
            providers.append("langchain")
    credential_refs = bool(re.search(r'"credentials"\s*:', text) or "credentials" in text.lower())
    code_nodes = any("code" in t and "n8n-nodes" in t for t in node_types_lower)
    shell_nodes = any("executecommand" in t for t in node_types_lower)
    db_nodes = any(k in t for t in node_types_lower for k in ("postgres", "mysql", "mongodb", "redis"))
    ai_nodes = any("langchain" in t or "openai" in t or "agent" in t for t in node_types_lower)
    pub_nodes = any(any(p in t for p in PUBLICATION_NODES) for t in node_types_lower)
    billing = any(m in text.lower() for m in BILLING_MARKERS)
    destructive = bool(DESTRUCTIVE_SQL.search(text)) or any("delete" in t for t in node_types_lower)
    community = any(
        t.startswith("n8n-nodes-") and "n8n-nodes-base" not in t and "langchain" not in t
        for t in node_types
    )
    active_flag = data.get("active") is True
    return {
        "workflow_content": True,
        "node_count": len(nodes),
        "node_types": sorted(set(node_types)),
        "code_nodes": code_nodes,
        "shell_nodes": shell_nodes,
        "database_nodes": db_nodes,
        "ai_nodes": ai_nodes,
        "publication_nodes": pub_nodes,
        "billing_markers": billing,
        "destructive_markers": destructive,
        "community_nodes": community,
        "credential_markers": credential_refs,
        "active_flag_present": "active" in data,
        "active_flag_true": active_flag,
        "providers": sorted(set(providers))[:20],
    }


def classify_content(
    rel: str,
    suffix: str,
    text_sample: str,
    wf_analysis: dict[str, Any] | None,
) -> tuple[str, str, str, str, list[str]]:
    """Return content_type, source_category, trust_status, decision, blockers."""
    name_lower = rel.lower().replace("\\", "/")
    blockers: list[str] = []

    if wf_analysis:
        blockers = []
        if wf_analysis["credential_markers"]:
            blockers.append("credential_references")
        if wf_analysis["code_nodes"]:
            blockers.append("code_node")
        if wf_analysis["shell_nodes"]:
            blockers.append("shell_node")
        if wf_analysis["publication_nodes"]:
            blockers.append("publication_action")
        if wf_analysis["destructive_markers"]:
            blockers.append("destructive_action")
        if wf_analysis["community_nodes"]:
            blockers.append("community_node")
        return (
            "n8n_workflow_export",
            "workflow_template",
            "quarantined",
            "quarantine",
            blockers,
        )

    if suffix == ".skill" or name_lower.endswith("/skill.md"):
        return (
            "external_cursor_skill",
            "skill_package",
            "quarantined",
            "quarantine",
            ["external_skill_package", "adapt_methodology_required"],
        )

    if suffix == ".py":
        return (
            "executable_script",
            "executable_script",
            "quarantined",
            "quarantine",
            ["algorithm_review_only", "never_execute"],
        )

    if suffix == ".css" or "template-" in name_lower:
        return (
            "presentation_style_asset",
            "presentation_template",
            "untrusted",
            "defer",
            ["visual_adaptation_required"],
        )

    if suffix == ".md":
        if any(k in name_lower for k in ("codex", "gemini", "claude", "employee", "сессия", "session")):
            return (
                "employee_runtime_material",
                "agent_instruction",
                "untrusted",
                "defer",
                ["not_for_product_runtime"],
            )
        if any(k in name_lower for k in ("quality", "audit", "gate", "скилл", "skill")):
            return (
                "quality_gate_methodology",
                "methodology",
                "untrusted",
                "adapt_methodology",
                [],
            )
        if "references/" in name_lower or "methodology" in name_lower:
            return (
                "reference_document",
                "reference_document",
                "untrusted",
                "adapt_methodology",
                [],
            )
        if any(k in name_lower for k in ("стандарт", "step-", "workflow", "n8n")):
            return (
                "engineering_methodology",
                "methodology",
                "untrusted",
                "adapt_methodology",
                [],
            )
        return (
            "reference_document",
            "reference_document",
            "untrusted",
            "adapt_methodology",
            [],
        )

    if suffix in {".docx", ".pdf"}:
        return (
            "binary_document",
            "reference_document",
            "unknown",
            "defer",
            ["binary_review_required"],
        )

    return ("unknown", "unknown", "unknown", "defer", ["unknown_content_type"])


def target_component(source_category: str, decision: str, wf: dict | None) -> str:
    if wf:
        return "workflow_catalog_quarantine"
    mapping = {
        "skill_package": "native_skill_adaptation",
        "executable_script": "algorithm_review_only",
        "presentation_template": "presentation_architecture_skill",
        "methodology": "engineering_knowledge_base",
        "reference_document": "knowledge_core_catalog",
        "agent_instruction": "deferred_runtime_material",
    }
    return mapping.get(source_category, "deferred_review")


def inventory_entry(
    archive_id: str,
    archive_name: str,
    archive_hash: str,
    path: Path,
    root: Path,
) -> dict[str, Any]:
    rel = str(path.relative_to(root)).replace("\\", "/")
    suffix = path.suffix.lower()
    raw = path.read_bytes()
    file_hash = sha256_bytes(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = ""

    wf_analysis: dict[str, Any] | None = None
    if suffix == ".json" and text:
        try:
            data = json.loads(text)
            if is_n8n_workflow(data):
                wf_analysis = analyze_workflow_json(text, data)
        except json.JSONDecodeError:
            pass

    content_type, source_category, trust_status, decision, blockers = classify_content(
        rel, suffix, text[:3000], wf_analysis
    )
    secrets = scan_secrets(text[:100000]) if text else []
    if secrets:
        blockers = sorted(set(blockers + ["secret_pattern_detected"]))

    network = any(m in text.lower() for m in NETWORK_MARKERS) if text else False
    provider_deps: list[str] = []
    if wf_analysis:
        provider_deps = wf_analysis.get("providers", [])
    elif text:
        for prov in ("openai", "telegram", "instagram", "postgres", "groq", "gemini", "anthropic"):
            if prov in text.lower():
                provider_deps.append(prov)

    notes = ""
    if wf_analysis and wf_analysis.get("active_flag_true"):
        notes = "active_flag=true in export — does not activate in Marketsynth"

    return {
        "archive_id": archive_id,
        "archive_name": archive_name,
        "archive_hash": archive_hash,
        "file_path": rel,
        "file_name": path.name,
        "file_extension": suffix.lstrip(".") or "none",
        "file_size": len(raw),
        "file_hash": file_hash,
        "content_type": content_type,
        "source_category": source_category,
        "executable_content": suffix in EXECUTABLE_EXT or source_category == "executable_script",
        "workflow_content": bool(wf_analysis),
        "script_content": suffix == ".py",
        "network_instructions": network,
        "credential_markers": bool(secrets) or (wf_analysis or {}).get("credential_markers", False),
        "provider_dependencies": provider_deps,
        "license_status": "unknown",
        "provenance_status": "external_archive",
        "duplicate_group": None,
        "trust_status": trust_status,
        "decision": decision,
        "target_component": target_component(source_category, decision, wf_analysis),
        "blockers": blockers,
        "notes": notes,
        **({k: v for k, v in wf_analysis.items() if k not in ("providers",)} if wf_analysis else {}),
    }


def build_inventory() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    archives_meta: list[dict[str, Any]] = []
    for archive_name, meta in ARCHIVES.items():
        src = Path(meta["source_path"])
        archive_hash = sha256_file(src) if src.is_file() else "missing_source_file"
        archives_meta.append(
            {
                "archive_id": meta["archive_id"],
                "archive_name": archive_name,
                "archive_hash": archive_hash,
                "description": meta["description"],
                "file_count": 0,
            }
        )
        extracted: Path = meta["extracted"]
        if not extracted.exists():
            continue
        count = 0
        for path in sorted(extracted.rglob("*")):
            if path.is_file():
                entries.append(
                    inventory_entry(meta["archive_id"], archive_name, archive_hash, path, extracted)
                )
                count += 1
        archives_meta[-1]["file_count"] = count

    by_hash: dict[str, list[int]] = defaultdict(list)
    for i, e in enumerate(entries):
        by_hash[e["file_hash"]].append(i)
    for h, idxs in by_hash.items():
        if len(idxs) > 1:
            group = f"dup-{h[:12]}"
            for i in idxs:
                entries[i]["duplicate_group"] = group

    return {
        "program": "KB-WPL-01.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "note": "NOT Make blueprints. Separate from archive-marketer / ИИ маркетолог в n8n.rar",
        "archives": archives_meta,
        "file_count": len(entries),
        "entries": entries,
    }


def workflow_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    wfs = [e for e in entries if e.get("workflow_content")]
    total = len(wfs)
    unique_hashes = len({e["file_hash"] for e in wfs})
    return {
        "workflow_json_count": total,
        "unique_by_content_hash": unique_hashes,
        "exact_duplicates": total - unique_hashes,
        "code_nodes": sum(1 for e in wfs if e.get("code_nodes")),
        "shell_nodes": sum(1 for e in wfs if e.get("shell_nodes")),
        "credential_markers": sum(1 for e in wfs if e.get("credential_markers")),
        "publication_nodes": sum(1 for e in wfs if e.get("publication_nodes")),
        "billing_markers": sum(1 for e in wfs if e.get("billing_markers")),
        "destructive_markers": sum(1 for e in wfs if e.get("destructive_markers")),
        "community_nodes": sum(1 for e in wfs if e.get("community_nodes")),
        "ai_nodes": sum(1 for e in wfs if e.get("ai_nodes")),
        "active_flag_true": sum(1 for e in wfs if e.get("active_flag_true")),
    }


def write_docs(inventory: dict[str, Any]) -> None:
    entries = inventory["entries"]
    decisions = Counter(e["decision"] for e in entries)
    wf_stats = workflow_summary(entries)

    write_json(OUT / "archive-checksums.json", inventory)

    write_text(
        OUT / "README.md",
        "# Archive Intake — KB-WPL-01.0\n\n"
        "Deterministic inventory and trust assessment for four external archives.\n\n"
        "**No execution. No installation. No app modules in this phase.**\n\n"
        f"- Total files: **{inventory['file_count']}**\n"
        f"- Workflow JSON: **{wf_stats['workflow_json_count']}** "
        f"({wf_stats['unique_by_content_hash']} unique by hash)\n"
        f"- Separate from Make archive `ИИ маркетолог в n8n.rar`\n\n"
        "Next phase: KB-WPL-01.1 Shared Knowledge Contracts (after owner review of this inventory).\n",
    )

    write_text(
        OUT / "archive-inventory.md",
        "# Archive Inventory\n\n"
        "## Archives\n\n"
        + "\n".join(
            f"- **{a['archive_name']}** (`{a['archive_id']}`) — "
            f"{a['file_count']} files — `{a['archive_hash'][:16]}…`"
            for a in inventory["archives"]
        )
        + "\n\n## Workflow JSON risk summary (RAR)\n\n"
        + "\n".join(f"- {k}: **{v}**" for k, v in wf_stats.items())
        + "\n",
    )

    write_text(
        OUT / "adopt-adapt-quarantine-reject-matrix.md",
        "# Adopt / Adapt / Quarantine / Defer / Reject\n\n"
        "| Decision | Count |\n|----------|-------|\n"
        + "\n".join(f"| {k} | {v} |" for k, v in sorted(decisions.items()))
        + "\n\n## Default rules applied\n\n"
        "- n8n workflow JSON → **quarantine**\n"
        "- external Cursor Skill → **quarantine** + adapt methodology\n"
        "- imported script → **quarantine** + algorithm review only\n"
        "- CSS/theme asset → **defer**\n"
        "- Codex/Gemini employee runtime → **defer** (not product runtime)\n"
        "- quality-gate methodology → **adapt_methodology**\n",
    )

    write_text(
        OUT / "source-risk-register.md",
        "# Source Risk Register\n\n"
        "## Critical risks\n\n"
        f"1. **{wf_stats['code_nodes']}** workflows contain code nodes\n"
        f"2. **{wf_stats['credential_markers']}** workflows reference credentials\n"
        f"3. **{wf_stats['publication_nodes']}** workflows have publication nodes\n"
        f"4. **{wf_stats['destructive_markers']}** workflows have destructive markers\n"
        f"5. **{wf_stats['community_nodes']}** workflows use community/unknown nodes\n"
        f"6. All archives: **license_status = unknown**\n"
        f"7. **{wf_stats['active_flag_true']}** exports have active=true (informational only)\n\n"
        "## Mitigations\n\n"
        "- Static parse only — no n8n import\n"
        "- Metadata catalog — no workflow bodies in production packages\n"
        "- Pattern extraction requires ≥2 sources or manual audit (KB-WPL-01.3)\n"
        "- Publication/spend/destructive patterns require human approval gates\n",
    )

    write_text(
        OUT / "license-provenance-report.md",
        "# License and Provenance\n\n"
        "| Archive | License | Provenance |\n|---------|---------|------------|\n"
        + "\n".join(
            f"| {a['archive_name']} | unknown | external_archive |"
            for a in inventory["archives"]
        )
        + "\n\nDo not treat as MIT/Apache without explicit license file.\n"
        "Do not mix with `ИИ маркетолог в n8n.rar` (Make methodology — separate program).\n",
    )

    dup_groups = sum(1 for e in entries if e.get("duplicate_group"))
    write_text(
        OUT / "duplicate-content-report.md",
        "# Duplicate Content Report\n\n"
        f"- File-level entries in duplicate groups: **{dup_groups}**\n"
        f"- Workflow JSON total: **{wf_stats['workflow_json_count']}**\n"
        f"- Workflow unique by content hash: **{wf_stats['unique_by_content_hash']}**\n"
        f"- Workflow exact duplicates: **{wf_stats['exact_duplicates']}**\n",
    )

    # Deep RAR intake doc
    bots_entries = [e for e in entries if e["archive_id"] == "arc-bots-knowledge-rar"]
    md_count = sum(1 for e in bots_entries if e["file_extension"] == "md")
    json_wf = [e for e in bots_entries if e.get("workflow_content")]
    write_text(
        OUT / "ARCHIVE-BOTS-KNOWLEDGE-INTAKE.md",
        "# Archive Intake — Боты в базу знаний.rar\n\n"
        "**Archive ID:** `arc-bots-knowledge-rar`\n\n"
        "## Confirmed contents\n\n"
        f"- n8n workflow JSON exports: **{len(json_wf)}**\n"
        f"- Markdown standards/methodology: **{md_count}**\n"
        "- Binary docs: docx/pdf (deferred review)\n\n"
        "**These are n8n exports (`nodes`, `connections`, `meta`) — NOT Make blueprints.**\n\n"
        "## Workflow JSON static audit (pre-pattern-library)\n\n"
        "| Risk marker | Count |\n|-------------|-------|\n"
        + "\n".join(
            f"| {k} | {v} |"
            for k, v in {
                "total_json": len(json_wf),
                "unique_hash": len({e['file_hash'] for e in json_wf}),
                "code_nodes": wf_stats["code_nodes"],
                "shell_nodes": wf_stats["shell_nodes"],
                "credential_markers": wf_stats["credential_markers"],
                "publication_nodes": wf_stats["publication_nodes"],
                "billing_markers": wf_stats["billing_markers"],
                "destructive_markers": wf_stats["destructive_markers"],
                "community_nodes": wf_stats["community_nodes"],
                "ai_nodes": wf_stats["ai_nodes"],
            }.items()
        )
        + "\n\n## Decision\n\n"
        "All workflow JSON → **quarantine** → `workflow_catalog_quarantine`\n\n"
        "Pattern Library (KB-WPL-01.3) **blocked** until this inventory is accepted.\n\n"
        "## MD material categories\n\n"
        "- AI employee methodology → defer (not product runtime)\n"
        "- Cursor Skill audit / quality gates → adapt_methodology\n"
        "- n8n workflow architecture standards → adapt_methodology\n"
        "- Codex/Gemini CLI setup → defer\n"
        "- Session/timer commands → defer\n",
    )


def main() -> None:
    print("KB-WPL-01.0 intake freeze starting...")
    inventory = build_inventory()
    write_docs(inventory)
    wf = workflow_summary(inventory["entries"])
    print(f"Files: {inventory['file_count']}")
    print(f"Workflow JSON: {wf['workflow_json_count']} ({wf['unique_by_content_hash']} unique)")
    print(f"Code nodes: {wf['code_nodes']}, credentials: {wf['credential_markers']}")
    print(f"Publication: {wf['publication_nodes']}, destructive: {wf['destructive_markers']}")


if __name__ == "__main__":
    main()
