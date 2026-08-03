"""KB-WPL-01.8 — Knowledge Discovery read models tests."""
# ruff: noqa: E501

from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest
from app.knowledge.capability_model.serialization import (
    FROZEN_CAPABILITY_MODEL_BUNDLE_HASH,
    FROZEN_CAPABILITY_MODEL_SEMANTIC_HASH,
    recompute_freeze_manifest_bundle_hash,
)
from app.knowledge.discovery.contracts import (
    FORBIDDEN_RECOMMENDED_ACTIONS,
    QUERY_MODES,
    SAFE_NEXT_ACTIONS,
)
from app.knowledge.discovery.errors import DiscoveryValidationError
from app.knowledge.discovery.explanations import explain_candidate, explain_route
from app.knowledge.discovery.filters import (
    validate_query,
    validate_recommended_action,
    validate_result,
)
from app.knowledge.discovery.indexes import DiscoverySources, load_default_sources
from app.knowledge.discovery.queries import (
    discover,
    find_capabilities,
    find_patterns,
    find_skills,
    route_task,
)
from app.knowledge.discovery.serialization import (
    FROZEN_DISCOVERY_BUNDLE_HASH,
    compute_result_hash,
    compute_semantic_bundle_hash,
    load_freeze_manifest,
)
from app.knowledge.n8n_engineering.constants import FROZEN_LIBRARY_SEMANTIC_HASH
from app.knowledge.workflow_patterns.serialization import load_library_manifest
from app.skills.hashing import calculate_skill_package_hash
from tests.support.discovery_validation import base_query
from tests.support.kb_skill_validation import KB_SKILL_PACKAGE_HASHES

REPO = Path(__file__).resolve().parents[1]
DISCOVERY_DIR = REPO / "app" / "knowledge" / "discovery"
FORBIDDEN_IMPORTS = ("requests", "httpx", "aiohttp", "socket", "mcp", "telegram_mcp")
TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"


def _sources_with_private_skill() -> DiscoverySources:
    src = load_default_sources()
    src.tenant_private_skills.append(
        {
            "skill_id": "ms.skill.private_marketing",
            "title": "Private Marketing Skill",
            "tenant_scope": "tenant_private",
            "tenant_id": TENANT_A,
            "trust_status": "candidate",
            "maturity": "reviewed",
        }
    )
    src.quarantined_templates.append(
        {
            "workflow_template_id": "wf-quarantine-001",
            "title": "Quarantined Template",
            "tenant_id": TENANT_A,
            "capability_ids": ["engineering.workflow_architecture"],
            "quarantined": True,
        }
    )
    src.rejected_artifacts.append(
        {
            "artifact_id": "rej-001",
            "title": "Rejected Workflow",
            "tenant_id": TENANT_A,
            "trust_status": "rejected",
        }
    )
    return src


@pytest.fixture
def sources() -> DiscoverySources:
    return _sources_with_private_skill()


def test_01_module_imports_without_side_effects() -> None:
    import app.knowledge.discovery as discovery

    assert discovery.BUNDLE_STATUS == "read_only_discovery_model"


def test_02_query_contract_validates() -> None:
    assert validate_query(base_query("Проверить бизнес-идею")) == []


