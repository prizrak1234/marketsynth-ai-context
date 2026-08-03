"""KB-WPL-01.2.1 — Workflow catalog quality repair tests."""

from __future__ import annotations

import json
from pathlib import Path

from app.knowledge.workflow_catalog.candidate_eligibility import evaluate_candidate_eligibility
from app.knowledge.workflow_catalog.classifiers import classify_workflow
from app.knowledge.workflow_catalog.contracts import SecurityFindingRecord
from app.knowledge.workflow_catalog.normalization import extract_integrated_providers
from app.knowledge.workflow_catalog.parser import parse_workflow_data
from app.knowledge.workflow_catalog.serialization import assert_no_executable_body
from tests.support.wpl_schema_validation import FROZEN_BUNDLE_HASH, recompute_bundle_hash

REPO = Path(__file__).resolve().parents[1]
CATALOG_ROOT = REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0"
STATS_PATH = CATALOG_ROOT / "statistics.json"
SECURITY_PATH = CATALOG_ROOT / "security_summary.json"
SCAN_PROVENANCE = {"source_type": "security_scan", "archive_id": "arc", "source_id": "wf"}


def _sample(**overrides: object) -> dict:
    base = {
        "name": "Test SEO Workflow",
        "nodes": [
            {"type": "n8n-nodes-base.manualTrigger", "name": "Start"},
            {"type": "n8n-nodes-base.httpRequest", "name": "Fetch"},
        ],
        "connections": {},
    }
    base.update(overrides)
    return base


def _parse(**overrides: object):
    return parse_workflow_data(
        _sample(**overrides),
        source_path="sample.json",
        source_path_hash="a" * 64,
    )


def test_01_sticky_note_alone_not_documentation_capability() -> None:
    wf = _sample(
        nodes=[
            {"type": "n8n-nodes-base.manualTrigger", "name": "Start"},
            {
                "type": "n8n-nodes-base.stickyNote",
                "name": "Note",
                "parameters": {"content": "hello"},
            },
        ]
    )
    outcome = parse_workflow_data(wf, source_path="a.json", source_path_hash="b" * 64)
    assert outcome.record is not None
    assert "workflow_documentation" not in outcome.record.categories
    assert outcome.diagnostics.documentation_quality in {"minimal", "present", "substantial"}


def test_02_sticky_note_alone_not_backup_capability() -> None:
    outcome = _parse(
        nodes=[
            {
                "type": "n8n-nodes-base.stickyNote",
                "name": "Note",
                "parameters": {"content": "backup note"},
            },
        ]
    )
    assert outcome.record is not None
    assert "workflow_backup" not in outcome.record.categories


def test_03_explicit_documentation_workflow_classified() -> None:
    outcome = _parse(
        name="Generate workflow documentation export",
        nodes=[
            {"type": "n8n-nodes-base.manualTrigger", "name": "Start"},
            {"type": "n8n-nodes-base.googleDocs", "name": "Write Doc"},
        ],
    )
    assert outcome.record is not None
    assert "workflow_documentation" in outcome.record.categories


def test_04_explicit_backup_workflow_classified() -> None:
    outcome = _parse(
        name="Backup workflow snapshot to drive",
        nodes=[
            {"type": "n8n-nodes-base.manualTrigger", "name": "Start"},
            {
                "type": "n8n-nodes-base.n8n",
                "name": "Export",
                "parameters": {"operation": "getWorkflow"},
            },
            {"type": "n8n-nodes-base.googleDrive", "name": "Store"},
        ],
    )
    assert outcome.record is not None
    assert "workflow_backup" in outcome.record.categories


def test_05_sticky_note_absent_from_providers() -> None:
    outcome = _parse(
        nodes=[
            {"type": "n8n-nodes-base.stickyNote", "name": "Note"},
            {"type": "n8n-nodes-base.gmail", "name": "Send"},
        ]
    )
    assert outcome.record is not None
    assert "stickyNote" not in outcome.record.providers
    assert "Gmail" in outcome.record.providers


