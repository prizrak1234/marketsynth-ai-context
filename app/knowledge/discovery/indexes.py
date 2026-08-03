"""In-memory deterministic discovery indexes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.knowledge.capability_model.serialization import (
    load_capabilities,
    load_capability_gaps,
    load_capability_skill_bindings,
    load_connector_tool_bindings,
    load_pattern_connector_bindings,
    load_professions,
    load_skill_pattern_bindings,
)
from app.knowledge.discovery.serialization import load_aliases
from app.knowledge.discovery.tokenization import normalize_text, tokenize
from app.knowledge.n8n_engineering.constants import KNOWN_PATTERN_IDS
from app.knowledge.workflow_patterns.serialization import load_library_index

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "packages" / "skills"


@dataclass
class DiscoverySources:
    professions: list[dict[str, Any]]
    capabilities: list[dict[str, Any]]
    skill_bindings: list[dict[str, Any]]
    pattern_bindings: list[dict[str, Any]]
    connector_bindings: list[dict[str, Any]]
    tool_bindings: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    patterns: list[dict[str, Any]]
    aliases: list[dict[str, Any]]
    quarantined_templates: list[dict[str, Any]] = field(default_factory=list)
    rejected_artifacts: list[dict[str, Any]] = field(default_factory=list)
    tenant_private_skills: list[dict[str, Any]] = field(default_factory=list)
    error_patterns: list[dict[str, Any]] = field(default_factory=list)
    practice_records: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DiscoveryIndexes:
    profession_by_id: dict[str, dict[str, Any]]
    profession_by_token: dict[str, list[str]]
    capability_by_id: dict[str, dict[str, Any]]
    capability_by_token: dict[str, list[str]]
    skill_by_id: dict[str, dict[str, Any]]
    skill_by_capability: dict[str, list[str]]
    pattern_by_id: dict[str, dict[str, Any]]
    pattern_by_capability: dict[str, list[str]]
    gap_by_capability: dict[str, list[dict[str, Any]]]
    connector_class_by_capability: dict[str, list[str]]
    tool_class_by_capability: dict[str, list[str]]
    alias_by_phrase: dict[str, dict[str, Any]]
    dependency_graph: list[dict[str, Any]]


def _load_skill_manifest(skill_dir: Path) -> dict[str, Any] | None:
    manifest_path = skill_dir / "manifest.yaml"
    if not manifest_path.is_file():
        for sub in skill_dir.iterdir():
            if sub.is_dir() and (sub / "manifest.yaml").is_file():
                manifest_path = sub / "manifest.yaml"
                break
        else:
            return None
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return {
        "skill_id": data.get("id", skill_dir.name),
        "title": data.get("name", skill_dir.name),
        "version": data.get("version", "0.1.0"),
        "status": data.get("status", "candidate"),
        "tenant_scope": data.get("tenant_scope", "global"),
        "tenant_id": data.get("tenant_id"),
        "project_id": data.get("project_id"),
        "trust_status": "candidate",
        "maturity": "reviewed",
        "executable": data.get("activation_conditions", {}).get("executable", False),
    }


def load_default_sources(extra: DiscoverySources | None = None) -> DiscoverySources:
    skills: list[dict[str, Any]] = []
    if SKILLS_ROOT.is_dir():
        for path in sorted(SKILLS_ROOT.iterdir()):
            if path.is_dir() and path.name.startswith("ms.skill."):
                manifest = _load_skill_manifest(path)
                if manifest:
                    skills.append(manifest)
    library = load_library_index()
    patterns = [
        {
            "pattern_id": entry["pattern_id"],
            "title": entry["pattern_id"].replace("_", " ").title(),
            "maturity": entry.get("maturity", "reviewed"),
            "trust_status": "reviewed",
            "tenant_scope": entry.get("tenant_scope", "tenant_scoped"),
        }
        for entry in library.get("pattern_entries", [])
        if entry["pattern_id"] in KNOWN_PATTERN_IDS
    ]
    base = DiscoverySources(
        professions=load_professions(),
        capabilities=load_capabilities(),
        skill_bindings=load_capability_skill_bindings(),
        pattern_bindings=load_skill_pattern_bindings(),
        connector_bindings=load_pattern_connector_bindings(),
        tool_bindings=load_connector_tool_bindings(),
        gaps=load_capability_gaps(),
        skills=skills,
        patterns=patterns,
        aliases=load_aliases(),
        error_patterns=[
            {
                "error_pattern_id": "n8n_expression_error",
                "symptoms": ["expression error", "ошибка n8n", "type mismatch"],
                "capability_ids": ["engineering.workflow_debugging"],
            }
        ],
        practice_records=[
            {
                "practice_id": "human_approval_before_write_or_publication",
                "domain": "control_and_safety",
                "capability_ids": ["marketing.distribution"],
            }
        ],
    )
    if extra:
        base.skills.extend(extra.skills)
        base.skills.extend(extra.tenant_private_skills)
        base.quarantined_templates.extend(extra.quarantined_templates)
        base.rejected_artifacts.extend(extra.rejected_artifacts)
        base.tenant_private_skills.extend(extra.tenant_private_skills)
    return base


def _index_tokens(text: str, item_id: str, index: dict[str, list[str]]) -> None:
    for token in tokenize(text):
        index.setdefault(token, [])
        if item_id not in index[token]:
            index[token].append(item_id)


def build_indexes(sources: DiscoverySources) -> DiscoveryIndexes:
    profession_by_id = {p["profession_id"]: p for p in sources.professions}
    profession_by_token: dict[str, list[str]] = {}
    for prof in sources.professions:
        _index_tokens(prof["profession_name"], prof["profession_id"], profession_by_token)
        _index_tokens(prof["profession_id"], prof["profession_id"], profession_by_token)

    capability_by_id = {c["capability_id"]: c for c in sources.capabilities}
    capability_by_token: dict[str, list[str]] = {}
    for cap in sources.capabilities:
        _index_tokens(cap["capability_name"], cap["capability_id"], capability_by_token)
        _index_tokens(cap["capability_id"], cap["capability_id"], capability_by_token)
        for alias_token in ("n8n", "workflow", "telegram", "youtube"):
            if alias_token in cap["capability_id"]:
                _index_tokens(alias_token, cap["capability_id"], capability_by_token)

    skill_by_id = {s["skill_id"]: s for s in sources.skills}
    skill_by_capability: dict[str, list[str]] = {}
    for binding in sources.skill_bindings:
        cap_id = binding.get("capability_id")
        skill_id = binding.get("skill_id")
        if cap_id and skill_id and skill_id.startswith("ms.skill."):
            skill_by_capability.setdefault(cap_id, [])
            if skill_id not in skill_by_capability[cap_id]:
                skill_by_capability[cap_id].append(skill_id)

    pattern_by_id = {p["pattern_id"]: p for p in sources.patterns}
    pattern_by_capability: dict[str, list[str]] = {}
    for binding in sources.pattern_bindings:
        cap_id = binding.get("capability_id")
        pid = binding.get("pattern_id")
        if cap_id and pid:
            pattern_by_capability.setdefault(cap_id, [])
            if pid not in pattern_by_capability[cap_id]:
                pattern_by_capability[cap_id].append(pid)

    gap_by_capability: dict[str, list[dict[str, Any]]] = {}
    for gap in sources.gaps:
        gap_by_capability.setdefault(gap["capability_id"], []).append(gap)

    connector_class_by_capability: dict[str, list[str]] = {}
    for cap in sources.capabilities:
        connector_class_by_capability[cap["capability_id"]] = list(
            cap.get("required_connector_classes") or []
        )

    tool_class_by_capability: dict[str, list[str]] = {}
    for cap in sources.capabilities:
        tool_class_by_capability[cap["capability_id"]] = list(
            cap.get("required_tool_classes") or []
        )

    alias_by_phrase = {normalize_text(a["alias"]): a for a in sources.aliases}

    from app.knowledge.capability_model.serialization import load_capability_dependencies

    return DiscoveryIndexes(
        profession_by_id=profession_by_id,
        profession_by_token=profession_by_token,
        capability_by_id=capability_by_id,
        capability_by_token=capability_by_token,
        skill_by_id=skill_by_id,
        skill_by_capability=skill_by_capability,
        pattern_by_id=pattern_by_id,
        pattern_by_capability=pattern_by_capability,
        gap_by_capability=gap_by_capability,
        connector_class_by_capability=connector_class_by_capability,
        tool_class_by_capability=tool_class_by_capability,
        alias_by_phrase=alias_by_phrase,
        dependency_graph=load_capability_dependencies(),
    )
