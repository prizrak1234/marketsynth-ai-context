"""Generate KB-WPL-01.8 discovery read-model bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "packages" / "knowledge" / "discovery" / "0.1.0"

ALIASES = [
    {"alias": "проверить идею", "capability_ids": ["marketing.market_validation"], "locale": "ru"},
    {"alias": "проверить бизнес-идею", "capability_ids": ["marketing.market_validation"], "locale": "ru"},
    {"alias": "исследовать рынок", "capability_ids": ["marketing.market_research"], "locale": "ru"},
    {"alias": "конкуренты", "capability_ids": ["marketing.competitive_intelligence"], "locale": "ru"},
    {"alias": "проанализировать конкурентов", "capability_ids": ["marketing.competitive_intelligence"], "locale": "ru"},
    {"alias": "целевая аудитория", "capability_ids": ["marketing.customer_intelligence"], "locale": "ru"},
    {"alias": "icp", "capability_ids": ["marketing.customer_intelligence"], "locale": "en"},
    {"alias": "позиционирование", "capability_ids": ["marketing.positioning"], "locale": "ru"},
    {"alias": "positioning", "capability_ids": ["marketing.positioning"], "locale": "en"},
    {"alias": "оффер", "capability_ids": ["marketing.offer_architecture"], "locale": "ru"},
    {"alias": "offer", "capability_ids": ["marketing.offer_architecture"], "locale": "en"},
    {"alias": "пост в telegram", "capability_ids": ["marketing.distribution"], "locale": "ru"},
    {"alias": "telegram post", "capability_ids": ["marketing.distribution"], "locale": "en"},
    {"alias": "опубликовать пост", "capability_ids": ["marketing.distribution"], "locale": "ru"},
    {"alias": "youtube script", "capability_ids": ["deliverables.content_architecture"], "locale": "en"},
    {"alias": "сценарий youtube", "capability_ids": ["deliverables.content_architecture"], "locale": "ru"},
    {"alias": "презентация", "capability_ids": ["marketing.presentation_architecture", "deliverables.presentation_architecture"], "locale": "ru"},
    {"alias": "создать презентацию", "capability_ids": ["marketing.presentation_architecture", "deliverables.presentation_architecture"], "locale": "ru"},
    {"alias": "presentation", "capability_ids": ["marketing.presentation_architecture", "deliverables.presentation_architecture"], "locale": "en"},
    {"alias": "n8n workflow", "capability_ids": ["engineering.workflow_architecture"], "locale": "en"},
    {"alias": "спроектировать n8n workflow", "capability_ids": ["engineering.workflow_architecture"], "locale": "ru"},
    {"alias": "ошибка n8n", "capability_ids": ["engineering.workflow_debugging"], "locale": "ru"},
    {"alias": "n8n debugging", "capability_ids": ["engineering.workflow_debugging"], "locale": "en"},
    {"alias": "deployment review", "capability_ids": ["engineering.deployment_review"], "locale": "en"},
    {"alias": "связать знания", "capability_ids": ["knowledge.knowledge_linking"], "locale": "ru"},
    {"alias": "связать документы", "capability_ids": ["knowledge.knowledge_linking"], "locale": "ru"},
    {"alias": "найти дубли", "capability_ids": ["knowledge.knowledge_linking"], "locale": "ru"},
    {"alias": "связать документы и найти дубли", "capability_ids": ["knowledge.knowledge_linking"], "locale": "ru"},
    {"alias": "knowledge linking", "capability_ids": ["knowledge.knowledge_linking"], "locale": "en"},
    {"alias": "n8n", "capability_ids": ["engineering.workflow_architecture", "engineering.workflow_debugging"], "locale": "en"},
    {"alias": "workflow", "capability_ids": ["engineering.workflow_architecture"], "locale": "en"},
    {"alias": "retry pattern", "capability_ids": ["engineering.error_recovery"], "pattern_ids": ["retry_with_idempotency"], "locale": "en"},
    {"alias": "approval pattern", "capability_ids": ["marketing.distribution"], "pattern_ids": ["human_approval_before_publication"], "locale": "en"},
    {"alias": "запустить рекламу", "capability_ids": ["marketing.distribution"], "locale": "ru"},
    {"alias": "advertising", "capability_ids": ["marketing.distribution"], "locale": "en"},
]

QUERY_MODES = [
    "task_routing",
    "capability_lookup",
    "skill_lookup",
    "workflow_pattern_lookup",
    "engineering_diagnosis_lookup",
    "knowledge_maintenance_lookup",
    "deliverable_lookup",
    "internal_audit_lookup",
]

SAFE_ACTIONS = [
    "use_internal_skill_contract",
    "review_workflow_pattern",
    "review_practice",
    "inspect_error_pattern",
    "gather_missing_evidence",
    "request_human_review",
    "request_security_review",
    "request_connector_design",
    "request_runtime_implementation",
    "adapt_internal_methodology",
    "defer",
    "reject",
]

RANKING_WEIGHTS = {
    "profession_fit": 10,
    "capability_fit": 12,
    "explicit_request_fit": 15,
    "skill_availability": 8,
    "pattern_support": 4,
    "trust_status": 6,
    "maturity": 5,
    "tenant_visibility": 20,
    "provider_fit": 3,
    "platform_fit": 3,
    "evidence_fit": 4,
    "approval_compatibility": 6,
    "execution_sensitivity_compatibility": 8,
    "gap_severity": -5,
    "dependency_completeness": 5,
    "source_quality": 4,
    "version_compatibility": 3,
    "limitations_penalty": -4,
}

FIXTURES = [
    {"id": "fixture-market-validation", "task_description": "Проверить бизнес-идею", "mode": "task_routing"},
    {"id": "fixture-market-research", "task_description": "Исследовать рынок", "mode": "task_routing"},
    {"id": "fixture-competitors", "task_description": "Проанализировать конкурентов", "mode": "task_routing"},
    {"id": "fixture-icp", "task_description": "Определить ICP", "mode": "task_routing"},
    {"id": "fixture-positioning", "task_description": "Сделать позиционирование", "mode": "task_routing"},
    {"id": "fixture-offer", "task_description": "Создать оффер", "mode": "task_routing"},
    {"id": "fixture-telegram", "task_description": "Сделать пост в Telegram", "mode": "task_routing"},
    {"id": "fixture-youtube", "task_description": "Подготовить сценарий YouTube", "mode": "deliverable_lookup"},
    {"id": "fixture-presentation", "task_description": "Создать презентацию", "mode": "deliverable_lookup"},
    {"id": "fixture-n8n-arch", "task_description": "Спроектировать n8n workflow", "mode": "engineering_diagnosis_lookup"},
    {"id": "fixture-n8n-debug", "task_description": "Найти ошибку в n8n workflow", "mode": "engineering_diagnosis_lookup"},
    {"id": "fixture-n8n-deploy", "task_description": "Проверить workflow перед деплоем", "mode": "engineering_diagnosis_lookup"},
    {"id": "fixture-linking", "task_description": "Связать документы и найти дубли", "mode": "knowledge_maintenance_lookup"},
    {"id": "fixture-retry", "task_description": "Найти паттерн retry", "mode": "workflow_pattern_lookup"},
    {"id": "fixture-approval", "task_description": "Найти approval pattern", "mode": "workflow_pattern_lookup"},
    {"id": "fixture-ad-spend", "task_description": "Запустить рекламу", "mode": "task_routing", "execution_sensitivity": "billing"},
    {"id": "fixture-publish", "task_description": "Опубликовать пост", "mode": "task_routing", "execution_sensitivity": "publication"},
    {"id": "fixture-ambiguous", "task_description": "Сделать что-то полезное для бизнеса", "mode": "task_routing"},
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    write_json(BUNDLE / "aliases.json", {"version": "0.1.0", "aliases": ALIASES})
    write_json(BUNDLE / "ranking_weights.json", {"version": "0.1.0", "weights": RANKING_WEIGHTS})
    write_json(BUNDLE / "query_modes.json", {"version": "0.1.0", "modes": QUERY_MODES})
    write_json(BUNDLE / "safe_actions.json", {"version": "0.1.0", "actions": SAFE_ACTIONS})
    write_json(BUNDLE / "discovery_fixtures.json", {"version": "0.1.0", "fixtures": FIXTURES})

    data_files = [
        "aliases.json",
        "ranking_weights.json",
        "query_modes.json",
        "safe_actions.json",
        "discovery_fixtures.json",
    ]
    file_hashes = {name: sha256_file(BUNDLE / name) for name in data_files}
    bundle_hash = hashlib.sha256(
        json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    semantic_hash = bundle_hash

    write_json(
        BUNDLE / "freeze_manifest.json",
        {
            "schema_version": "0.1.0",
            "bundle_status": "read_only_discovery_model",
            "runtime_authorized": False,
            "external_discovery": False,
            "vector_search": False,
            "llm_ranking": False,
            "persistence": False,
            "installation_actions": False,
            "file_hashes": file_hashes,
            "bundle_hash": bundle_hash,
            "semantic_bundle_hash": semantic_hash,
            "generated_at": "2026-07-24T01:00:00Z",
        },
    )
    (BUNDLE / "README.md").write_text(
        "# Discovery Read Models v0.1.0\n\n"
        "Deterministic read-only discovery aliases, ranking weights, and fixtures.\n\n"
        f"- bundle_hash: `{bundle_hash}`\n",
        encoding="utf-8",
    )
    print(f"bundle_hash={bundle_hash}")


if __name__ == "__main__":
    main()