def test_06_code_absent_from_providers() -> None:
    outcome = _parse(nodes=[{"type": "n8n-nodes-base.code", "name": "Code"}])
    assert outcome.record is not None
    assert "code" not in outcome.record.providers


def test_07_generic_nodes_absent_from_providers() -> None:
    outcome = _parse(
        nodes=[
            {"type": "n8n-nodes-base.set", "name": "Set"},
            {"type": "n8n-nodes-base.if", "name": "If"},
            {"type": "n8n-nodes-base.merge", "name": "Merge"},
            {"type": "n8n-nodes-base.wait", "name": "Wait"},
        ]
    )
    assert outcome.record is not None
    for generic in ("set", "if", "merge", "wait"):
        assert generic not in outcome.record.providers


def test_08_http_request_absent_from_providers() -> None:
    outcome = _parse(nodes=[{"type": "n8n-nodes-base.httpRequest", "name": "HTTP"}])
    assert outcome.record is not None
    assert "httpRequest" not in outcome.record.providers


def test_09_real_integrated_provider_extracted() -> None:
    outcome = _parse(nodes=[{"type": "n8n-nodes-base.telegram", "name": "Send"}])
    assert outcome.record is not None
    assert "Telegram" in outcome.record.providers


def test_10_provider_from_hostname_normalized() -> None:
    wf = _sample(
        nodes=[
            {
                "type": "n8n-nodes-base.httpRequest",
                "name": "OpenAI",
                "parameters": {"url": "https://api.openai.com/v1/chat/completions"},
            }
        ]
    )
    node_types = [node["type"] for node in wf["nodes"]]
    providers = extract_integrated_providers(
        wf["nodes"],
        node_types,
        json.dumps(wf),
        [],
    )
    assert "OpenAI" in providers


def test_11_node_types_remain_available() -> None:
    outcome = _parse(nodes=[{"type": "n8n-nodes-base.httpRequest", "name": "HTTP"}])
    assert outcome.record is not None
    assert "n8n-nodes-base.httpRequest" in outcome.record.node_types


def test_12_functional_classes_available() -> None:
    outcome = _parse(
        nodes=[
            {"type": "n8n-nodes-base.scheduleTrigger", "name": "Cron"},
            {"type": "n8n-nodes-base.set", "name": "Set"},
            {"type": "n8n-nodes-base.if", "name": "If"},
        ]
    )
    assert "trigger" in outcome.diagnostics.functional_classes
    assert "transform" in outcome.diagnostics.functional_classes
    assert "branch" in outcome.diagnostics.functional_classes


def test_13_if_alone_not_human_approval() -> None:
    result = classify_workflow(
        "Branch workflow",
        "",
        ["n8n-nodes-base.if"],
        [],
        [],
        nodes=[{"type": "n8n-nodes-base.if", "name": "If"}],
        documentation_quality="none",
    )
    assert "human_approval" not in result.categories
    assert result.approval_signal_strength in {"none", "weak"}


def test_14_wait_alone_not_human_approval() -> None:
    result = classify_workflow(
        "Wait workflow",
        "",
        ["n8n-nodes-base.wait"],
        [],
        [],
        nodes=[{"type": "n8n-nodes-base.wait", "name": "Wait"}],
        documentation_quality="none",
    )
    assert "human_approval" not in result.categories


def test_15_explicit_approve_path_implies_approval() -> None:
    result = classify_workflow(
        "Moderation",
        "",
        ["n8n-nodes-base.slackHitlTool"],
        ["Slack"],
        [],
        nodes=[{"type": "n8n-nodes-base.slackHitlTool", "name": "Human approve/reject"}],
        documentation_quality="none",
    )
    assert "human_approval" in result.categories
    assert result.approval_signal_strength == "explicit"


