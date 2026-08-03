"""Phase H2.1–H2.2 — Knowledge Inventory + Specialist Skill Registry."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.knowledge_foundation.admission import can_admit_to_production, required_metadata_fields
from app.knowledge_foundation.allowlists import (
    contains_forbidden_secret_markers,
    is_path_allowlisted,
    is_path_blocked,
)
from app.knowledge_foundation.inventory import (
    filter_inventory,
    get_inventory_item,
    list_inventory,
    reset_inventory_cache_for_tests,
)
from app.knowledge_foundation.migration_manifest import FIRST_APPROVED_PACK_IDS, list_manifest
from app.knowledge_foundation.retrieval_policy import retrieve_for_skill
from app.knowledge_foundation.scopes import assert_retrieval_allowed, is_cross_tenant_denied
from app.knowledge_foundation.scopes import KnowledgeScopeError
from app.knowledge_foundation.storage_decision import (
    BULK_REPO_INGESTION_ENABLED,
    EMBEDDINGS_ENABLED,
    SELECTED_STORAGE_OPTION,
)
from app.schemas.contracts import (
    KnowledgeInventoryFilter,
    KnowledgeItemStatus,
    KnowledgeStorageOption,
    KnowledgeType,
    SpecialistSkillCode,
    SpecialistSkillExecutionPolicy,
    SpecialistSkillStatus,
    UserRequestRouteCategory,
)
from app.specialist_skills.capability_packs import (
    get_capability_pack,
    skill_allowed_for_specialist,
)
from app.specialist_skills.clarifications import evaluate_clarification
from app.specialist_skills.registry import get_skill, list_skills
from app.specialist_skills.route_mapping import (
    map_route_to_skill,
    resolve_skill_for_user_request_category,
)


@pytest.fixture(autouse=True)
def _reset_inventory() -> None:
    reset_inventory_cache_for_tests()
    yield
    reset_inventory_cache_for_tests()


OWNER_A = UUID("00000000-0000-4000-8000-000000000001")
OWNER_B = UUID("00000000-0000-4000-8000-000000000002")
PROJECT_A = UUID("00000000-0000-4000-8000-0000000000aa")
PROJECT_B = UUID("00000000-0000-4000-8000-0000000000bb")


def test_skill_versions_and_draft_only() -> None:
    skills = list_skills()
    assert len(skills) == 14
    for skill in skills:
        assert skill.version == "1.0"
        assert skill.status == SpecialistSkillStatus.DRAFT
        assert skill.execution_policy == SpecialistSkillExecutionPolicy.DRAFT_ONLY
        assert skill.clarification_schema
        assert get_skill(skill.code) is not None


def test_capability_pack_allowlists() -> None:
    content = get_capability_pack("content_specialist")
    assert content is not None
    assert SpecialistSkillCode.CONTENT_TELEGRAM_POST in content.allowed_skills
    assert SpecialistSkillCode.PROGRAMMER_TELEGRAM_BOT_SPEC not in content.allowed_skills
    assert "shell" in content.forbidden_tools
    assert skill_allowed_for_specialist(
        "content_specialist", SpecialistSkillCode.CONTENT_TELEGRAM_POST
    )
    assert not skill_allowed_for_specialist(
        "content_specialist", SpecialistSkillCode.RESEARCH_MARKET_OVERVIEW
    )
    programmer = get_capability_pack("programmer")
    assert programmer is not None
    assert "deploy" in programmer.forbidden_tools
    assert "git_mutate" in programmer.forbidden_tools


def test_route_to_correct_skill() -> None:
    assert (
        resolve_skill_for_user_request_category(UserRequestRouteCategory.CONTENT)
        == SpecialistSkillCode.CONTENT_TELEGRAM_POST
    )
    assert (
        resolve_skill_for_user_request_category(UserRequestRouteCategory.TELEGRAM_BOT)
        == SpecialistSkillCode.PROGRAMMER_TELEGRAM_BOT_SPEC
    )
    assert (
        resolve_skill_for_user_request_category(UserRequestRouteCategory.MARKET_RESEARCH)
        == SpecialistSkillCode.RESEARCH_MARKET_OVERVIEW
    )
    assert (
        resolve_skill_for_user_request_category(UserRequestRouteCategory.COMPETITOR_ANALYSIS)
        == SpecialistSkillCode.RESEARCH_COMPETITOR_ANALYSIS
    )
    assert (
        resolve_skill_for_user_request_category(UserRequestRouteCategory.CONTENT_PLAN)
        == SpecialistSkillCode.CONTENT_CONTENT_PLAN
    )
    idea = map_route_to_skill(UserRequestRouteCategory.IDEA_VALIDATION)
    assert idea.uses_existing_project_path is True
    assert idea.skill_code is None
    strategy = map_route_to_skill(UserRequestRouteCategory.MARKETING_STRATEGY)
    assert strategy.domain_eligibility_required is True
    assert strategy.skill_code == SpecialistSkillCode.STRATEGY_POSITIONING


def test_missing_input_requires_clarification() -> None:
    result = evaluate_clarification(SpecialistSkillCode.CONTENT_TELEGRAM_POST, {})
    assert result.ready is False
    assert "topic" in result.missing_fields
    assert "audience" in result.missing_fields
    assert result.clarification_prompt

    filled = evaluate_clarification(
        SpecialistSkillCode.CONTENT_TELEGRAM_POST,
        {
            "platform": "telegram",
            "topic": "бурение",
            "audience": "B2B",
            "objective": "лиды",
            "tone": "деловой",
            "length": "короткий",
            "CTA": "написать в бот",
            "brand_constraints": "без кликбейта",
        },
    )
    assert filled.ready is True
    assert filled.missing_fields == []


def test_programmer_clarification_contract() -> None:
    result = evaluate_clarification(SpecialistSkillCode.PROGRAMMER_TELEGRAM_BOT_SPEC, {"users": "клиенты"})
    assert result.ready is False
    assert "business_purpose" in result.missing_fields


def test_forbidden_skill_not_available_to_specialist() -> None:
    assert not skill_allowed_for_specialist(
        "programmer", SpecialistSkillCode.CONTENT_TELEGRAM_POST
    )
    assert not skill_allowed_for_specialist(
        "researcher", SpecialistSkillCode.STRATEGY_POSITIONING
    )


def test_scopes_global_owner_project() -> None:
    project_item = get_inventory_item("kn.proj.demo_brief")
    assert project_item is not None
    assert is_cross_tenant_denied(
        project_item, requester_owner_id=OWNER_B, requester_project_id=PROJECT_A
    )
    assert is_cross_tenant_denied(
        project_item, requester_owner_id=OWNER_A, requester_project_id=PROJECT_B
    )
    assert not is_cross_tenant_denied(
        project_item, requester_owner_id=OWNER_A, requester_project_id=PROJECT_A
    )
    with pytest.raises(KnowledgeScopeError):
        assert_retrieval_allowed(
            project_item, requester_owner_id=OWNER_B, requester_project_id=PROJECT_A
        )


def test_cross_owner_retrieval_denied_in_retrieve() -> None:
    hits_a = retrieve_for_skill(
        SpecialistSkillCode.CONTENT_TELEGRAM_POST,
        requester_owner_id=OWNER_A,
        requester_project_id=PROJECT_A,
    )
    ids_a = {h.knowledge_id for h in hits_a}
    assert "kn.proj.demo_brief" in ids_a
    assert "kn.ex.owner_brand_demo" in ids_a

    hits_b = retrieve_for_skill(
        SpecialistSkillCode.CONTENT_TELEGRAM_POST,
        requester_owner_id=OWNER_B,
        requester_project_id=PROJECT_B,
    )
    ids_b = {h.knowledge_id for h in hits_b}
    assert "kn.proj.demo_brief" not in ids_b
    assert "kn.ex.owner_brand_demo" not in ids_b


def test_superseded_and_rejected_excluded() -> None:
    hits = retrieve_for_skill(
        SpecialistSkillCode.RESEARCH_MARKET_OVERVIEW,
        requester_owner_id=OWNER_A,
    )
    ids = {h.knowledge_id for h in hits}
    assert "kn.super.research_v1" not in ids
    assert "kn.obs.legacy_botfazer_readme" not in ids
    assert "kn.forb.workflows_raw" not in ids
    assert "kn.forb.secrets_env" not in ids
    assert "kn.hist.phase_ai_39_audit" not in ids
    assert "kn.meth.research_overview" in ids


def test_obsolete_botfazer_and_secrets_excluded() -> None:
    assert is_path_blocked("docs/phase_ai_39_marketing_pipeline_readiness_audit.md")
    assert is_path_blocked("workflows/raw/")
    assert is_path_blocked(".env")
    assert not is_path_allowlisted("docs/phase_ai_39_marketing_pipeline_readiness_audit.md")
    assert contains_forbidden_secret_markers("api_key=sk-test")
    rejected = get_inventory_item("kn.obs.legacy_botfazer_readme")
    assert rejected is not None
    assert rejected.knowledge_type == KnowledgeType.OBSOLETE
    assert not can_admit_to_production(rejected)


def test_citations_retained_on_research_hits() -> None:
    hits = retrieve_for_skill(
        SpecialistSkillCode.RESEARCH_COMPETITOR_ANALYSIS,
        requester_owner_id=OWNER_A,
        requester_project_id=PROJECT_A,
    )
    research = [h for h in hits if h.knowledge_id.startswith("kn.meth.research")]
    assert research
    assert all(h.citation_required for h in research)
    assert all(h.version and h.source_uri and h.authority for h in hits)


def test_storage_option_no_embeddings_no_bulk() -> None:
    assert SELECTED_STORAGE_OPTION == KnowledgeStorageOption.POSTGRES_FTS
    assert EMBEDDINGS_ENABLED is False
    assert BULK_REPO_INGESTION_ENABLED is False


def test_russian_and_english_knowledge_metadata() -> None:
    locales = {item.locale for item in list_inventory()}
    assert "ru" in locales
    assert "en" in locales
    ru = filter_inventory(KnowledgeInventoryFilter(locale="ru"))
    assert any(item.id == "kn.const.ru_invariants" for item in ru)


def test_first_approved_pack_and_manifest() -> None:
    for kid in FIRST_APPROVED_PACK_IDS:
        item = get_inventory_item(kid)
        assert item is not None
        assert item.status == KnowledgeItemStatus.APPROVED
        assert can_admit_to_production(item)
    manifest = list_manifest()
    assert any(entry["action"] == "exclude" for entry in manifest)
    assert any("phase_ai" in entry["source"] for entry in manifest)
    fields = required_metadata_fields()
    assert "source_hash" in fields
    assert "citation_required" in fields


def test_no_automatic_execution_flags_in_api(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    policy = client.get("/knowledge-foundation/policy", headers=auth_headers)
    assert policy.status_code == 200
    body = policy.json()
    assert body["embeddings_enabled"] is False
    assert body["bulk_repo_ingestion_enabled"] is False
    assert body["execution_enabled"] is False
    assert body["agent_run_enabled"] is False
    assert body["storage_option"] == "postgres_fts"

    skills = client.get("/specialist-skills", headers=auth_headers)
    assert skills.status_code == 200
    payload = skills.json()
    assert payload["execution_enabled"] is False
    assert payload["duplicates_agent_registry"] is False
    assert payload["count"] == 14

    resolve = client.get(
        "/specialist-skills/resolve",
        headers=auth_headers,
        params={"route_category": "content"},
    )
    assert resolve.status_code == 200
    assert resolve.json()["skill"]["code"] == "content.telegram_post"
    assert resolve.json()["execution_enabled"] is False


def test_inventory_filters_and_review_api(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    listed = client.get(
        "/knowledge-foundation/inventory",
        headers=auth_headers,
        params={"status": "candidate"},
    )
    assert listed.status_code == 200
    assert listed.json()
    candidate_id = listed.json()[0]["id"]

    approved = client.post(
        f"/knowledge-foundation/inventory/{candidate_id}/approve",
        headers=auth_headers,
        json={"note": "reviewed in test"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    rejected = client.post(
        f"/knowledge-foundation/inventory/{candidate_id}/reject",
        headers=auth_headers,
        json={"note": "rollback"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_retrieval_preview_api(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client.post(
        "/knowledge-foundation/items/ingest-content-pack",
        headers=auth_headers,
    )
    preview = client.get(
        "/knowledge-foundation/retrieval-preview",
        headers=auth_headers,
        params={"skill_code": "content.telegram_post"},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["embeddings_used"] is False
    assert body["similarity_as_confidence"] is False
    assert body["hits"] or body["result"]["items"]
    hits = body["hits"] or body["result"]["items"]
    assert any(
        (h.get("knowledge_type") == "constitutional_policy")
        for h in hits
    )
