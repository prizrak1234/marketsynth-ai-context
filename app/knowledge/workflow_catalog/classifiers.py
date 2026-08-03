"""Explainable workflow capability, approval, and priority classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.knowledge.workflow_catalog.contracts import CommercialPriority
from app.knowledge.workflow_catalog.normalization import node_type_suffix

CAPABILITY_RULES: list[tuple[str, list[str], list[str], list[str]]] = [
    ("seo", ["seo", "keyword", "wordstat", "audit"], ["serpapi"], []),
    (
        "publication",
        ["publish", "post to", "telegram post", "instagram post"],
        ["telegram", "instagram", "facebook", "wordpress", "twitter"],
        ["publication"],
    ),
    ("lead_generation", ["lead", "лид", "crm", "whatsapp"], ["hubspot", "pipedrive"], []),
    ("blog_generation", ["blog", "article", "wordpress post"], ["wordpress"], []),
    ("social_content", ["social", "carousel", "reddit"], ["instagram", "linkedin", "reddit"], []),
    ("agent_orchestration", ["agent", "orchestr"], ["langchain"], []),
    ("rag", ["rag", "embedding", "vector store"], ["perplexity"], []),
    ("review_analysis", ["review", "отзыв"], [], []),
    ("market_research", ["research", "market", "competitor"], ["serpapi"], []),
    ("scheduling", ["schedule", "cron", "timer"], ["scheduleTrigger"], []),
    ("customer_support", ["support", "ticket", "helpdesk"], [], []),
    ("analytics", ["analytics", "metric", "report"], ["googleAnalytics"], []),
    ("email_marketing", ["newsletter", "email campaign", "email marketing"], ["gmail", "smtp"], []),
]

DOCUMENTATION_NAME_KEYS = (
    "documentation",
    "document workflow",
    "workflow doc",
    "markdown doc",
    "generate docs",
    "export description",
)
DOCUMENTATION_NODE_SUFFIXES = ("googleDocs", "htmlcsstopdf", "markdown")
BACKUP_NAME_KEYS = ("backup", "резерв", "snapshot", "restore workflow", "export workflow")
BACKUP_NODE_SUFFIXES = ("n8n", "googleDrive")

APPROVAL_EXPLICIT_KEYS = (
    "approve",
    "reject",
    "human approval",
    "human review",
    "moderation",
    "hitl",
    "wait for approval",
)
APPROVAL_PROBABLE_KEYS = ("confirm", "review status", "pending approval", "awaiting approval")


@dataclass(frozen=True)
class ClassificationResult:
    categories: list[str]
    commercial_priority: CommercialPriority
    explanation: list[str] = field(default_factory=list)
    capability_confidence: str = "medium"
    priority_confidence: str = "medium"
    priority_reasons: list[str] = field(default_factory=list)
    approval_signal_strength: str = "none"
    approval_explanation: list[str] = field(default_factory=list)


def classify_workflow(
    name: str,
    description: str,
    node_types: list[str],
    providers: list[str],
    side_effects: list[str],
    *,
    nodes: list[dict[str, Any]],
    documentation_quality: str,
) -> ClassificationResult:
    nl = name.lower()
    dl = description.lower()
    explanation: list[str] = []
    matched: list[str] = []
    provider_blob = " ".join(providers).lower()
    node_suffixes = [node_type_suffix(t) for t in node_types]
    suffix_blob = " ".join(node_suffixes).lower()
    text_blob = f"{nl} {dl}"

    for cap, name_keys, provider_keys, effect_keys in CAPABILITY_RULES:
        if any(k in nl or k in dl for k in name_keys):
            matched.append(cap)
            explanation.append(f"name/description matched {cap}")
        elif any(k.lower() in provider_blob for k in provider_keys):
            matched.append(cap)
            explanation.append(f"provider matched {cap}")
        elif any(k.lower() in suffix_blob for k in provider_keys):
            matched.append(cap)
            explanation.append(f"integrated node matched {cap}")
        elif effect_keys and any(e in side_effects for e in effect_keys):
            matched.append(cap)
            explanation.append(f"side_effect matched {cap}")

    if _matches_documentation_capability(text_blob, node_suffixes, nodes):
        matched.append("workflow_documentation")
        explanation.append("explicit documentation workflow signal")

    if _matches_backup_capability(text_blob, node_suffixes, nodes):
        matched.append("workflow_backup")
        explanation.append("explicit backup workflow signal")

    approval_strength, approval_expl = _approval_signal(nodes, node_types, text_blob)
    if approval_strength in {"probable", "explicit"}:
        matched.append("human_approval")
        explanation.extend(approval_expl)

    categories = sorted(set(matched)) or ["other"]
    cap_conf = _capability_confidence(categories, explanation)
    priority, pri_conf, pri_reasons = _priority(
        categories,
        nl,
        dl,
        providers,
        side_effects,
        explanation,
        cap_conf,
    )
    return ClassificationResult(
        categories=categories,
        commercial_priority=priority,
        explanation=explanation,
        capability_confidence=cap_conf,
        priority_confidence=pri_conf,
        priority_reasons=pri_reasons,
        approval_signal_strength=approval_strength,
        approval_explanation=approval_expl,
    )


def _matches_documentation_capability(
    text_blob: str,
    node_suffixes: list[str],
    nodes: list[dict[str, Any]],
) -> bool:
    name_hit = any(key in text_blob for key in DOCUMENTATION_NAME_KEYS)
    node_hit = any(suffix in DOCUMENTATION_NODE_SUFFIXES for suffix in node_suffixes)
    action_hit = False
    doc_keys = ("markdown", "documentation", "export doc")
    for node in nodes:
        if not isinstance(node, dict):
            continue
        params = node.get("parameters")
        if not isinstance(params, dict):
            continue
        operation = str(params.get("operation", "")).lower()
        if operation in {"create", "update", "export", "generate"} and node_hit:
            action_hit = True
        if any(key in str(params.get("title", "")).lower() for key in doc_keys):
            action_hit = True
    return name_hit and (node_hit or action_hit)


def _matches_backup_capability(
    text_blob: str,
    node_suffixes: list[str],
    nodes: list[dict[str, Any]],
) -> bool:
    name_hit = any(k in text_blob for k in BACKUP_NAME_KEYS)
    node_hit = any(suffix in BACKUP_NODE_SUFFIXES for suffix in node_suffixes)
    action_hit = False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        params = node.get("parameters")
        if not isinstance(params, dict):
            continue
        operation = str(params.get("operation", "")).lower()
        if operation in {
            "get",
            "getworkflow",
            "list",
            "listworkflow",
            "export",
            "backup",
            "snapshot",
            "restore",
        }:
            action_hit = True
    storage_hit = "googleDrive" in node_suffixes
    return (name_hit and (node_hit or storage_hit)) or action_hit


def _approval_signal(
    nodes: list[dict[str, Any]],
    node_types: list[str],
    text_blob: str,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    explicit = False
    probable = False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type", ""))
        suffix = node_type_suffix(node_type)
        name = str(node.get("name", "")).lower()
        params_text = str(node.get("parameters", "")).lower()
        blob = f"{name} {params_text} {node_type.lower()}"
        if suffix in {"slackHitlTool"} or "hitl" in node_type.lower():
            explicit = True
            reasons.append("human-in-the-loop node detected")
        if any(k in blob for k in APPROVAL_EXPLICIT_KEYS):
            explicit = True
            reasons.append(f"explicit approval marker in node {name or suffix}")
        elif any(k in blob for k in APPROVAL_PROBABLE_KEYS):
            probable = True
            reasons.append(f"probable approval marker in node {name or suffix}")
    if any(k in text_blob for k in APPROVAL_EXPLICIT_KEYS):
        explicit = True
        reasons.append("explicit approval marker in workflow text")
    elif any(k in text_blob for k in APPROVAL_PROBABLE_KEYS):
        probable = True
        reasons.append("probable approval marker in workflow text")

    if explicit:
        return "explicit", reasons
    if probable:
        return "probable", reasons
    weak_markers = any(
        node_type_suffix(t) in {"if", "wait", "switch", "stickyNote"} for t in node_types
    )
    if weak_markers:
        return "weak", ["branch/wait/note only — not approval"]
    return "none", []


def _capability_confidence(categories: list[str], explanation: list[str]) -> str:
    if categories == ["other"]:
        return "low"
    strong_prefixes = ("name/description matched", "explicit", "side_effect matched")
    strong = sum(1 for e in explanation if e.startswith(strong_prefixes))
    if strong >= 2:
        return "high"
    if strong == 1:
        return "medium"
    if any("integrated node matched" in e for e in explanation):
        return "medium"
    return "low"


def _priority(
    categories: list[str],
    name_lower: str,
    desc_lower: str,
    providers: list[str],
    side_effects: list[str],
    explanation: list[str],
    capability_confidence: str,
) -> tuple[CommercialPriority, str, list[str]]:
    reasons: list[str] = []
    marketing_caps = {
        "seo",
        "publication",
        "lead_generation",
        "blog_generation",
        "social_content",
        "analytics",
        "market_research",
        "email_marketing",
    }
    p0_keys = ("research", "competitor", "market", "review")
    p0_name = any(key in name_lower or key in desc_lower for key in p0_keys)
    p1_caps = marketing_caps.intersection(categories)
    engineering_keys = {"workflow_backup", "workflow_documentation", "development"}
    engineering_caps = engineering_keys.intersection(categories)

    if p0_name and (p1_caps or capability_confidence != "low"):
        reasons.append("P0: marketing objective in name/description with capability evidence")
        return "P0_core_marketing", "high" if p1_caps else "medium", reasons

    if p1_caps:
        reasons.append(f"P1: marketing capabilities {sorted(p1_caps)}")
        if side_effects:
            reasons.append(f"side_effects: {side_effects}")
        if providers:
            reasons.append(f"providers: {providers[:5]}")
        conf = "high" if capability_confidence == "high" else "medium"
        return "P1_content_distribution_analytics", conf, reasons

    if engineering_caps:
        reasons.append(f"engineering capabilities {sorted(engineering_caps)}")
        return "engineering_reference", "medium", reasons

    if "agent_orchestration" in categories or "langchain" in " ".join(providers).lower():
        reasons.append("platform/agent extension signal")
        return "P2_platform_extensions", "medium", reasons

    if categories == ["other"]:
        reasons.append("no confident marketing capability")
        return "catalog_only", "low", reasons

    reasons.append("residual capability without strong marketing fit")
    conf = "low" if capability_confidence == "low" else "medium"
    return "P2_platform_extensions", conf, reasons