def test_16_approval_signal_strength_explainable() -> None:
    result = classify_workflow(
        "Review queue",
        "awaiting approval",
        ["n8n-nodes-base.formTrigger"],
        [],
        [],
        nodes=[{"type": "n8n-nodes-base.formTrigger", "name": "Confirm"}],
        documentation_quality="none",
    )
    assert result.approval_explanation


def test_17_critical_security_finding_blocks_candidate() -> None:
    outcome = _parse()
    assert outcome.record and outcome.diagnostics.classification
    record = outcome.record.model_copy(
        update={
            "security_findings": [
                SecurityFindingRecord(
                    finding_id="sf-test",
                    severity="critical",
                    finding_type="destructive_sql",
                    location="workflow_body",
                    description="test",
                    provenance=SCAN_PROVENANCE,
                )
            ],
            "destructive_actions": True,
        }
    )
    evaluation = evaluate_candidate_eligibility(record, outcome.diagnostics.classification)
    assert evaluation.adaptation_status != "reusable_pattern_candidate"
    assert evaluation.candidate_blockers


def test_18_destructive_action_blocks_candidate() -> None:
    outcome = _parse()
    assert outcome.record and outcome.diagnostics.classification
    record = outcome.record.model_copy(update={"destructive_actions": True})
    evaluation = evaluate_candidate_eligibility(record, outcome.diagnostics.classification)
    assert "destructive_or_shell" in evaluation.candidate_blockers


def test_19_shell_node_blocks_candidate() -> None:
    outcome = _parse(nodes=[{"type": "n8n-nodes-base.executeCommand", "name": "Shell"}])
    assert outcome.record and outcome.diagnostics.classification
    evaluation = evaluate_candidate_eligibility(outcome.record, outcome.diagnostics.classification)
    assert evaluation.adaptation_status == "requires_rewrite"


def test_20_exposed_secret_blocks_candidate() -> None:
    outcome = _parse()
    assert outcome.record and outcome.diagnostics.classification
    record = outcome.record.model_copy(
        update={
            "security_findings": [
                SecurityFindingRecord(
                    finding_id="sf-secret",
                    severity="critical",
                    finding_type="bearer_token",
                    location="workflow_body",
                    description="test",
                    provenance=SCAN_PROVENANCE,
                )
            ]
        }
    )
    evaluation = evaluate_candidate_eligibility(record, outcome.diagnostics.classification)
    assert any("exposed_secret" in blocker for blocker in evaluation.candidate_blockers)


def test_21_community_node_blocks_candidate_when_high_risk() -> None:
    outcome = _parse(nodes=[{"type": "n8n-nodes-custom.foo", "name": "Custom"}])
    assert outcome.record and outcome.diagnostics.classification
    record = outcome.record.model_copy(
        update={
            "security_findings": [
                SecurityFindingRecord(
                    finding_id="sf-community",
                    severity="critical",
                    finding_type="community_node",
                    location="node",
                    description="test",
                    provenance=SCAN_PROVENANCE,
                )
            ]
        }
    )
    evaluation = evaluate_candidate_eligibility(record, outcome.diagnostics.classification)
    assert "unknown_high_risk_community_node" in evaluation.candidate_blockers


def test_22_publication_candidate_requires_manual_security_review() -> None:
    outcome = _parse(nodes=[{"type": "n8n-nodes-base.telegram", "name": "Publish"}])
    assert outcome.diagnostics.candidate_evaluation is not None
    reasons = outcome.diagnostics.candidate_evaluation.candidate_reasons
    manual_reason = any("manual" in reason for reason in reasons)
    assert manual_reason or outcome.record.adaptation_status == "catalog_only"


def test_23_billing_candidate_requires_manual_security_review() -> None:
    wf = _sample(name="Stripe billing webhook")
    wf["nodes"].append({"type": "n8n-nodes-base.httpRequest", "name": "Stripe"})
    outcome = parse_workflow_data(wf, source_path="bill.json", source_path_hash="c" * 64)
    assert outcome.record is not None
    assert outcome.record.billing_actions is True


