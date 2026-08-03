#!/usr/bin/env python3
# ruff: noqa: E501
"""KB-SKILL-01 — inventory, schemas, workflow catalog metadata, skill scaffolds."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
INTAKE = REPO / ".tmp_archive_intake"
DOCS = REPO / "docs" / "research" / "external-archives"
QUARANTINE = REPO / "quarantine" / "kb-skill-01"
SCHEMA_ROOT = REPO / "packages" / "knowledge" / "external_artifacts" / "0.1.0"
CATALOG_PKG = REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0"

ARCHIVES = {
    "skills.zip": {
        "archive_id": "arc-skills-zip",
        "extracted": INTAKE / "skills",
        "source_path": r"f:\Мой проект\skills.zip",
    },
    "obsidian-vault-linking.zip": {
        "archive_id": "arc-obsidian-vault-linking",
        "extracted": INTAKE / "obsidian-vault-linking",
        "source_path": r"f:\Мой проект\obsidian-vault-linking.zip",
    },
    "_Скиллы для передачи.zip": {
        "archive_id": "arc-skills-dlya-peredachi",
        "extracted": INTAKE / "skills-dlya-peredachi",
        "source_path": r"f:\Мой проект\_Скиллы для передачи.zip",
    },
    "Боты в базу знаний.rar": {
        "archive_id": "arc-bots-knowledge-rar",
        "extracted": INTAKE / "bots-knowledge",
        "source_path": r"f:\Мой проект\Боты в базу знаний.rar",
    },
}

EXECUTABLE_EXT = {".py", ".sh", ".ps1", ".bat", ".skill"}
WORKFLOW_EXT = {".json"}
DOC_EXT = {".md", ".txt", ".docx", ".pdf"}

SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{20,}", "api_key_openai"),
    (r"Bearer\s+[a-zA-Z0-9._\-]+", "bearer_token"),
    (r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]", "api_key_marker"),
    (r"password\s*[:=]\s*['\"][^'\"]+['\"]", "password_marker"),
    (r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----", "private_key"),
]

PROV = {"source_type": "kb_skill_01", "source_id": "build-script"}


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


def classify_file(rel: str, suffix: str, content_sample: str) -> tuple[str, str, str]:
    name_lower = rel.lower()
    if suffix == ".skill" or name_lower.endswith("skill.md"):
        return "skill_package", "engineering", "QUARANTINE"
    if suffix == ".py":
        return "executable_script", "engineering", "QUARANTINE"
    if "workflow" in name_lower or (suffix == ".json" and '"nodes"' in content_sample[:500]):
        return "workflow_template", "automation", "QUARANTINE"
    if suffix in {".css"} or "template-" in name_lower:
        return "presentation_template", "presentation", "ADAPT"
    if suffix == ".md" and "references/" in name_lower.replace("\\", "/"):
        return "reference_document", "engineering", "ADAPT"
    if suffix == ".md":
        if any(x in name_lower for x in ("methodology", "step-", "стандарт", "скилл")):
            return "methodology", "engineering", "ADAPT"
        return "reference_document", "general", "ADAPT"
    if suffix in {".docx", ".pdf"}:
        return "reference_document", "general", "DEFER"
    return "unknown", "unknown", "DEFER"


def scan_secrets(text: str) -> list[str]:
    findings: list[str] = []
    for pattern, label in SECRET_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append(label)
    return findings


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
    content_hash = sha256_bytes(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
    category, domain, decision = classify_file(rel, suffix, text[:2000])
    secrets = scan_secrets(text[:50000]) if text else []
    return {
        "archive_id": archive_id,
        "archive_name": archive_name,
        "archive_hash": archive_hash,
        "file_path": rel,
        "file_name": path.name,
        "file_type": suffix.lstrip(".") or "unknown",
        "file_size": len(raw),
        "content_hash": content_hash,
        "source_category": category,
        "inferred_domain": domain,
        "executable_content": suffix in EXECUTABLE_EXT or category == "executable_script",
        "network_capable_content": any(
            k in text.lower()
            for k in ("http://", "https://", "api.telegram", "graph.facebook", "fetch(")
        )
        if text
        else False,
        "credential_markers": bool(secrets) or "credential" in text.lower() if text else False,
        "external_dependencies": [],
        "license_status": "unknown",
        "provenance_status": "external_archive",
        "duplicate_group": None,
        "proposed_decision": decision,
        "proposed_target": {
            "ADAPT": "native_skill_or_knowledge_base",
            "QUARANTINE": "quarantine_catalog",
            "REJECT": "rejected",
            "DEFER": "deferred_review",
        }.get(decision, "deferred_review"),
        "blocking_unknowns": ["license_unknown"] if decision != "REJECT" else [],
    }


def build_inventory() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    archive_meta: list[dict[str, Any]] = []
    for archive_name, meta in ARCHIVES.items():
        src = Path(meta["source_path"])
        archive_hash = sha256_file(src) if src.is_file() else "missing"
        archive_meta.append(
            {
                "archive_id": meta["archive_id"],
                "archive_name": archive_name,
                "archive_hash": archive_hash,
                "source_path": meta["source_path"],
            }
        )
        extracted: Path = meta["extracted"]
        if not extracted.exists():
            continue
        for path in sorted(extracted.rglob("*")):
            if path.is_file():
                entries.append(
                    inventory_entry(meta["archive_id"], archive_name, archive_hash, path, extracted)
                )
    # duplicate groups by content_hash
    by_hash: dict[str, list[int]] = {}
    for i, e in enumerate(entries):
        by_hash.setdefault(e["content_hash"], []).append(i)
    for h, idxs in by_hash.items():
        if len(idxs) > 1:
            group = f"dup-{h[:12]}"
            for i in idxs:
                entries[i]["duplicate_group"] = group
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "archives": archive_meta,
        "file_count": len(entries),
        "entries": entries,
    }


def schema_block(id_suffix: str, title: str, props: dict, required: list[str]) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://schemas.marketsynth.ai/external-artifacts/0.1.0/{id_suffix}",
        "title": title,
        "type": "object",
        "additionalProperties": False,
        "properties": props,
        "required": required,
    }


def build_external_artifact_schemas() -> str:
    write_json(
        SCHEMA_ROOT / "provenance.schema.json",
        schema_block(
            "provenance.schema.json",
            "ExternalArtifactProvenance",
            {
                "source_type": {"type": "string"},
                "source_id": {"type": "string"},
                "archive_id": {"type": "string"},
                "archive_hash": {"type": "string"},
                "generated_at": {"type": "string"},
            },
            ["source_type", "archive_id"],
        ),
    )
    trust_status = {
        "type": "string",
        "enum": [
            "untrusted",
            "quarantined",
            "statically_validated",
            "methodology_approved",
            "platform_adapted",
            "rejected",
        ],
    }
    write_json(
        SCHEMA_ROOT / "knowledge-artifact.schema.json",
        schema_block(
            "knowledge-artifact.schema.json",
            "KnowledgeArtifact",
            {
                "artifact_id": {"type": "string"},
                "artifact_type": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "source_reference": {"type": "string"},
                "source_archive_id": {"type": "string"},
                "source_path": {"type": "string"},
                "content_hash": {"type": "string", "minLength": 64, "maxLength": 64},
                "language": {"type": "string"},
                "domain": {"type": "string"},
                "capabilities": {"type": "array", "items": {"type": "string"}},
                "products_or_platforms": {"type": "array", "items": {"type": "string"}},
                "methodology": {"type": "boolean"},
                "prerequisites": {"type": "array", "items": {"type": "string"}},
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "security_findings": {"type": "array", "items": {"type": "string"}},
                "quality_status": {"type": "string"},
                "trust_status": trust_status,
                "lifecycle_status": {"type": "string"},
                "tenant_scope": {"type": "string"},
                "provenance": {"$ref": "provenance.schema.json"},
                "created_at": {"type": "string"},
                "verified_at": {"type": "string"},
                "supersedes": {"type": "string"},
                "related_artifact_ids": {"type": "array", "items": {"type": "string"}},
            },
            [
                "artifact_id",
                "artifact_type",
                "title",
                "summary",
                "source_reference",
                "source_archive_id",
                "source_path",
                "content_hash",
                "trust_status",
                "lifecycle_status",
                "tenant_scope",
                "provenance",
            ],
        ),
    )
    for fname, title, props, req in [
        (
            "workflow-template.schema.json",
            "WorkflowTemplate",
            {
                "workflow_template_id": {"type": "string"},
                "original_name": {"type": "string"},
                "normalized_name": {"type": "string"},
                "description": {"type": "string"},
                "category": {"type": "string"},
                "use_case": {"type": "string"},
                "trigger_types": {"type": "array", "items": {"type": "string"}},
                "node_types": {"type": "array", "items": {"type": "string"}},
                "providers": {"type": "array", "items": {"type": "string"}},
                "credentials_required": {"type": "boolean"},
                "side_effects": {"type": "array", "items": {"type": "string"}},
                "publication_actions": {"type": "boolean"},
                "billing_actions": {"type": "boolean"},
                "destructive_actions": {"type": "boolean"},
                "personal_data_risk": {"type": "string"},
                "security_findings": {"type": "array", "items": {"type": "string"}},
                "workflow_hash": {"type": "string"},
                "quarantine_status": {"type": "string"},
                "adaptation_status": {
                    "type": "string",
                    "enum": [
                        "catalog_only",
                        "requires_rewrite",
                        "reusable_pattern",
                        "rejected",
                        "deferred",
                        "adapted_internal_template",
                    ],
                },
                "target_capabilities": {"type": "array", "items": {"type": "string"}},
                "commercial_priority": {"type": "string"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            [
                "workflow_template_id",
                "original_name",
                "normalized_name",
                "category",
                "trigger_types",
                "node_types",
                "workflow_hash",
                "quarantine_status",
                "adaptation_status",
                "provenance",
            ],
        ),
        (
            "practice-record.schema.json",
            "PracticeRecord",
            {
                "practice_id": {"type": "string"},
                "domain": {"type": "string"},
                "context": {"type": "string"},
                "problem": {"type": "string"},
                "decision": {"type": "string"},
                "rationale": {"type": "string"},
                "verification_status": {
                    "type": "string",
                    "enum": [
                        "claimed",
                        "source_documented",
                        "reproduced",
                        "regression_tested",
                        "obsolete",
                        "contradicted",
                        "unknown",
                    ],
                },
                "provenance": {"$ref": "provenance.schema.json"},
            },
            ["practice_id", "domain", "problem", "decision", "verification_status", "provenance"],
        ),
        (
            "error-pattern.schema.json",
            "ErrorPattern",
            {
                "error_pattern_id": {"type": "string"},
                "platform": {"type": "string"},
                "component": {"type": "string"},
                "symptom": {"type": "string"},
                "likely_cause": {"type": "string"},
                "remediation": {"type": "string"},
                "verification_status": {"type": "string"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            ["error_pattern_id", "platform", "symptom", "remediation", "provenance"],
        ),
        (
            "knowledge-link.schema.json",
            "KnowledgeLink",
            {
                "link_id": {"type": "string"},
                "source_artifact_id": {"type": "string"},
                "target_artifact_id": {"type": "string"},
                "relation": {"type": "string"},
                "reason": {"type": "string"},
                "confidence": {"type": "string"},
                "tenant_scope": {"type": "string"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            [
                "link_id",
                "source_artifact_id",
                "target_artifact_id",
                "relation",
                "reason",
                "tenant_scope",
                "provenance",
            ],
        ),
        (
            "security-finding.schema.json",
            "SecurityFinding",
            {
                "finding_id": {"type": "string"},
                "severity": {"type": "string"},
                "finding_type": {"type": "string"},
                "location": {"type": "string"},
                "description": {"type": "string"},
                "redacted": {"type": "boolean"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            ["finding_id", "severity", "finding_type", "description", "provenance"],
        ),
        (
            "source-reference.schema.json",
            "SourceReference",
            {
                "archive_id": {"type": "string"},
                "archive_hash": {"type": "string"},
                "relative_path": {"type": "string"},
                "content_hash": {"type": "string"},
            },
            ["archive_id", "relative_path", "content_hash"],
        ),
        (
            "import-report.schema.json",
            "ImportReport",
            {
                "report_id": {"type": "string"},
                "archive_count": {"type": "integer"},
                "file_count": {"type": "integer"},
                "workflow_count": {"type": "integer"},
                "security_finding_count": {"type": "integer"},
                "generated_at": {"type": "string"},
            },
            ["report_id", "file_count", "generated_at"],
        ),
        (
            "methodology-record.schema.json",
            "MethodologyRecord",
            {
                "methodology_id": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "domain": {"type": "string"},
                "steps": {"type": "array", "items": {"type": "string"}},
                "quality_gates": {"type": "array", "items": {"type": "string"}},
                "verification_status": {"type": "string"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            ["methodology_id", "title", "domain", "verification_status", "provenance"],
        ),
        (
            "workflow-node-reference.schema.json",
            "WorkflowNodeReference",
            {
                "node_id": {"type": "string"},
                "node_type": {"type": "string"},
                "node_version": {"type": "string"},
                "role": {"type": "string"},
                "provider": {"type": "string"},
                "security_class": {"type": "string"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            ["node_id", "node_type", "provenance"],
        ),
        (
            "dependency-reference.schema.json",
            "DependencyReference",
            {
                "dependency_id": {"type": "string"},
                "dependency_type": {"type": "string"},
                "name": {"type": "string"},
                "version_scope": {"type": "string"},
                "requires_reverification": {"type": "boolean"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            ["dependency_id", "dependency_type", "name", "provenance"],
        ),
        (
            "quality-gate.schema.json",
            "QualityGate",
            {
                "gate_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "severity": {"type": "string"},
                "applies_to": {"type": "array", "items": {"type": "string"}},
                "verification_status": {"type": "string"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            ["gate_id", "title", "severity", "provenance"],
        ),
    ]:
        write_json(SCHEMA_ROOT / fname, schema_block(fname, title, props, req))

    files = sorted(p.name for p in SCHEMA_ROOT.glob("*.schema.json"))
    file_hashes = {n: sha256_file(SCHEMA_ROOT / n) for n in files}
    bundle_hash = sha256_bytes(
        json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode()
    )
    write_json(
        SCHEMA_ROOT / "freeze_manifest.json",
        {
            "schema_version": "0.1.0",
            "canonical_uri_base": "https://schemas.marketsynth.ai/external-artifacts/0.1.0/",
            "schema_status": "frozen",
            "file_hashes": file_hashes,
            "bundle_hash": bundle_hash,
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    return bundle_hash


def parse_workflow_json(path: Path, archive_id: str, rel: str) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or "nodes" not in data:
        return None
    nodes = data.get("nodes") or []
    node_types = sorted({n.get("type", "unknown") for n in nodes if isinstance(n, dict)})
    triggers = [t for t in node_types if "trigger" in t.lower() or "Trigger" in t]
    name = data.get("name") or path.stem
    wf_hash = sha256_file(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    security: list[str] = []
    if re.search(r"sk-[a-zA-Z0-9]{20,}", text):
        security.append("embedded_api_key_pattern")
    if any("n8n-nodes-base.executeCommand" in t for t in node_types):
        security.append("shell_command_node")
    if any("code" in t.lower() for t in node_types):
        security.append("code_node")
    pub = any(
        k in t.lower()
        for t in node_types
        for k in ("telegram", "instagram", "facebook", "linkedin", "wordpress", "gmail")
    )
    category = "other"
    nl = name.lower()
    if any(k in nl for k in ("seo", "keyword", "audit")):
        category = "seo"
    elif any(k in nl for k in ("blog", "content", "wordpress")):
        category = "content_generation"
    elif any(k in nl for k in ("lead", "crm", "whatsapp")):
        category = "lead_generation"
    elif any(k in nl for k in ("backup", "резерв")):
        category = "backup"
    elif any(k in nl for k in ("telegram", "instagram", "social")):
        category = "social_publication"
    priority = "reference_only"
    if category in {"seo", "content_generation", "lead_generation"}:
        priority = "P1_content_and_analytics"
    if any(k in nl for k in ("research", "competitor", "review")):
        priority = "P0_core_marketing"
    return {
        "workflow_template_id": f"wf-{wf_hash[:16]}",
        "original_name": name,
        "normalized_name": re.sub(r"[^\w\s-]", "", name)[:120],
        "description": "",
        "category": category,
        "use_case": name[:200],
        "trigger_types": triggers or node_types[:3],
        "node_types": node_types,
        "providers": [],
        "credentials_required": "credentials" in text.lower(),
        "side_effects": ["publication"] if pub else [],
        "publication_actions": pub,
        "billing_actions": False,
        "destructive_actions": "DELETE" in text.upper() or "DROP TABLE" in text.upper(),
        "personal_data_risk": "elevated" if re.search(r"@\w+\.\w+", text) else "unknown",
        "security_findings": security,
        "workflow_hash": wf_hash,
        "quarantine_status": "quarantined",
        "adaptation_status": "catalog_only",
        "target_capabilities": [category],
        "commercial_priority": priority,
        "provenance": {
            "source_type": "external_archive",
            "archive_id": archive_id,
            "relative_path": rel,
        },
    }


def build_workflow_catalog(inventory: dict[str, Any]) -> dict[str, Any]:
    templates: list[dict[str, Any]] = []
    wf_root = INTAKE / "bots-knowledge"
    archive_id = "arc-bots-knowledge-rar"
    if wf_root.exists():
        for path in sorted(wf_root.rglob("*.json")):
            rel = str(path.relative_to(wf_root)).replace("\\", "/")
            if "воркфлоу" not in rel and "workflow" not in rel.lower():
                # still parse n8n json anywhere under bots-knowledge
                pass
            parsed = parse_workflow_json(path, archive_id, rel)
            if parsed:
                templates.append(parsed)
    # dedupe by workflow_hash
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for t in templates:
        h = t["workflow_hash"]
        if h not in seen:
            seen.add(h)
            unique.append(t)
    catalog = {
        "schema_version": "0.1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "workflow_count": len(unique),
        "duplicate_count": len(templates) - len(unique),
        "templates": unique,
    }
    write_json(CATALOG_PKG / "catalog.json", catalog)
    return catalog


def write_workflow_catalog_docs(catalog: dict[str, Any]) -> None:
    wf_docs = REPO / "docs" / "research" / "workflow-catalog"
    wf_docs.mkdir(parents=True, exist_ok=True)
    templates = catalog.get("templates", [])
    by_cat: dict[str, list[dict[str, Any]]] = {}
    rejected: list[dict[str, Any]] = []
    security_counts: dict[str, int] = {}
    for t in templates:
        cat = t.get("category", "other")
        by_cat.setdefault(cat, []).append(t)
        if t.get("adaptation_status") == "rejected":
            rejected.append(t)
        for f in t.get("security_findings", []):
            security_counts[f] = security_counts.get(f, 0) + 1
    write_text(
        wf_docs / "README.md",
        "# Workflow Template Quarantine Catalog\n\n"
        "Read-only metadata from external n8n JSON. **No deployment.**\n\n"
        f"- Unique templates: **{catalog.get('workflow_count', 0)}**\n"
        f"- Duplicates removed: **{catalog.get('duplicate_count', 0)}**\n"
        f"- Default status: **catalog_only / quarantined**\n",
    )
    write_text(
        wf_docs / "workflow-index.md",
        "# Workflow Index\n\n"
        + "\n".join(
            f"- `{t['workflow_template_id']}` — {t['original_name'][:80]}"
            for t in templates[:50]
        )
        + (f"\n\n… and {max(0, len(templates) - 50)} more.\n" if len(templates) > 50 else "\n"),
    )
    for fname, cats in [
        ("marketing-workflows.md", {"seo", "lead_generation", "competitor_analysis", "marketing_research"}),
        ("content-workflows.md", {"content_generation", "content_strategy", "social_publication"}),
        ("analytics-workflows.md", {"analytics", "seo"}),
        ("knowledge-and-rag-workflows.md", {"rag", "knowledge_base"}),
        ("engineering-workflows.md", {"backup", "monitoring", "development", "agent_orchestration"}),
    ]:
        items = [t for t in templates if t.get("category") in cats]
        write_text(
            wf_docs / fname,
            f"# {fname.replace('-', ' ').replace('.md', '').title()}\n\n"
            f"Count: **{len(items)}**\n\n"
            + "\n".join(f"- {t['original_name'][:100]}" for t in items[:30])
            + "\n",
        )
    write_text(
        wf_docs / "rejected-workflows.md",
        "# Rejected Workflows\n\n"
        f"Explicitly rejected: **{len(rejected)}**\n\n"
        "Destructive or unsafe workflows remain catalog_only until security review.\n",
    )
    write_text(
        wf_docs / "security-summary.md",
        "# Security Summary\n\n"
        + "\n".join(f"- `{k}`: {v}" for k, v in sorted(security_counts.items()))
        + "\n",
    )


def write_inventory_docs(inventory: dict[str, Any], catalog: dict[str, Any]) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    write_json(DOCS / "archive-checksums.json", inventory)
    totals = {"ADAPT": 0, "QUARANTINE": 0, "REJECT": 0, "DEFER": 0}
    for e in inventory["entries"]:
        d = e.get("proposed_decision", "DEFER")
        totals[d] = totals.get(d, 0) + 1
    write_text(
        DOCS / "README.md",
        "# External Archives — KB-SKILL-01\n\n"
        "Controlled intake of four external archives. **No direct installation.**\n\n"
        f"- Files inventoried: **{inventory['file_count']}**\n"
        f"- Workflow templates cataloged: **{catalog.get('workflow_count', 0)}**\n"
        f"- Duplicate workflows: **{catalog.get('duplicate_count', 0)}**\n",
    )
    write_text(
        DOCS / "source-inventory.md",
        "# Source Inventory\n\n"
        + "\n".join(
            f"- **{a['archive_name']}** `{a['archive_hash'][:16]}…`"
            for a in inventory["archives"]
        )
        + f"\n\nTotal files: {inventory['file_count']}\n",
    )
    write_text(
        DOCS / "adopt-adapt-reject-matrix.md",
        "# Adopt / Adapt / Quarantine / Reject\n\n"
        "| Decision | Count |\n|----------|-------|\n"
        + "\n".join(f"| {k} | {v} |" for k, v in sorted(totals.items()))
        + "\n",
    )
    write_text(
        DOCS / "source-risk-register.md",
        "# Source Risk Register\n\n"
        "- External Skills (.skill, SKILL.md) → QUARANTINE\n"
        "- Executable scripts (.py) → QUARANTINE, never run during audit\n"
        "- 249 n8n workflow JSON → catalog_only, no deployment\n"
        "- Unknown licenses on all archives → DEFER legal review\n"
        "- Credential markers in workflow JSON → redact, never bind\n",
    )
    write_text(
        DOCS / "duplicate-content-report.md",
        f"# Duplicate Content\n\n"
        f"Workflow exact duplicates removed: **{catalog.get('duplicate_count', 0)}**\n\n"
        f"File-level duplicate groups: **{sum(1 for e in inventory['entries'] if e.get('duplicate_group'))}** entries in groups\n",
    )
    write_text(
        DOCS / "license-and-provenance-report.md",
        "# License and Provenance\n\n"
        "All four archives: **license_status = unknown**, **provenance_status = external_archive**.\n\n"
        "Do not treat as MIT/Apache without explicit license file.\n",
    )


def main() -> None:
    print("KB-SKILL-01 build starting...")
    inventory = build_inventory()
    bundle = build_external_artifact_schemas()
    catalog = build_workflow_catalog(inventory)
    write_workflow_catalog_docs(catalog)
    write_inventory_docs(inventory, catalog)
    print(f"Inventory files: {inventory['file_count']}")
    print(f"External artifacts bundle: {bundle}")
    print(f"Workflow templates: {catalog['workflow_count']}")


if __name__ == "__main__":
    main()