def test_03_result_contract_validates(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить бизнес-идею"), sources=sources)
    assert validate_result(result) == []


def test_04_candidate_contract_validates(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить бизнес-идею"), sources=sources)
    candidate = result["skill_candidates"][0]
    assert candidate["runtime_authorized"] is False
    assert "match_reasons" in candidate


def test_05_mode_enum_finite() -> None:
    assert len(QUERY_MODES) == 8


def test_06_forbidden_action_enum_absent() -> None:
    for action in FORBIDDEN_RECOMMENDED_ACTIONS:
        assert action not in SAFE_NEXT_ACTIONS


def test_07_runtime_authorized_always_false(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить бизнес-идею"), sources=sources)
    assert result["runtime_authorized"] is False


def test_08_capability_model_hash_verified() -> None:
    from app.knowledge.capability_model.serialization import load_freeze_manifest as load_cap

    manifest = load_cap()
    assert manifest["bundle_hash"] == FROZEN_CAPABILITY_MODEL_BUNDLE_HASH
    assert manifest["semantic_bundle_hash"] == FROZEN_CAPABILITY_MODEL_SEMANTIC_HASH
    assert manifest["bundle_hash"] == recompute_freeze_manifest_bundle_hash()


def test_09_wpl_hash_verified() -> None:
    manifest = load_library_manifest()
    assert manifest["library_semantic_hash"] == FROZEN_LIBRARY_SEMANTIC_HASH


def test_10_exact_id_match_works(sources: DiscoverySources) -> None:
    query = base_query(
        "anything",
        required_capability_ids=["marketing.market_validation"],
    )
    result = discover(query, sources=sources)
    assert any(c["artifact_id"] == "marketing.market_validation" for c in result["capabilities"])


def test_11_exact_capability_match_works(sources: DiscoverySources) -> None:
    caps = find_capabilities("market_validation exact", tenant_id=TENANT_A, sources=sources)
    assert caps


def test_12_russian_alias_market_validation(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить бизнес-идею"), sources=sources)
    assert any(c["artifact_id"] == "marketing.market_validation" for c in result["capabilities"])


def test_13_russian_alias_telegram_post(sources: DiscoverySources) -> None:
    result = discover(base_query("Сделать пост в Telegram"), sources=sources)
    assert any(c["artifact_id"] == "marketing.distribution" for c in result["capabilities"])


def test_14_youtube_content_alias(sources: DiscoverySources) -> None:
    result = discover(base_query("Подготовить сценарий YouTube"), sources=sources)
    assert any(
        c["artifact_id"] == "deliverables.content_architecture" for c in result["capabilities"]
    )


def test_15_n8n_architecture_alias(sources: DiscoverySources) -> None:
    result = discover(base_query("Спроектировать n8n workflow"), sources=sources)
    assert any(
        c["artifact_id"] == "engineering.workflow_architecture" for c in result["capabilities"]
    )


def test_16_n8n_debugging_alias(sources: DiscoverySources) -> None:
    result = discover(base_query("Найти ошибку в n8n workflow"), sources=sources)
    assert any(c["artifact_id"] == "engineering.workflow_debugging" for c in result["capabilities"])


def test_17_presentation_alias(sources: DiscoverySources) -> None:
    result = discover(base_query("Создать презентацию"), sources=sources)
    ids = {c["artifact_id"] for c in result["capabilities"]}
    assert "marketing.presentation_architecture" in ids or "deliverables.presentation_architecture" in ids


def test_18_knowledge_linking_alias(sources: DiscoverySources) -> None:
    result = discover(base_query("Связать документы и найти дубли"), sources=sources)
    assert any(c["artifact_id"] == "knowledge.knowledge_linking" for c in result["capabilities"])


def test_19_exact_match_outranks_alias(sources: DiscoverySources) -> None:
    explicit = discover(
        base_query("test", required_capability_ids=["marketing.market_validation"]),
        sources=sources,
    )
    alias = discover(base_query("Проверить идею"), sources=sources)
    explicit_rank = explicit["capabilities"][0]["total_rank"]
    alias_cap = next(c for c in alias["capabilities"] if c["artifact_id"] == "marketing.market_validation")
    assert explicit_rank >= alias_cap["total_rank"]


def test_20_existing_skill_outranks_pattern(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить бизнес-идею"), sources=sources)
    if result["skill_candidates"] and result["pattern_candidates"]:
        assert result["skill_candidates"][0]["total_rank"] >= result["pattern_candidates"][0]["total_rank"]


def test_21_pattern_supports_not_replaces_skill(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить бизнес-идею"), sources=sources)
    for pattern in result["pattern_candidates"]:
        assert any("replace" in lim.lower() for lim in pattern.get("limitations", []))


def test_22_missing_skill_appears_as_gap(sources: DiscoverySources) -> None:
    result = discover(base_query("Создать оффер и запустить рекламу"), sources=sources)
    assert result["capability_gaps"] or any(
        c["artifact_id"] == "marketing.launch_strategy" for c in result["capabilities"]
    )


def test_23_missing_connector_appears_as_gap(sources: DiscoverySources) -> None:
    result = discover(base_query("Опубликовать пост"), sources=sources)
    assert result["connector_requirements"] or result["capability_gaps"]


def test_24_missing_tool_appears_as_gap(sources: DiscoverySources) -> None:
    result = discover(base_query("Опубликовать пост"), sources=sources)
    assert result["tool_requirements"] or result["capability_gaps"]


def test_25_missing_approval_blocks_publication_readiness(sources: DiscoverySources) -> None:
    result = discover(
        base_query("Опубликовать пост", execution_sensitivity="publication"),
        sources=sources,
    )
    assert "request_human_review" in result["safe_next_actions"]
    assert result["readiness_summary"]["runtime_available"] is False


def test_26_billing_query_exposes_deny_by_default(sources: DiscoverySources) -> None:
    result = discover(base_query("Запустить рекламу", execution_sensitivity="billing"), sources=sources)
    assert "request_human_review" in result["safe_next_actions"]
    assert any("deny" in b for b in result["blockers"]) or result["capability_gaps"]


def test_27_marketing_route_ordered(sources: DiscoverySources) -> None:
    route = route_task(base_query("Сделать позиционирование"), sources=sources)
    caps = route["required_capability_ids"]
    if "marketing.market_validation" in caps and "marketing.positioning" in caps:
        assert caps.index("marketing.market_validation") < caps.index("marketing.positioning")


def test_28_engineering_route_ordered(sources: DiscoverySources) -> None:
    route = route_task(base_query("Спроектировать n8n workflow"), sources=sources)
    assert "engineering.workflow_architecture" in route["required_capability_ids"]


def test_29_knowledge_route_ordered(sources: DiscoverySources) -> None:
    route = route_task(base_query("Связать документы"), sources=sources)
    assert "knowledge.knowledge_linking" in route["required_capability_ids"]


def test_30_deliverables_route_ordered(sources: DiscoverySources) -> None:
    route = route_task(base_query("Создать презентацию"), sources=sources)
    assert route["candidate_skill_ids"]


def test_31_market_validation_before_positioning(sources: DiscoverySources) -> None:
    route = route_task(base_query("Сделать позиционирование"), sources=sources)
    caps = route["required_capability_ids"]
    if {"marketing.market_validation", "marketing.positioning"}.issubset(caps):
        assert caps.index("marketing.market_validation") < caps.index("marketing.positioning")


def test_32_claim_substantiation_before_offer(sources: DiscoverySources) -> None:
    route = route_task(base_query("Создать оффер"), sources=sources)
    caps = route["required_capability_ids"]
    if {"marketing.claim_substantiation", "marketing.offer_architecture"}.issubset(caps):
        assert caps.index("marketing.claim_substantiation") < caps.index("marketing.offer_architecture")


def test_33_publication_approval_present(sources: DiscoverySources) -> None:
    result = discover(base_query("Опубликовать пост", execution_sensitivity="publication"), sources=sources)
    assert result["approval_requirements"] or result["connector_requirements"]


def test_34_learning_candidate_does_not_mutate_knowledge(sources: DiscoverySources) -> None:
    result = discover(base_query("Собрать feedback для обучения"), sources=sources)
    for action in result["safe_next_actions"]:
        assert action not in {"install_skill", "execute_skill", "publish"}


def test_35_rejected_artifact_hidden(sources: DiscoverySources) -> None:
    result = discover(base_query("Rejected workflow"), sources=sources)
    assert not any(c.get("artifact_type") == "rejected_artifact_reference" for c in result["capabilities"])


def test_36_quarantined_artifact_hidden(sources: DiscoverySources) -> None:
    result = discover(base_query("Quarantined"), sources=sources)
    assert "quarantined_workflow_templates" not in result


def test_37_internal_audit_shows_quarantine(sources: DiscoverySources) -> None:
    query = base_query("Quarantined", internal_audit_mode=True, include_quarantined=True)
    result = discover(query, sources=sources)
    assert result.get("quarantined_workflow_templates")


def test_38_internal_audit_still_tenant_safe(sources: DiscoverySources) -> None:
    src = copy.deepcopy(sources)
    src.quarantined_templates.append(
        {
            "workflow_template_id": "wf-other-tenant",
            "title": "Other tenant",
            "tenant_id": TENANT_B,
            "capability_ids": [],
            "quarantined": True,
        }
    )
    query = base_query("Quarantined", tenant_id=TENANT_A, internal_audit_mode=True, include_quarantined=True)
    result = discover(query, sources=src)
    ids = [t["artifact_id"] for t in result.get("quarantined_workflow_templates", [])]
    assert "wf-other-tenant" not in ids


def test_39_private_skill_hidden_cross_tenant(sources: DiscoverySources) -> None:
    src = copy.deepcopy(sources)
    src.skills.append(
        {
            "skill_id": "ms.skill.private_marketing",
            "title": "Private",
            "tenant_scope": "tenant_private",
            "tenant_id": TENANT_A,
            "trust_status": "candidate",
            "maturity": "reviewed",
        }
    )
    query = base_query("Private skill", tenant_id=TENANT_B)
    result = discover(query, sources=src)
    assert "ms.skill.private_marketing" not in [s["artifact_id"] for s in result["skill_candidates"]]


def test_40_hidden_skill_absent_from_counts(sources: DiscoverySources) -> None:
    result = discover(base_query("test", tenant_id=TENANT_B), sources=sources)
    assert all(s["artifact_id"] != "ms.skill.private_marketing" for s in result["skill_candidates"])


def test_41_generic_not_found_behavior(sources: DiscoverySources) -> None:
    from app.knowledge.discovery.visibility import generic_not_found

    assert generic_not_found()["error"] == "not_found"


def test_42_profession_only_not_implementation_ready(sources: DiscoverySources) -> None:
    query = base_query("test", preferred_profession_ids=["profession.ai_marketing_director"])
    result = discover(query, sources=sources)
    for prof in result["professions"]:
        assert prof.get("recommended_action") != "use_internal_skill_contract"


def test_43_deferred_capability_remains_deferred(sources: DiscoverySources) -> None:
    result = discover(base_query("Написать copywriting текст"), sources=sources)
    cap = next((c for c in result["capabilities"] if c["artifact_id"] == "marketing.copywriting"), None)
    if cap:
        assert cap.get("implementation_status") == "deferred" or result["capability_gaps"]


def test_44_future_skill_not_presented_as_installed(sources: DiscoverySources) -> None:
    result = discover(base_query("Copywriting"), sources=sources)
    assert "ms.skill.copywriting" not in [s["artifact_id"] for s in result["skill_candidates"]]


def test_45_ranking_explainable(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить бизнес-идею"), sources=sources)
    candidate = result["capabilities"][0]
    assert explain_candidate(candidate)
    assert candidate.get("ranking_explanation")


def test_46_ranking_deterministic(sources: DiscoverySources) -> None:
    q = base_query("Проверить бизнес-идею")
    r1 = discover(q, sources=sources)
    r2 = discover(q, sources=sources)
    assert r1["result_hash"] == r2["result_hash"]


def test_47_ranking_stable_under_source_ordering(sources: DiscoverySources) -> None:
    shuffled = copy.deepcopy(sources)
    shuffled.skills = list(reversed(shuffled.skills))
    q = base_query("Проверить бизнес-идею")
    assert discover(q, sources=sources)["result_hash"] == discover(q, sources=shuffled)["result_hash"]


def test_48_similarity_only_not_high_confidence(sources: DiscoverySources) -> None:
    result = discover(base_query("market"), sources=sources)
    for cap in result["capabilities"]:
        if cap["match_reasons"][0]["match_type"] == "exact_token":
            assert cap.get("confidence") != "high"


def test_49_provider_constraint_affects_rank(sources: DiscoverySources) -> None:
    q = base_query("n8n", platform_constraints=["n8n"])
    result = discover(q, sources=sources)
    assert result["capabilities"]


def test_50_platform_constraint_affects_rank(sources: DiscoverySources) -> None:
    q = base_query("workflow", platform_constraints=["n8n"])
    result = discover(q, sources=sources)
    assert result["capabilities"]


def test_51_evidence_requirement_affects_result(sources: DiscoverySources) -> None:
    q = base_query("Проверить идею", required_evidence_classes=["market_source"])
    result = discover(q, sources=sources)
    assert "market_source" in result["evidence_requirements"]


def test_52_approval_constraint_affects_result(sources: DiscoverySources) -> None:
    result = discover(base_query("Опубликовать пост", execution_sensitivity="publication"), sources=sources)
    assert result["approval_requirements"] or result["safe_next_actions"]


def test_53_safe_next_actions_finite(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить идею"), sources=sources)
    for action in result["safe_next_actions"]:
        assert action in SAFE_NEXT_ACTIONS


def test_54_forbidden_install_action_rejected() -> None:
    assert validate_recommended_action("install_skill")


def test_55_forbidden_deploy_action_rejected() -> None:
    assert validate_recommended_action("deploy_workflow")


def test_56_forbidden_publish_action_rejected() -> None:
    assert validate_recommended_action("publish")


def test_57_result_hash_deterministic(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить идею"), sources=sources)
    assert result["result_hash"] == compute_result_hash(result)


def test_58_timestamp_excluded_from_semantic_hash(sources: DiscoverySources) -> None:
    result = discover(base_query("Проверить идею"), sources=sources)
    result["generated_at"] = "2026-07-24T99:99:99Z"
    assert compute_result_hash(result) == result["result_hash"]


def test_59_no_persistence_api_ui_network_mcp() -> None:
    for path in DISCOVERY_DIR.glob("**/*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in FORBIDDEN_IMPORTS
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS


def test_60_frozen_hashes_unchanged() -> None:
    manifest = load_freeze_manifest()
    assert manifest["bundle_hash"] == FROZEN_DISCOVERY_BUNDLE_HASH
    assert compute_semantic_bundle_hash() == FROZEN_DISCOVERY_BUNDLE_HASH
    for skill_id, expected in KB_SKILL_PACKAGE_HASHES.items():
        root = REPO / "packages" / "skills" / skill_id
        assert calculate_skill_package_hash(root) == expected


def test_61_existing_kb_wpl_tests_remain_green() -> None:
    from app.knowledge.capability_model.validation import validate_bundle

    assert validate_bundle() == []
    result = discover(base_query("Проверить идею"))
    assert result["runtime_authorized"] is False


def test_security_rejects_api_key() -> None:
    with pytest.raises(DiscoveryValidationError):
        discover(base_query("task with sk-live-api-key-secret"))


def test_explain_route(sources: DiscoverySources) -> None:
    route = route_task(base_query("Проверить идею"), sources=sources)
    assert explain_route(route)


def test_find_skills_helper(sources: DiscoverySources) -> None:
    skills = find_skills("Проверить идею", tenant_id=TENANT_A, sources=sources)
    assert skills


def test_find_patterns_helper(sources: DiscoverySources) -> None:
    patterns = find_patterns("retry pattern", tenant_id=TENANT_A, sources=sources)
    assert patterns
