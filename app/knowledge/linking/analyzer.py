"""Knowledge linking — deterministic link analysis without filesystem mutation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

WIKI_LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


@dataclass
class ArtifactRef:
    artifact_id: str
    title: str
    tenant_scope: str = "global"
    tags: list[str] = field(default_factory=list)
    existing_links: list[dict] = field(default_factory=list)


@dataclass
class LinkAnalysisResult:
    proposed_links: list[dict]
    broken_links: list[dict]
    orphan_artifacts: list[str]
    cross_tenant_link_rejections: list[dict]
    human_review_required: bool


def _title_index(artifacts: list[ArtifactRef]) -> dict[str, str]:
    return {a.title.lower().strip(): a.artifact_id for a in artifacts}


def extract_wiki_links(text: str) -> list[str]:
    return [m.group(1).strip() for m in WIKI_LINK.finditer(text)]


def analyze_links(
    artifacts: list[ArtifactRef],
    *,
    tenant_id: str = "global",
) -> LinkAnalysisResult:
    title_to_id = _title_index(artifacts)
    incoming: dict[str, set[str]] = {a.artifact_id: set() for a in artifacts}
    proposed: list[dict] = []
    broken: list[dict] = []
    cross_tenant: list[dict] = []

    for artifact in artifacts:
        if artifact.tenant_scope not in ("global", tenant_id):
            continue
        for link in artifact.existing_links:
            target_id = link.get("target_artifact_id", "")
            target = next((a for a in artifacts if a.artifact_id == target_id), None)
            if target is None:
                broken.append(
                    {
                        "source_artifact_id": artifact.artifact_id,
                        "target_artifact_id": target_id,
                        "reason": "missing_target",
                    }
                )
                continue
            if target.tenant_scope not in ("global", tenant_id):
                cross_tenant.append(
                    {
                        "source_artifact_id": artifact.artifact_id,
                        "target_artifact_id": target_id,
                        "reason": "cross_tenant",
                    }
                )
                continue
            incoming[target_id].add(artifact.artifact_id)
            proposed.append(
                {
                    "source_artifact_id": artifact.artifact_id,
                    "target_artifact_id": target_id,
                    "relation": link.get("relation", "related_to"),
                    "reason": link.get("reason", "existing_link"),
                    "confidence": link.get("confidence", "medium"),
                }
            )
        for title in extract_wiki_links(artifact.title):
            target_id = title_to_id.get(title.lower())
            if not target_id:
                broken.append(
                    {
                        "source_artifact_id": artifact.artifact_id,
                        "target_title": title,
                        "reason": "unresolved_wiki_link",
                    }
                )

    orphans = [
        a.artifact_id
        for a in artifacts
        if not incoming[a.artifact_id] and a.tenant_scope in ("global", tenant_id)
    ]
    return LinkAnalysisResult(
        proposed_links=proposed,
        broken_links=broken,
        orphan_artifacts=orphans,
        cross_tenant_link_rejections=cross_tenant,
        human_review_required=bool(broken or cross_tenant),
    )