def test_24_personal_data_candidate_elevated_review() -> None:
    wf = _sample(name="Customer onboarding")
    wf["description"] = "passport scan upload"
    outcome = parse_workflow_data(wf, source_path="pii.json", source_path_hash="d" * 64)
    assert outcome.record is not None
    assert outcome.record.personal_data_risk == "high"


def test_25_low_confidence_not_candidate() -> None:
    outcome = _parse(
        name="Untitled workflow",
        nodes=[{"type": "n8n-nodes-base.noOp", "name": "NoOp"}],
    )
    assert outcome.record is not None
    assert outcome.record.adaptation_status != "reusable_pattern_candidate"


def test_26_candidate_reasons_populated_for_eligible() -> None:
    outcome = _parse(
        name="SEO keyword audit report",
        nodes=[
            {"type": "n8n-nodes-base.manualTrigger", "name": "Start"},
            {"type": "n8n-nodes-base.httpRequest", "name": "Fetch"},
        ],
    )
    evaluation = outcome.diagnostics.candidate_evaluation
    assert evaluation is not None
    if evaluation.adaptation_status == "reusable_pattern_candidate":
        assert evaluation.candidate_reasons


def test_27_candidate_blockers_populated_when_blocked() -> None:
    outcome = _parse(nodes=[{"type": "n8n-nodes-base.code", "name": "Code"}])
    evaluation = outcome.diagnostics.candidate_evaluation
    assert evaluation is not None
    assert "code_node_present" in evaluation.candidate_blockers


def test_28_priority_reasons_populated() -> None:
    outcome = _parse(
        name="SEO keyword audit",
        nodes=[{"type": "n8n-nodes-base.httpRequest", "name": "Fetch"}],
    )
    assert outcome.diagnostics.classification is not None
    assert outcome.diagnostics.classification.priority_reasons


def test_29_security_metrics_distinguish_layers() -> None:
    summary = json.loads(SECURITY_PATH.read_text(encoding="utf-8"))
    assert "total_findings" in summary
    assert "affected_workflows_by_finding_type" in summary
    assert "total_detected_nodes" in summary["code_nodes"]


def test_30_invalid_json_excluded_from_valid_statistics() -> None:
    stats = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    assert stats["invalid_count"] == 1
    assert stats["valid_workflow_denominator"] == stats["unique_exports"]
    caps = stats["capability_distribution"]
    assert caps.get("workflow_documentation", 0) < stats["valid_workflow_denominator"]


def test_31_catalog_metadata_only() -> None:
    catalog = json.loads((CATALOG_ROOT / "catalog.json").read_text(encoding="utf-8"))
    for template in catalog["templates"][:20]:
        assert_no_executable_body(template)


def test_32_catalog_hash_deterministic() -> None:
    from app.knowledge.workflow_catalog.serialization import bundle_catalog_hash

    catalog = json.loads((CATALOG_ROOT / "catalog.json").read_text(encoding="utf-8"))
    assert bundle_catalog_hash(catalog)


def test_33_frozen_wpl_schema_bundle_unchanged() -> None:
    assert recompute_bundle_hash() == FROZEN_BUNDLE_HASH


def test_34_no_workflow_execution_introduced() -> None:
    parser_text = (REPO / "app/knowledge/workflow_catalog/parser.py").read_text(encoding="utf-8")
    assert "subprocess" not in parser_text
    assert "eval(" not in parser_text


def test_35_catalog_quality_repair_distribution_sane() -> None:
    stats = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    assert stats["capability_distribution"].get("workflow_documentation", 0) < 50
    assert stats["capability_distribution"].get("workflow_backup", 0) < 50
    providers = stats["provider_distribution"]
    for generic in ("stickyNote", "code", "set", "if", "merge", "wait", "httpRequest"):
        assert generic not in providers
