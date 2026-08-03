"""Generate KB-WPL-01.7 capability model bundle (one-time generator)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "packages" / "knowledge" / "capability_model" / "0.1.0"
SCHEMAS = BUNDLE / "schemas"

PROVENANCE = {
    "origin": "platform_native",
    "phase": "KB-WPL-01.7",
    "generated_by": "scripts/generate_capability_model_bundle.py",
}

PATTERN_CAPABILITY_MAP: dict[str, list[str]] = {
    "human_approval_before_publication": [
        "marketing.distribution",
        "deliverables.publication_handoff",
        "engineering.runtime_safety",
    ],
    "structured_LLM_to_API_request": [
        "engineering.workflow_architecture",
        "engineering.connector_integration_design",
    ],
    "retry_with_idempotency": [
        "engineering.runtime_safety",
        "engineering.error_recovery",
    ],
    "evidence_grounded_generation": [
        "deliverables.content_architecture",
        "knowledge.knowledge_quality",
        "marketing.market_research",
    ],
    "lead_capture_to_qualification": ["marketing.distribution"],
    "draft_to_human_approval": [
        "deliverables.content_architecture",
        "deliverables.publication_handoff",
    ],
    "workflow_backup": ["engineering.workflow_backup"],
    "error_workflow_or_recovery": ["engineering.error_recovery"],
    "pagination_and_batching": [
        "engineering.workflow_architecture",
        "engineering.runtime_safety",
    ],
    "checkpoint_and_resume": [
        "engineering.error_recovery",
        "engineering.test_and_replay_design",
    ],
    "dead_letter_queue": ["engineering.error_recovery", "engineering.observability"],
    "provider_rate_limit_handling": [
        "engineering.connector_integration_design",
        "engineering.runtime_safety",
    ],
    "quality_gate_after_generation": [
        "deliverables.content_architecture",
        "knowledge.knowledge_quality",
    ],
    "specialist_subworkflow": [
        "engineering.workflow_architecture",
        "platform.professional_task_routing",
    ],
    "supervisor_pattern": [
        "platform.professional_task_routing",
        "engineering.runtime_safety",
    ],
    "tool_workflow_separation": [
        "engineering.connector_integration_design",
        "engineering.runtime_safety",
    ],
    "human_edit_then_resume": [
        "deliverables.publication_handoff",
        "deliverables.content_architecture",
    ],
    "publication_confirmation": [
        "marketing.distribution",
        "knowledge.provenance_management",
    ],
    "source_lineage_preservation": [
        "knowledge.provenance_management",
        "knowledge.lineage_integrity",
    ],
    "customer_feedback_to_learning_candidate": [
        "marketing.learning_and_feedback",
        "knowledge.knowledge_candidate_review",
    ],
}

MARKETING_SKILLS = {
    "marketing.product_context": ["ms.skill.product_marketing_context"],
    "marketing.market_research": ["ms.skill.market_research"],
    "marketing.competitive_intelligence": ["ms.skill.competitor_analysis"],
    "marketing.customer_intelligence": ["ms.skill.icp_segmentation"],
    "marketing.customer_interview_design": ["ms.skill.customer_interview_design"],
    "marketing.customer_meaning_extraction": ["ms.skill.customer_meaning_extraction"],
    "marketing.market_validation": ["ms.skill.market_validation"],
    "marketing.positioning": ["ms.skill.positioning"],
    "marketing.claim_substantiation": ["ms.skill.claim_substantiation"],
    "marketing.offer_architecture": ["ms.skill.offer_builder"],
    "marketing.presentation_architecture": ["ms.skill.presentation_architecture"],
}

ENGINEERING_SKILLS = {
    "engineering.workflow_architecture": ["ms.skill.n8n_workflow_architecture"],
    "engineering.workflow_debugging": ["ms.skill.n8n_workflow_debugging"],
    "engineering.deployment_review": ["ms.skill.n8n_deployment_review"],
}

KNOWLEDGE_SKILLS = {
    "knowledge.knowledge_linking": ["ms.skill.knowledge_linking"],
}

DELIVERABLES_SKILLS = {
    "deliverables.presentation_architecture": ["ms.skill.presentation_architecture"],
    "deliverables.content_architecture": ["ms.skill.presentation_architecture"],
    "deliverables.visual_briefing": ["ms.skill.presentation_architecture"],
    "deliverables.chart_specification": ["ms.skill.presentation_architecture"],
    "deliverables.accessibility_review": ["ms.skill.presentation_architecture"],
}

DEFERRED_MARKETING = [
    "marketing.content_strategy",
    "marketing.copywriting",
    "marketing.launch_strategy",
    "marketing.distribution",
    "marketing.marketing_analytics",
    "marketing.learning_and_feedback",
]

DEFERRED_ENGINEERING = [
    "engineering.workflow_documentation",
    "engineering.provider_version_review",
]

DEFERRED_KNOWLEDGE = [
    "knowledge.knowledge_discovery",
]

DEFERRED_DELIVERABLES = [
    "deliverables.document_structure",
    "deliverables.renderer_handoff",
    "deliverables.publication_handoff",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def base_capability(
    cap_id: str,
    name: str,
    profession_ids: list[str],
    *,
    status: str = "implemented_non_executable",
    readiness: list[str] | None = None,
    required_skills: list[str] | None = None,
    optional_skills: list[str] | None = None,
    required_patterns: list[str] | None = None,
    optional_patterns: list[str] | None = None,
    required_connectors: list[str] | None = None,
    required_tools: list[str] | None = None,
    approval: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "capability_id": cap_id,
        "capability_name": name,
        "profession_ids": profession_ids,
        "objective": f"Deliver {name.lower()} outcomes with explicit evidence boundaries.",
        "business_outcomes": [f"Structured {name.lower()} output for human review."],
        "input_requirements": ["Governed upstream context where applicable."],
        "output_contract_summary": "Research or specification contract — non-executable.",
        "required_skill_ids": required_skills or [],
        "optional_skill_ids": optional_skills or [],
        "required_pattern_ids": required_patterns or [],
        "optional_pattern_ids": optional_patterns or [],
        "required_connector_classes": required_connectors or [],
        "required_tool_classes": required_tools or [],
        "dependency_capability_ids": [],
        "approval_requirements": approval or [],
        "evidence_requirements": ["provenance", "source_reference"],
        "tenant_requirements": ["tenant_scoped"],
        "implementation_status": status,
        "readiness": readiness
        or ["available_as_knowledge", "package_contract_ready", "runtime_not_available"],
        "limitations": limitations or ["Non-executable in KB-WPL-01.7 phase."],
        "runtime_authorized": False,
        "provenance": PROVENANCE,
    }


def build_capabilities() -> list[dict[str, Any]]:
    caps: list[dict[str, Any]] = []
    mkt_prof = ["profession.ai_marketing_director"]
    eng_prof = ["profession.automation_architect"]
    kn_prof = ["profession.knowledge_architect"]
    del_prof = ["profession.content_deliverables_architect"]

    for cap_id, skills in MARKETING_SKILLS.items():
        name = cap_id.split(".", 1)[1].replace("_", " ").title()
        limitations = None
        shared_refs: list[str] | None = None
        if cap_id == "marketing.positioning":
            limitations = [
                "Consumes CIM from customer_intelligence — does not replace JTBD/pain recompute.",
            ]
        if cap_id == "marketing.customer_intelligence":
            shared_refs = ["packages/knowledge/customer_intelligence/0.1.0"]
        cap = base_capability(
            cap_id,
            name,
            mkt_prof,
            required_skills=skills,
            limitations=limitations,
            readiness=[
                "available_as_knowledge",
                "package_contract_ready",
                "runtime_not_available",
            ],
        )
        if shared_refs:
            cap["shared_contract_references"] = shared_refs
        caps.append(cap)

    for cap_id in DEFERRED_MARKETING:
        name = cap_id.split(".", 1)[1].replace("_", " ").title()
        extra: dict[str, Any] = {}
        if cap_id == "marketing.distribution":
            extra = {
                "required_patterns": ["human_approval_before_publication", "publication_confirmation"],
                "required_connectors": ["publication_connector"],
                "required_tools": ["publish"],
                "approval": ["human_approval"],
                "readiness": [
                    "available_as_knowledge",
                    "connector_not_available",
                    "approval_boundary_missing",
                    "runtime_not_available",
                ],
            }
        if cap_id == "marketing.learning_and_feedback":
            extra = {
                "required_patterns": ["customer_feedback_to_learning_candidate"],
                "readiness": ["available_as_knowledge", "runtime_not_available", "deferred"],
            }
        caps.append(
            base_capability(
                cap_id,
                name,
                mkt_prof,
                status="deferred",
                readiness=extra.get("readiness", ["deferred", "runtime_not_available"]),
                required_patterns=extra.get("required_patterns"),
                required_connectors=extra.get("required_connectors"),
                required_tools=extra.get("required_tools"),
                approval=extra.get("approval"),
                limitations=["Future capability — explicit gap recorded."],
            )
        )

    for cap_id, skills in ENGINEERING_SKILLS.items():
        name = cap_id.split(".", 1)[1].replace("_", " ").title()
        caps.append(base_capability(cap_id, name, eng_prof, required_skills=skills))

    eng_extra = {
        "engineering.pattern_selection": base_capability(
            "engineering.pattern_selection",
            "Pattern Selection",
            eng_prof,
            required_patterns=list(PATTERN_CAPABILITY_MAP.keys()),
            readiness=["available_as_knowledge", "package_contract_ready", "runtime_not_available"],
        ),
        "engineering.workflow_backup": base_capability(
            "engineering.workflow_backup",
            "Workflow Backup",
            eng_prof,
            required_patterns=["workflow_backup"],
        ),
        "engineering.error_recovery": base_capability(
            "engineering.error_recovery",
            "Error Recovery",
            eng_prof,
            required_patterns=["error_workflow_or_recovery", "retry_with_idempotency", "checkpoint_and_resume"],
        ),
        "engineering.observability": base_capability(
            "engineering.observability",
            "Observability",
            eng_prof,
            required_patterns=["dead_letter_queue"],
        ),
        "engineering.connector_integration_design": base_capability(
            "engineering.connector_integration_design",
            "Connector Integration Design",
            eng_prof,
            required_patterns=["structured_LLM_to_API_request", "tool_workflow_separation"],
            required_connectors=["development_connector"],
        ),
        "engineering.runtime_safety": base_capability(
            "engineering.runtime_safety",
            "Runtime Safety",
            eng_prof,
            required_patterns=["supervisor_pattern", "retry_with_idempotency", "human_approval_before_publication"],
        ),
        "engineering.test_and_replay_design": base_capability(
            "engineering.test_and_replay_design",
            "Test And Replay Design",
            eng_prof,
            required_patterns=["checkpoint_and_resume"],
        ),
    }
    caps.extend(eng_extra.values())

    for cap_id in DEFERRED_ENGINEERING:
        name = cap_id.split(".", 1)[1].replace("_", " ").title()
        caps.append(
            base_capability(
                cap_id,
                name,
                eng_prof,
                status="deferred",
                readiness=["deferred", "runtime_not_available"],
            )
        )

    kn_caps = {
        "knowledge.knowledge_linking": base_capability(
            "knowledge.knowledge_linking",
            "Knowledge Linking",
            kn_prof,
            required_skills=["ms.skill.knowledge_linking"],
        ),
        "knowledge.lineage_integrity": base_capability(
            "knowledge.lineage_integrity",
            "Lineage Integrity",
            kn_prof,
            required_patterns=["source_lineage_preservation"],
        ),
        "knowledge.duplicate_detection": base_capability(
            "knowledge.duplicate_detection",
            "Duplicate Detection",
            kn_prof,
            required_skills=["ms.skill.knowledge_linking"],
        ),
        "knowledge.contradiction_detection": base_capability(
            "knowledge.contradiction_detection",
            "Contradiction Detection",
            kn_prof,
            required_skills=["ms.skill.knowledge_linking"],
        ),
        "knowledge.supersession_review": base_capability(
            "knowledge.supersession_review",
            "Supersession Review",
            kn_prof,
            required_skills=["ms.skill.knowledge_linking"],
        ),
        "knowledge.index_management": base_capability(
            "knowledge.index_management",
            "Index Management",
            kn_prof,
            required_skills=["ms.skill.knowledge_linking"],
        ),
        "knowledge.knowledge_quality": base_capability(
            "knowledge.knowledge_quality",
            "Knowledge Quality",
            kn_prof,
            required_patterns=["quality_gate_after_generation", "evidence_grounded_generation"],
        ),
        "knowledge.knowledge_candidate_review": base_capability(
            "knowledge.knowledge_candidate_review",
            "Knowledge Candidate Review",
            kn_prof,
            required_patterns=["customer_feedback_to_learning_candidate"],
            approval=["human_approval"],
        ),
        "knowledge.provenance_management": base_capability(
            "knowledge.provenance_management",
            "Provenance Management",
            kn_prof,
            required_patterns=["source_lineage_preservation"],
        ),
        "knowledge.source_ingestion": base_capability(
            "knowledge.source_ingestion",
            "Source Ingestion",
            kn_prof,
            status="deferred",
            readiness=["deferred", "runtime_not_available"],
        ),
    }
    caps.extend(kn_caps.values())
    caps.append(
        base_capability(
            "knowledge.knowledge_discovery",
            "Knowledge Discovery",
            kn_prof,
            status="deferred",
            readiness=["deferred", "runtime_not_available"],
            limitations=["Deferred to KB-WPL-01.8."],
        )
    )

    for cap_id, skills in DELIVERABLES_SKILLS.items():
        name = cap_id.split(".", 1)[1].replace("_", " ").title()
        patterns = []
        if cap_id == "deliverables.content_architecture":
            patterns = ["quality_gate_after_generation", "draft_to_human_approval"]
        if cap_id in {"deliverables.presentation_architecture", "deliverables.visual_briefing"}:
            patterns = ["source_lineage_preservation"]
        caps.append(
            base_capability(
                cap_id,
                name,
                del_prof,
                required_skills=skills,
                required_patterns=patterns or None,
            )
        )

    for cap_id in DEFERRED_DELIVERABLES:
        name = cap_id.split(".", 1)[1].replace("_", " ").title()
        extra: dict[str, Any] = {}
        if cap_id == "deliverables.publication_handoff":
            extra = {
                "required_patterns": ["human_approval_before_publication", "human_edit_then_resume"],
                "required_connectors": ["publication_connector"],
                "required_tools": ["publish"],
                "approval": ["human_approval"],
                "readiness": [
                    "connector_not_available",
                    "approval_boundary_missing",
                    "runtime_not_available",
                    "deferred",
                ],
            }
        if cap_id == "deliverables.renderer_handoff":
            extra = {
                "required_connectors": ["rendering_connector"],
                "required_tools": ["render"],
                "readiness": ["connector_not_available", "runtime_not_available", "deferred"],
            }
        caps.append(
            base_capability(
                cap_id,
                name,
                del_prof,
                status="deferred",
                required_patterns=extra.get("required_patterns"),
                required_connectors=extra.get("required_connectors"),
                required_tools=extra.get("required_tools"),
                approval=extra.get("approval"),
                readiness=extra.get("readiness", ["deferred", "runtime_not_available"]),
            )
        )

    caps.append(
        base_capability(
            "platform.professional_task_routing",
            "Professional Task Routing",
            mkt_prof + eng_prof,
            status="specified",
            readiness=["available_as_knowledge", "runtime_not_available"],
            required_patterns=["supervisor_pattern", "specialist_subworkflow"],
            limitations=["Conceptual routing contract only — not Discovery runtime."],
        )
    )
    return caps


def build_professions(capabilities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cap_by_prof: dict[str, list[str]] = {}
    for cap in capabilities:
        for pid in cap["profession_ids"]:
            cap_by_prof.setdefault(pid, []).append(cap["capability_id"])

    return [
        {
            "profession_id": "profession.ai_marketing_director",
            "profession_name": "AI Marketing Director",
            "domain": "marketing",
            "objective": "Route marketing work through governed capabilities and Skills.",
            "responsibilities": [
                "identify user intent",
                "determine required marketing capabilities",
                "route work through approved Skills",
                "preserve evidence and blockers",
                "stop unsafe or unsupported work",
                "request human decisions",
                "coordinate analysis before execution",
            ],
            "prohibited_responsibilities": [
                "execute external tools directly",
                "grant permissions",
                "activate Skills",
                "bypass Market Validation",
                "bypass Claim Substantiation",
                "ignore tenant boundaries",
                "approve spend",
                "approve publication",
                "rewrite Evidence as fact",
            ],
            "capability_ids": sorted(cap_by_prof["profession.ai_marketing_director"]),
            "governance_level": "human_accountable",
            "human_accountability_required": True,
            "runtime_authorized": False,
            "production_status": "mapped",
            "version": "0.1.0",
            "provenance": PROVENANCE,
        },
        {
            "profession_id": "profession.automation_architect",
            "profession_name": "Automation Architect",
            "domain": "automation_engineering",
            "objective": "Design and review workflow architecture without deployment.",
            "responsibilities": [
                "design workflow architecture",
                "diagnose workflow failures",
                "review deployment readiness",
                "select approved patterns",
                "define approval, idempotency and recovery boundaries",
                "document provider constraints",
                "prepare safe manual implementation plans",
            ],
            "prohibited_responsibilities": [
                "deploy",
                "activate",
                "access credentials",
                "mutate live workflows",
                "bypass deployment review",
                "execute imported JSON",
                "grant Connector permissions",
            ],
            "capability_ids": sorted(cap_by_prof["profession.automation_architect"]),
            "governance_level": "human_accountable",
            "human_accountability_required": True,
            "runtime_authorized": False,
            "production_status": "mapped",
            "version": "0.1.0",
            "provenance": PROVENANCE,
        },
        {
            "profession_id": "profession.knowledge_architect",
            "profession_name": "Knowledge Architect",
            "domain": "knowledge_management",
            "objective": "Maintain knowledge relationships and quality without auto-mutation.",
            "responsibilities": [
                "maintain knowledge relationships",
                "identify broken references",
                "detect duplicates and contradictions",
                "preserve version lineage",
                "recommend indexes",
                "prepare knowledge candidates for human review",
            ],
            "prohibited_responsibilities": [
                "mutate canonical Knowledge Core automatically",
                "merge records automatically",
                "delete history",
                "cross tenants",
                "select a truth winner automatically",
            ],
            "capability_ids": sorted(cap_by_prof["profession.knowledge_architect"]),
            "governance_level": "human_accountable",
            "human_accountability_required": True,
            "runtime_authorized": False,
            "production_status": "mapped",
            "version": "0.1.0",
            "provenance": PROVENANCE,
        },
        {
            "profession_id": "profession.content_deliverables_architect",
            "profession_name": "Content & Deliverables Architect",
            "domain": "content_and_deliverables",
            "objective": "Structure approved content into deliverable specifications.",
            "responsibilities": [
                "structure approved content into deliverables",
                "preserve claim/evidence integrity",
                "prepare provider-neutral output specifications",
                "define accessibility and review requirements",
            ],
            "prohibited_responsibilities": [
                "render final files",
                "publish without approval",
                "mutate source knowledge",
                "grant Connector permissions",
            ],
            "capability_ids": sorted(cap_by_prof["profession.content_deliverables_architect"]),
            "governance_level": "human_accountable",
            "human_accountability_required": True,
            "runtime_authorized": False,
            "production_status": "mapped",
            "version": "0.1.0",
            "provenance": PROVENANCE,
        },
    ]


def build_skill_bindings(capabilities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for cap in capabilities:
        cap_id = cap["capability_id"]
        for skill_id in cap.get("required_skill_ids") or []:
            bindings.append(
                {
                    "capability_id": cap_id,
                    "skill_id": skill_id,
                    "binding_type": "required",
                    "status": "bound",
                    "applicability": f"Primary methodology for {cap['capability_name']}.",
                    "limitations": ["Non-executable candidate package."],
                    "provenance": PROVENANCE,
                }
            )
    return bindings


def build_pattern_bindings() -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for pattern_id, cap_ids in PATTERN_CAPABILITY_MAP.items():
        for cap_id in cap_ids:
            bindings.append(
                {
                    "pattern_id": pattern_id,
                    "capability_id": cap_id,
                    "library_version": "0.1.0-frozen",
                    "applicability": f"Pattern informs {cap_id} architecture boundaries.",
                    "limitations": [
                        "Read-only reference — does not grant execution or tool permission.",
                        "runtime_authorized=false",
                    ],
                    "runtime_authorized": False,
                    "provenance": PROVENANCE,
                }
            )
    return bindings


def build_dependencies() -> list[dict[str, Any]]:
    deps: list[dict[str, Any]] = []

    def add(source: str, target: str, *, dep_type: str = "required", note: str = "") -> None:
        deps.append(
            {
                "source_capability_id": source,
                "target_capability_id": target,
                "dependency_type": dep_type,
                "relationship": "requires_upstream",
                "note": note,
                "provenance": PROVENANCE,
            }
        )

    marketing_chain = [
        "marketing.product_context",
        "marketing.market_research",
        "marketing.competitive_intelligence",
        "marketing.customer_intelligence",
        "marketing.market_validation",
        "marketing.positioning",
        "marketing.claim_substantiation",
        "marketing.offer_architecture",
        "marketing.launch_strategy",
    ]
    for left, right in zip(marketing_chain, marketing_chain[1:], strict=False):
        add(left, right)

    add("marketing.offer_architecture", "marketing.content_strategy", dep_type="optional")
    add("marketing.content_strategy", "marketing.copywriting", dep_type="optional")
    add("marketing.launch_strategy", "marketing.distribution", dep_type="optional")
    add("marketing.distribution", "marketing.marketing_analytics", dep_type="optional")
    add("marketing.marketing_analytics", "marketing.learning_and_feedback", dep_type="optional")
    add(
        "marketing.claim_substantiation",
        "marketing.distribution",
        note="Publication path requires substantiation upstream.",
    )

    add("engineering.workflow_architecture", "engineering.deployment_review")
    add("engineering.deployment_review", "engineering.workflow_debugging", dep_type="optional")

    add("knowledge.source_ingestion", "knowledge.provenance_management")
    add("knowledge.provenance_management", "knowledge.knowledge_linking")
    add("knowledge.knowledge_linking", "knowledge.duplicate_detection", dep_type="optional")
    add("knowledge.knowledge_linking", "knowledge.contradiction_detection", dep_type="optional")
    add("knowledge.knowledge_linking", "knowledge.knowledge_candidate_review")
    add(
        "knowledge.knowledge_candidate_review",
        "knowledge.knowledge_discovery",
        dep_type="optional",
        note="Future persistence deferred.",
    )
    return deps


def build_gaps(capabilities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    idx = 0
    for cap in capabilities:
        if cap["implementation_status"] != "deferred":
            continue
        idx += 1
        gap_type = "capability_not_released"
        missing_skills: list[str] = []
        missing_connectors = list(cap.get("required_connector_classes") or [])
        missing_tools = list(cap.get("required_tool_classes") or [])
        if missing_connectors:
            gap_type = "missing_connector"
        gaps.append(
            {
                "gap_id": f"gap-{idx:03d}",
                "profession_id": cap["profession_ids"][0],
                "capability_id": cap["capability_id"],
                "gap_type": gap_type,
                "missing_skill_ids": missing_skills,
                "missing_pattern_ids": [],
                "missing_connector_classes": missing_connectors,
                "missing_tool_classes": missing_tools,
                "missing_approval_boundary": bool(cap.get("approval_requirements")),
                "missing_evidence_boundary": False,
                "missing_runtime": True,
                "impact": "Capability specified but not yet implemented as executable contour.",
                "blocking": cap["capability_id"] in {
                    "marketing.distribution",
                    "deliverables.publication_handoff",
                },
                "remediation": "Implement in future phase with Connector and approval boundaries.",
                "owner_review_required": True,
                "provenance": PROVENANCE,
            }
        )
    gaps.append(
        {
            "gap_id": "gap-runtime-global",
            "profession_id": "profession.automation_architect",
            "capability_id": "engineering.deployment_review",
            "gap_type": "missing_runtime",
            "missing_skill_ids": [],
            "missing_pattern_ids": [],
            "missing_connector_classes": ["development_connector"],
            "missing_tool_classes": ["write", "administer"],
            "missing_approval_boundary": True,
            "missing_evidence_boundary": False,
            "missing_runtime": True,
            "impact": "Deployment activation remains blocked until Connector Gateway phase.",
            "blocking": True,
            "remediation": "KB-WPL-04 Controlled n8n Deployment Gateway.",
            "owner_review_required": True,
            "provenance": PROVENANCE,
        }
    )
    return gaps


def build_connector_bindings() -> list[dict[str, Any]]:
    rows = [
        ("human_approval_before_publication", "publication_connector", ["publish"]),
        ("structured_LLM_to_API_request", "development_connector", ["write", "generate_draft"]),
        ("evidence_grounded_generation", "content_generation_connector", ["generate_draft"]),
        ("publication_confirmation", "publication_connector", ["publish", "read"]),
        ("lead_capture_to_qualification", "CRM_connector", ["read", "write"]),
    ]
    bindings: list[dict[str, Any]] = []
    for pattern_id, connector_class, tool_classes in rows:
        bindings.append(
            {
                "pattern_id": pattern_id,
                "connector_class": connector_class,
                "conceptual_only": True,
                "activates_connector": False,
                "permission_granted": False,
                "required_tool_classes": tool_classes,
                "applicability": "Conceptual binding for future Connector Gateway.",
                "limitations": ["No Connector activation in KB-WPL-01.7."],
                "provenance": PROVENANCE,
            }
        )
    return bindings


def build_connector_tool_bindings() -> list[dict[str, Any]]:
    rules = [
        ("research_connector", "read", "no_side_effect"),
        ("research_connector", "search", "no_side_effect"),
        ("content_generation_connector", "generate_draft", "draft_not_publication"),
        ("rendering_connector", "render", "render_not_publication"),
        ("publication_connector", "publish", "requires_approval_and_evidence"),
        ("publication_connector", "write", "requires_approval"),
        ("storage_connector", "delete", "elevated_approval"),
        ("advertising_connector", "spend", "deny_by_default"),
    ]
    bindings: list[dict[str, Any]] = []
    for connector_class, tool_class, policy in rules:
        bindings.append(
            {
                "connector_class": connector_class,
                "tool_class": tool_class,
                "policy": policy,
                "conceptual_only": True,
                "allowlist_mutation": False,
                "permission_granted": False,
                "provenance": PROVENANCE,
            }
        )
    return bindings


def write_schemas() -> None:
    SCHEMAS.mkdir(parents=True, exist_ok=True)
    common = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": True,
    }
    schema_defs = {
        "provenance.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/provenance.schema.json",
            "required": ["origin", "phase"],
        },
        "profession.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/profession.schema.json",
            "required": [
                "profession_id",
                "profession_name",
                "domain",
                "capability_ids",
                "runtime_authorized",
                "production_status",
                "version",
                "provenance",
            ],
        },
        "capability.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/capability.schema.json",
            "required": [
                "capability_id",
                "capability_name",
                "profession_ids",
                "implementation_status",
                "readiness",
                "provenance",
            ],
        },
        "capability-dependency.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/capability-dependency.schema.json",
            "required": ["source_capability_id", "target_capability_id", "dependency_type", "provenance"],
        },
        "profession-capability-binding.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/profession-capability-binding.schema.json",
            "required": ["profession_id", "capability_id", "provenance"],
        },
        "capability-skill-binding.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/capability-skill-binding.schema.json",
            "required": ["capability_id", "skill_id", "binding_type", "status", "provenance"],
        },
        "skill-pattern-binding.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/skill-pattern-binding.schema.json",
            "required": ["pattern_id", "capability_id", "runtime_authorized", "provenance"],
        },
        "pattern-connector-binding.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/pattern-connector-binding.schema.json",
            "required": ["pattern_id", "connector_class", "conceptual_only", "provenance"],
        },
        "connector-tool-binding.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/connector-tool-binding.schema.json",
            "required": ["connector_class", "tool_class", "conceptual_only", "provenance"],
        },
        "capability-readiness.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/capability-readiness.schema.json",
            "required": ["capability_id", "readiness_findings"],
        },
        "capability-gap.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/capability-gap.schema.json",
            "required": ["gap_id", "capability_id", "gap_type", "impact", "provenance"],
        },
        "professional-task-route.schema.json": {
            **common,
            "$id": "https://schemas.marketsynth.ai/capability-model/0.1.0/professional-task-route.schema.json",
            "required": ["route_id", "task_summary", "runtime_authorized", "provenance"],
        },
    }
    for name, schema in schema_defs.items():
        write_json(SCHEMAS / name, schema)


def main() -> None:
    write_schemas()
    capabilities = build_capabilities()
    professions = build_professions(capabilities)
    profession_bindings = [
        {"profession_id": p["profession_id"], "capability_id": c, "provenance": PROVENANCE}
        for p in professions
        for c in p["capability_ids"]
    ]
    write_json(BUNDLE / "professions.json", professions)
    write_json(BUNDLE / "capabilities.json", capabilities)
    write_json(BUNDLE / "profession_capability_bindings.json", profession_bindings)
    write_json(BUNDLE / "capability_skill_bindings.json", build_skill_bindings(capabilities))
    write_json(BUNDLE / "skill_pattern_bindings.json", build_pattern_bindings())
    write_json(BUNDLE / "pattern_connector_bindings.json", build_connector_bindings())
    write_json(BUNDLE / "connector_tool_bindings.json", build_connector_tool_bindings())
    write_json(BUNDLE / "capability_dependencies.json", build_dependencies())
    write_json(BUNDLE / "capability_gaps.json", build_gaps(capabilities))

    schema_hashes = {p.name: sha256_file(p) for p in sorted(SCHEMAS.glob("*.json"))}
    data_files = [
        "professions.json",
        "capabilities.json",
        "profession_capability_bindings.json",
        "capability_skill_bindings.json",
        "skill_pattern_bindings.json",
        "pattern_connector_bindings.json",
        "connector_tool_bindings.json",
        "capability_dependencies.json",
        "capability_gaps.json",
    ]
    data_hashes = {name: sha256_file(BUNDLE / name) for name in data_files}
    file_hashes = {**schema_hashes, **data_hashes}
    bundle_hash = hashlib.sha256(
        json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    semantic_hash = hashlib.sha256(
        json.dumps(data_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    write_json(
        BUNDLE / "freeze_manifest.json",
        {
            "schema_version": "0.1.0",
            "canonical_uri_base": "https://schemas.marketsynth.ai/capability-model/0.1.0/",
            "bundle_status": "mapped_read_only_model",
            "owner_decision": "accepted_as_architectural_mapping",
            "runtime_authorized": False,
            "production_eligible": False,
            "profession_count": len(professions),
            "capability_count": len(capabilities),
            "pattern_binding_count": len(PATTERN_CAPABILITY_MAP),
            "file_hashes": file_hashes,
            "bundle_hash": bundle_hash,
            "semantic_bundle_hash": semantic_hash,
            "generated_at": "2026-07-24T00:00:00Z",
        },
    )
    readme = (
        "# Capability Model v0.1.0\n\n"
        "Read-only Profession → Capability → Skill → Pattern → Connector → Tool mapping.\n\n"
        f"- bundle_hash: `{bundle_hash}`\n"
        f"- semantic_bundle_hash: `{semantic_hash}`\n"
        "- status: mapped_read_only_model\n"
    )
    (BUNDLE / "README.md").write_text(readme, encoding="utf-8")
    print(f"bundle_hash={bundle_hash}")
    print(f"semantic_bundle_hash={semantic_hash}")
    print(f"professions={len(professions)} capabilities={len(capabilities)}")


if __name__ == "__main__":
    main()
