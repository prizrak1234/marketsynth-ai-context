#!/usr/bin/env python3
# ruff: noqa: E501
"""Generate ARCHIVE-MKT-01 native skill packages and fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "packages" / "skills"

CIM_HASH = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
ICP_HASH = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
CA_HASH = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
MV_HASH = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
POS_HASH = "cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6"
CIM_URI = (
    "https://schemas.marketsynth.ai/customer-intelligence/0.1.0/"
    "customer-intelligence.schema.json"
)
SEG = "seg-remote-eng"
RESEARCH_FIELDS = {
    "evidence_gaps": {"type": "array", "items": {"type": "string", "maxLength": 2000}, "maxItems": 30},
    "coverage": {"type": "string", "enum": ["full", "partial", "minimal", "unknown"]},
    "evidence_quality": {
        "type": "string",
        "enum": ["comprehensive", "partial", "insufficient", "conflicted", "unknown"],
    },
    "research_status": {
        "type": "string",
        "enum": [
            "complete",
            "partially_complete",
            "insufficient_sources",
            "conflicted",
            "out_of_scope",
        ],
    },
}
RESEARCH_REQUIRED = ["evidence_gaps", "coverage", "evidence_quality", "research_status"]


def research_fixture_defaults() -> dict:
    return {
        "evidence_gaps": [],
        "coverage": "partial",
        "evidence_quality": "partial",
        "research_status": "partially_complete",
    }


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    write(path, json.dumps(data, indent=2, ensure_ascii=False))


def cim_ref(skill: str) -> dict:
    return {
        "source_skill_id": "ms.skill.icp_segmentation",
        "source_skill_version": "0.1.0",
        "source_output_hash": ICP_HASH,
        "cim_schema_uri": CIM_URI,
        "cim_version": "0.1.0",
        "cim_document_hash": CIM_HASH,
        "selected_segment_ids": [SEG],
        "source_evidence_references": ["ev-seg-seg-remote-eng"],
        "source_unknowns": [],
        "source_conflicts": [],
    }


def upstream_ref(skill_id: str, version: str, out_hash: str) -> dict:
    return {
        "source_skill_id": skill_id,
        "source_skill_version": version,
        "source_output_hash": out_hash,
        "source_status": "complete",
        "source_evidence_references": ["ev-upstream-001"],
        "source_unknowns": [],
        "source_conflicts": [],
    }


def manifest_block(
    skill_id: str,
    name: str,
    description: str,
    capabilities: list[str],
    deps: list[tuple[str, str, str]],
    output_schema: str = "schemas/output.schema.json",
) -> str:
    cap_lines = "\n".join(f"  - {c}" for c in capabilities)
    dep_lines = "\n".join(
        f'    - id: {sid}\n      relationship: {rel}\n      note: "{note}"'
        for sid, rel, note in deps
    )
    return (
        f"id: {skill_id}\n"
        f"name: {name}\n"
        f"version: 0.1.0\n"
        f"description: >\n"
        f"  {description}\n"
        f"owner: Marketsynth Platform\n"
        f"source: platform_native\n"
        f"license: Proprietary\n"
        f"status: candidate\n"
        f"output_contract_type: research\n"
        f"capabilities:\n{cap_lines}\n"
        f"activation_conditions:\n"
        f"  runtime_compatibility:\n"
        f"    - operator_dry_run\n"
        f"    - assistant_explicit_run\n"
        f"  requires_governed_context: true\n"
        f"  executable: false\n"
        f"required_inputs:\n"
        f"  schema_ref: schemas/input.schema.json\n"
        f"output_schema:\n"
        f"  schema_ref: {output_schema}\n"
        f"required_evidence:\n"
        f"  classes:\n"
        f"    - user_statement\n"
        f"    - market_source\n"
        f"    - audience_signal\n"
        f"    - assumption\n"
        f"    - inference\n"
        f"  rules:\n"
        f"    - id: no_runtime_execution\n"
        f"      description: Skill package is candidate-only; no autonomous execution.\n"
        f"    - id: no_invented_customer_answers\n"
        f"      description: Output must not contain fabricated respondent answers.\n"
        f"dependencies:\n"
        f"  declared_future_dependencies:\n"
        f"{dep_lines}\n"
        f"allowed_tools: []\n"
        f"approval_policy:\n"
        f"  analysis_preparation:\n"
        f"    external_side_effects: false\n"
        f"    approval_required: false\n"
        f"  customer_facing_transition:\n"
        f"    approval_required: true\n"
        f"    note: Human approval required before customer-facing copy or launch.\n"
        f"tenant_scope: global\n"
        f"quality_threshold:\n"
        f"  eval_required_before_active: true\n"
        f"  minimum_eval_cases: 1\n"
        f"  current_state: skeleton_only\n"
        f"known_limitations:\n"
        f"  - Non-executable candidate package — no runtime loader.\n"
        f"  - Does not publish, spend, or authorize launch.\n"
        f"  - Does not override Market Validation verdict.\n"
        f"test_suite:\n"
        f"  manifest: tests/eval_manifest.yaml\n"
        f"provenance:\n"
        f"  origin: platform_native\n"
        f"  methodology:\n"
        f"    - ARCHIVE-MKT-01 adapted methodology (evidence-aware rewrite)\n"
        f"  external_methodology_references:\n"
        f"    - audit_card: docs/research/archive-marketer/source-audit.md\n"
        f"      reuse: methodology_only\n"
        f"      note: Archive is methodology donor only — not trusted Skill package.\n"
        f"  external_code_dependency: false\n"
        f"runtime_compatibility:\n"
        f"  - operator_dry_run\n"
        f"  - assistant_explicit_run\n"
        f"knowledge_scopes:\n"
        f"  - customer_intelligence\n"
        f"  - marketing_claims\n"
        f"network_policy:\n"
        f"  default: deny\n"
        f"  allowed_hosts: []\n"
        f"  allowed_connectors_only: true\n"
        f"script_policy:\n"
        f"  enabled: false\n"
        f"  reason: ARCHIVE-MKT-01 skeleton — scripts forbidden.\n"
        f"resource_limits:\n"
        f"  max_package_size_mib: 10\n"
        f"  max_skill_md_kib: 256\n"
    )


def eval_manifest(skill_id: str, cases: list[tuple[str, str]]) -> str:
    lines = [
        "version: 1",
        f"skill_id: {skill_id}",
        "eval_cases:",
    ]
    for case_id, fixture in cases:
        lines.append(f"  - id: {case_id}")
        lines.append(f"    fixture: {fixture}")
        lines.append("    expectation: schema_valid")
    return "\n".join(lines) + "\n"


def skill_md(skill_id: str, name: str, purpose: str) -> str:
    return dedent(
        f"""\
        # {name}

        **Skill ID:** `{skill_id}`  
        **Version:** 0.1.0  
        **Status:** candidate (non-executable)

        ## Purpose

        {purpose}

        ## Boundaries

        - Does not execute at runtime.
        - Does not access connectors, network, or external APIs.
        - Does not override Market Validation verdict.
        - Does not produce approved customer-facing copy.
        - Archive methodology adapted with evidence discipline — not copied verbatim.

        ## Output contract

        `output_contract_type: research`

        ## Human approval

        Human approval is required before any customer-facing publication or spend.
        """
    )


def build_customer_interview_design() -> None:
    root = SKILLS / "ms.skill.customer_interview_design"
    sid = "ms.skill.customer_interview_design"
    write(
        root / "manifest.yaml",
        manifest_block(
            sid,
            "Customer Interview Design",
            "Design evidence-aware customer interview guides from CIM segments "
            "without inventing respondent answers.",
            [
                "interview_objective_definition",
                "segment_context_reference",
                "pain_question_design",
                "desired_state_question_design",
                "risk_and_safety_question_design",
                "objection_question_design",
                "evidence_collection_plan",
                "interview_bias_detection",
            ],
            [
                ("ms.skill.icp_segmentation", "required_dependency", "CIM >=0.1.0,<1.0.0"),
                ("ms.skill.market_research", "optional_dependency", "Optional context"),
            ],
        ),
    )
    write(
        root / "SKILL.md",
        skill_md(
            sid,
            "Customer Interview Design",
            "Transform CIM segment context into structured interview questions "
            "tagged by evidence purpose. Questions are not customer evidence.",
        ),
    )
    write(
        root / "resources/archive-customer-interview-framework.md",
        dedent(
            """\
            # Adapted Customer Interview Framework (ARCHIVE-MKT-01)

            Evidence-aware rewrite of segment interview methodology.

            ## Principles

            1. Questions collect evidence — they are not evidence themselves.
            2. Open-ended, non-leading phrasing.
            3. Separate analyst conclusions from question text.
            4. Tag each question with evidence objective and bias risk.
            5. Respondent answers default to `user_statement` / unverified until supported.

            ## Domains

            - Current state and pain
            - Desired future state and transformation
            - Measurable outcomes and time expectations
            - Service and convenience expectations
            - Safety and prior negative experience
            - Trust barriers and price/value concerns
            """
        ),
    )
    question_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{sid}/schemas/question.schema.json",
        "title": "InterviewQuestion",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "question_id": {"type": "string", "maxLength": 128},
            "domain": {"type": "string", "maxLength": 128},
            "question_text": {"type": "string", "maxLength": 4000},
            "question_type": {
                "type": "string",
                "enum": ["open", "closed", "probe", "scale", "unknown"],
            },
            "evidence_objective": {"type": "string", "maxLength": 2000},
            "expected_evidence_type": {"type": "string", "maxLength": 128},
            "follow_up_rules": {"type": "array", "items": {"type": "string"}},
            "leading_risk": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
            "sensitivity": {"type": "string", "enum": ["none", "moderate", "high", "unknown"]},
            "notes": {"type": "string", "maxLength": 2000},
            "provenance": {"type": "object"},
        },
        "required": [
            "question_id",
            "domain",
            "question_text",
            "question_type",
            "evidence_objective",
            "expected_evidence_type",
            "leading_risk",
            "sensitivity",
            "provenance",
        ],
    }
    write_json(root / "schemas/question.schema.json", question_schema)
    write_json(
        root / "schemas/input.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/input/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "customer_intelligence_reference": {"type": "object"},
                "selected_segment_ids": {"type": "array", "items": {"type": "string"}},
                "research_objectives": {"type": "array", "items": {"type": "string"}},
                "cim_claim_catalog": {"type": "object"},
            },
            "required": [
                "customer_intelligence_reference",
                "selected_segment_ids",
                "research_objectives",
            ],
        },
    )
    write_json(
        root / "schemas/output.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/output/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "interview_guide_id": {"type": "string"},
                "skill_id": {"type": "string", "const": sid},
                "skill_version": {"type": "string"},
                "cim_reference": {"type": "object"},
                "selected_segment_ids": {"type": "array", "items": {"type": "string"}},
                "research_objectives": {"type": "array", "items": {"type": "string"}},
                "interview_sections": {"type": "array", "items": {"type": "object"}},
                "questions": {
                    "type": "array",
                    "items": {"$ref": "schemas/question.schema.json"},
                },
                "follow_up_probes": {"type": "array", "items": {"type": "object"}},
                "evidence_capture_fields": {"type": "array", "items": {"type": "string"}},
                "bias_warnings": {"type": "array", "items": {"type": "string"}},
                "sensitive_topic_warnings": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "object"}},
                "unknowns": {"type": "array", "items": {"type": "object"}},
                **RESEARCH_FIELDS,
                "human_review_required": {"type": "boolean"},
                "provenance": {"type": "object"},
                "input_hash": {"type": "string", "minLength": 64, "maxLength": 64},
                "output_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            },
            "required": [
                "interview_guide_id",
                "skill_id",
                "skill_version",
                "cim_reference",
                "selected_segment_ids",
                "research_objectives",
                "interview_sections",
                "questions",
                "follow_up_probes",
                "evidence_capture_fields",
                "bias_warnings",
                "sensitive_topic_warnings",
                "assumptions",
                "unknowns",
                *RESEARCH_REQUIRED,
                "human_review_required",
                "provenance",
                "input_hash",
                "output_hash",
            ],
        },
    )
    q = {
        "question_id": "q-pain-1",
        "domain": "pain_and_discomfort",
        "question_text": "What is most frustrating about your current workflow today?",
        "question_type": "open",
        "evidence_objective": "Capture unprompted pain language",
        "expected_evidence_type": "user_statement",
        "follow_up_rules": ["Ask for a recent example"],
        "leading_risk": "low",
        "sensitivity": "none",
        "notes": "Non-leading open question",
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
    }
    output_ok = {
        "interview_guide_id": "int-guide-001",
        "skill_id": sid,
        "skill_version": "0.1.0",
        "cim_reference": cim_ref(sid),
        "selected_segment_ids": [SEG],
        "research_objectives": ["Understand async collaboration pain points"],
        "interview_sections": [{"section_id": "sec-1", "title": "Current state", "domain": "current_state"}],
        "questions": [q],
        "follow_up_probes": [{"probe_id": "probe-1", "trigger": "vague answer", "probe_text": "Can you describe a recent example?"}],
        "evidence_capture_fields": ["pain_language", "desired_outcome_language"],
        "bias_warnings": ["Avoid confirming product hypotheses during interview"],
        "sensitive_topic_warnings": [],
        "assumptions": [{"item_id": "a-1", "statement": "Segment represents target buyers", "evidence_class": "assumption"}],
        "unknowns": [{"domain": "budget", "description": "Budget sensitivity not yet explored"}],
        **research_fixture_defaults(),
        "human_review_required": True,
        "provenance": {
            "skill_id": sid,
            "skill_version": "0.1.0",
            "source_cim_output_hash": ICP_HASH,
        },
        "input_hash": "1" * 64,
        "output_hash": "2" * 64,
    }
    output_bad = dict(output_ok)
    output_bad["interview_guide_id"] = "int-guide-bad-answers"
    output_bad["respondent_answers"] = [{"answer": "Client will 100% agree"}]
    write_json(root / "tests/fixtures/output_valid_guide.json", output_ok)
    write_json(root / "tests/fixtures/output_invented_answers.json", output_bad)
    write_json(
        root / "tests/fixtures/input_segment_context.json",
        {
            "customer_intelligence_reference": cim_ref(sid),
            "selected_segment_ids": [SEG],
            "research_objectives": ["Understand async collaboration pain points"],
            "cim_claim_catalog": {"segment_ids": [SEG]},
        },
    )
    write(
        root / "tests/eval_manifest.yaml",
        eval_manifest(
            sid,
            [("valid_guide", "tests/fixtures/output_valid_guide.json")],
        ),
    )


def build_customer_meaning_extraction() -> None:
    root = SKILLS / "ms.skill.customer_meaning_extraction"
    sid = "ms.skill.customer_meaning_extraction"
    write(
        root / "manifest.yaml",
        manifest_block(
            sid,
            "Customer Meaning Extraction",
            "Extract structured customer meanings, desire-to-benefit maps and "
            "fear/objection maps without final offers or approved claims.",
            [
                "customer_meaning_normalization",
                "desire_to_benefit_mapping",
                "fear_objection_mapping",
                "trust_requirement_extraction",
                "promise_candidate_identification",
                "unsupported_promise_detection",
            ],
            [
                ("ms.skill.icp_segmentation", "required_dependency", "CIM >=0.1.0,<1.0.0"),
                ("ms.skill.customer_interview_design", "optional_dependency", "Interview guide context"),
            ],
        ),
    )
    write(
        root / "SKILL.md",
        skill_md(
            sid,
            "Customer Meaning Extraction",
            "Connect customer desire → capability → mechanism → benefit → promise "
            "candidate, and fear/objection → proof requirement, without viability verdict.",
        ),
    )
    for fname, title, props, req in [
        (
            "customer-meaning.schema.json",
            "CustomerMeaning",
            {
                "meaning_id": {"type": "string"},
                "selected_segment_ids": {"type": "array", "items": {"type": "string"}},
                "source_statement": {"type": "string"},
                "normalized_meaning": {"type": "string"},
                "meaning_type": {
                    "type": "string",
                    "enum": [
                        "desire",
                        "pain",
                        "desired_outcome",
                        "fear",
                        "objection",
                        "barrier",
                        "trigger",
                        "trust_requirement",
                        "service_expectation",
                        "safety_expectation",
                        "price_value_concern",
                        "self_doubt",
                        "previous_negative_experience",
                        "unknown",
                    ],
                },
                "customer_language": {"type": "string"},
                "desired_transformation": {"type": "string"},
                "underlying_need": {"type": "string"},
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "contradictory_evidence": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "inference": {"type": "string"},
                "confidence": {"type": "string", "enum": ["high", "medium", "low", "unknown"]},
                "unknowns": {"type": "array", "items": {"type": "string"}},
                "provenance": {"type": "object"},
            },
            [
                "meaning_id",
                "selected_segment_ids",
                "source_statement",
                "normalized_meaning",
                "meaning_type",
                "customer_language",
                "evidence_references",
                "confidence",
                "provenance",
            ],
        ),
        (
            "desire-to-benefit-map.schema.json",
            "DesireToBenefitMap",
            {
                "map_id": {"type": "string"},
                "customer_meaning_reference": {"type": "string"},
                "satisfaction_status": {
                    "type": "string",
                    "enum": ["supported", "partially_supported", "unsupported", "unknown", "conflicted"],
                },
                "product_capability_reference": {"type": "string"},
                "delivery_mechanism_reference": {"type": "string"},
                "benefit_statement": {"type": "string"},
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "conditions": {"type": "array", "items": {"type": "string"}},
                "limitations": {"type": "array", "items": {"type": "string"}},
                "unsupported_aspects": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string"},
                "provenance": {"type": "object"},
            },
            [
                "map_id",
                "customer_meaning_reference",
                "satisfaction_status",
                "benefit_statement",
                "evidence_references",
                "confidence",
                "provenance",
            ],
        ),
        (
            "fear-objection-map.schema.json",
            "FearObjectionMap",
            {
                "map_id": {"type": "string"},
                "fear_category": {
                    "type": "string",
                    "enum": [
                        "negative_experience",
                        "category_distrust",
                        "product_distrust",
                        "provider_distrust",
                        "self_doubt",
                        "price_value_mismatch",
                        "loss_risk",
                        "complexity",
                        "time_risk",
                        "social_risk",
                        "compliance_or_safety",
                        "unknown",
                    ],
                },
                "customer_meaning_reference": {"type": "string"},
                "underlying_concern": {"type": "string"},
                "proof_requirement_reference": {"type": "string"},
                "response_constraint": {"type": "string"},
                "unresolved_risk": {"type": "string"},
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "provenance": {"type": "object"},
            },
            [
                "map_id",
                "fear_category",
                "customer_meaning_reference",
                "underlying_concern",
                "proof_requirement_reference",
                "response_constraint",
                "unresolved_risk",
                "provenance",
            ],
        ),
    ]:
        write_json(
            root / f"schemas/{fname}",
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": f"{sid}/schemas/{fname}",
                "title": title,
                "type": "object",
                "additionalProperties": False,
                "properties": props,
                "required": req,
            },
        )
    write_json(
        root / "schemas/input.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/input/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "source_cim_reference": {"type": "object"},
                "source_evidence_references": {"type": "array", "items": {"type": "string"}},
                "selected_segment_ids": {"type": "array", "items": {"type": "string"}},
                "cim_claim_catalog": {"type": "object"},
            },
            "required": ["source_cim_reference", "selected_segment_ids"],
        },
    )
    write_json(
        root / "schemas/output.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/output/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "extraction_id": {"type": "string"},
                "skill_id": {"type": "string", "const": sid},
                "skill_version": {"type": "string"},
                "source_cim_reference": {"type": "object"},
                "source_evidence_references": {"type": "array", "items": {"type": "string"}},
                "customer_meanings": {
                    "type": "array",
                    "items": {"$ref": "schemas/customer-meaning.schema.json"},
                },
                "desire_to_benefit_maps": {
                    "type": "array",
                    "items": {"$ref": "schemas/desire-to-benefit-map.schema.json"},
                },
                "transformation_maps": {"type": "array", "items": {"type": "object"}},
                "fear_objection_maps": {
                    "type": "array",
                    "items": {"$ref": "schemas/fear-objection-map.schema.json"},
                },
                "trust_requirements": {"type": "array", "items": {"type": "object"}},
                "service_expectations": {"type": "array", "items": {"type": "object"}},
                "price_value_concerns": {"type": "array", "items": {"type": "object"}},
                "promise_candidates": {"type": "array", "items": {"type": "object"}},
                "unsupported_promises": {"type": "array", "items": {"type": "object"}},
                "assumptions": {"type": "array", "items": {"type": "object"}},
                "inferences": {"type": "array", "items": {"type": "object"}},
                "unknowns": {"type": "array", "items": {"type": "object"}},
                "conflicts": {"type": "array", "items": {"type": "object"}},
                **RESEARCH_FIELDS,
                "downstream_positioning_inputs": {"type": "array", "items": {"type": "object"}},
                "downstream_claim_substantiation_inputs": {"type": "array", "items": {"type": "object"}},
                "downstream_offer_inputs": {"type": "array", "items": {"type": "object"}},
                "provenance": {"type": "object"},
                "input_hash": {"type": "string", "minLength": 64, "maxLength": 64},
                "output_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            },
            "required": [
                "extraction_id",
                "skill_id",
                "skill_version",
                "source_cim_reference",
                "customer_meanings",
                "desire_to_benefit_maps",
                "fear_objection_maps",
                "promise_candidates",
                "unsupported_promises",
                *RESEARCH_REQUIRED,
                "provenance",
                "input_hash",
                "output_hash",
            ],
        },
    )
    meaning = {
        "meaning_id": "mean-desire-1",
        "selected_segment_ids": [SEG],
        "source_statement": "We lose hours in sync meetings",
        "normalized_meaning": "Reduce time lost to synchronous coordination",
        "meaning_type": "desire",
        "customer_language": "too many meetings",
        "desired_transformation": "More async, fewer meetings",
        "underlying_need": "Protect deep work time",
        "evidence_references": ["ev-interview-001"],
        "contradictory_evidence": [],
        "assumptions": [],
        "inference": "",
        "confidence": "medium",
        "unknowns": [],
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
    }
    dtb = {
        "map_id": "dtb-1",
        "customer_meaning_reference": "mean-desire-1",
        "satisfaction_status": "partially_supported",
        "product_capability_reference": "cap-async-workflows",
        "delivery_mechanism_reference": "mech-async-handoff",
        "benefit_statement": "Fewer status meetings via async handoffs",
        "evidence_references": ["ev-cap-001"],
        "conditions": ["Team adopts async norms"],
        "limitations": ["Does not eliminate all meetings"],
        "unsupported_aspects": ["Exact hour savings unverified"],
        "confidence": "medium",
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
    }
    output_ok = {
        "extraction_id": "cme-001",
        "skill_id": sid,
        "skill_version": "0.1.0",
        "source_cim_reference": cim_ref(sid),
        "source_evidence_references": ["ev-interview-001"],
        "customer_meanings": [meaning],
        "desire_to_benefit_maps": [dtb],
        "transformation_maps": [],
        "fear_objection_maps": [
            {
                "map_id": "fom-1",
                "fear_category": "category_distrust",
                "customer_meaning_reference": "mean-desire-1",
                "underlying_concern": "Async tools failed before",
                "proof_requirement_reference": "proof-pilot",
                "response_constraint": "No invented counter-proof",
                "unresolved_risk": "Adoption risk remains",
                "evidence_references": ["ev-interview-001"],
                "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
            }
        ],
        "trust_requirements": [],
        "service_expectations": [],
        "price_value_concerns": [],
        "promise_candidates": [
            {
                "promise_id": "pc-1",
                "proposed_statement": "Reduce meeting load with async workflows",
                "substantiation_status": "partially_supported",
            }
        ],
        "unsupported_promises": [
            {"finding_id": "up-1", "statement": "Guaranteed 50% fewer meetings", "reason": "No verified evidence"}
        ],
        "assumptions": [],
        "inferences": [],
        "unknowns": [],
        "conflicts": [],
        **research_fixture_defaults(),
        "evidence_gaps": ["Quantified time savings"],
        "downstream_positioning_inputs": [],
        "downstream_claim_substantiation_inputs": [],
        "downstream_offer_inputs": [],
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
        "input_hash": "3" * 64,
        "output_hash": "4" * 64,
    }
    output_bad = dict(output_ok)
    output_bad["extraction_id"] = "cme-auto-capability"
    output_bad["desire_to_benefit_maps"] = [
        dict(dtb, satisfaction_status="supported", evidence_references=[])
    ]
    write_json(root / "tests/fixtures/output_valid_extraction.json", output_ok)
    write_json(root / "tests/fixtures/output_unsupported_as_supported.json", output_bad)
    write(
        root / "tests/eval_manifest.yaml",
        eval_manifest(sid, [("valid", "tests/fixtures/output_valid_extraction.json")]),
    )


def build_claim_substantiation() -> None:
    root = SKILLS / "ms.skill.claim_substantiation"
    sid = "ms.skill.claim_substantiation"
    write(
        root / "manifest.yaml",
        manifest_block(
            sid,
            "Claim Substantiation",
            "Evaluate marketing claims and promise candidates for evidence support, "
            "limitations and compliance before Offer Builder.",
            [
                "claim_inventory_normalization",
                "claim_evidence_matching",
                "prohibited_claim_detection",
                "financial_claim_risk_detection",
                "safety_claim_risk_detection",
                "proof_gap_detection",
                "substantiation_readiness_assessment",
            ],
            [
                ("ms.skill.customer_meaning_extraction", "required_dependency", ">=0.1.0,<1.0.0"),
                ("ms.skill.positioning", "required_dependency", ">=0.1.0,<1.0.0"),
                ("ms.skill.market_validation", "required_dependency", ">=0.2.0,<1.0.0"),
            ],
        ),
    )
    write(
        root / "SKILL.md",
        skill_md(
            sid,
            "Claim Substantiation",
            "Hard gate between promise generation and customer-facing communication. "
            "Rejects guaranteed income and 100% safety without evidence.",
        ),
    )
    write_json(
        root / "schemas/claim-assessment.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/schemas/claim-assessment.schema.json",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "claim_id": {"type": "string"},
                "original_statement": {"type": "string"},
                "normalized_claim": {"type": "string"},
                "substantiation_status": {
                    "type": "string",
                    "enum": [
                        "supported",
                        "supported_with_conditions",
                        "partially_supported",
                        "unsupported",
                        "prohibited",
                        "requires_legal_review",
                        "insufficient_evidence",
                        "conflicted",
                    ],
                },
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "contradictory_evidence": {"type": "array", "items": {"type": "string"}},
                "mechanism_reference": {"type": "string"},
                "proof_requirements": {"type": "array", "items": {"type": "string"}},
                "limitations": {"type": "array", "items": {"type": "string"}},
                "required_qualifiers": {"type": "array", "items": {"type": "string"}},
                "prohibited_phrases": {"type": "array", "items": {"type": "string"}},
                "permitted_rewrite": {"type": "string"},
                "residual_risk": {"type": "string"},
                "human_review_required": {"type": "boolean"},
                "legal_review_required": {"type": "boolean"},
                "provenance": {"type": "object"},
            },
            "required": [
                "claim_id",
                "original_statement",
                "normalized_claim",
                "substantiation_status",
                "evidence_references",
                "limitations",
                "human_review_required",
                "legal_review_required",
                "provenance",
            ],
        },
    )
    write_json(
        root / "schemas/input.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/input/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "source_positioning_reference": {"type": "object"},
                "source_meaning_reference": {"type": "object"},
                "source_market_validation_reference": {"type": "object"},
                "claim_inventory": {"type": "array", "items": {"type": "object"}},
                "market_validation_verdict": {"type": "string"},
            },
            "required": [
                "source_positioning_reference",
                "source_meaning_reference",
                "source_market_validation_reference",
                "claim_inventory",
                "market_validation_verdict",
            ],
        },
    )
    write_json(
        root / "schemas/output.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/output/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "substantiation_report_id": {"type": "string"},
                "skill_id": {"type": "string", "const": sid},
                "skill_version": {"type": "string"},
                "source_positioning_reference": {"type": "object"},
                "source_meaning_reference": {"type": "object"},
                "source_market_validation_reference": {"type": "object"},
                "claim_assessments": {
                    "type": "array",
                    "items": {"$ref": "schemas/claim-assessment.schema.json"},
                },
                "supported_claims": {"type": "array", "items": {"type": "string"}},
                "conditional_claims": {"type": "array", "items": {"type": "string"}},
                "unsupported_claims": {"type": "array", "items": {"type": "string"}},
                "prohibited_claims": {"type": "array", "items": {"type": "string"}},
                "proof_gaps": {"type": "array", "items": {"type": "string"}},
                "legal_review_items": {"type": "array", "items": {"type": "string"}},
                "required_qualifiers": {"type": "array", "items": {"type": "string"}},
                "risk_reversal_candidates": {"type": "array", "items": {"type": "object"}},
                **RESEARCH_FIELDS,
                "offer_builder_claim_inputs": {"type": "array", "items": {"type": "object"}},
                "human_review_required": {"type": "boolean"},
                "provenance": {"type": "object"},
                "input_hash": {"type": "string", "minLength": 64, "maxLength": 64},
                "output_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            },
            "required": [
                "substantiation_report_id",
                "skill_id",
                "skill_version",
                "claim_assessments",
                "supported_claims",
                "unsupported_claims",
                "prohibited_claims",
                "offer_builder_claim_inputs",
                *RESEARCH_REQUIRED,
                "human_review_required",
                "provenance",
                "input_hash",
                "output_hash",
            ],
        },
    )
    assessment_supported = {
        "claim_id": "claim-async-1",
        "original_statement": "Async workflows can reduce meeting load",
        "normalized_claim": "Async workflows may reduce meeting load for adopting teams",
        "substantiation_status": "supported_with_conditions",
        "evidence_references": ["ev-cap-001", "ev-case-001"],
        "contradictory_evidence": [],
        "mechanism_reference": "mech-async-handoff",
        "proof_requirements": ["pilot_results"],
        "limitations": ["Requires team adoption"],
        "required_qualifiers": ["for teams that adopt async norms"],
        "prohibited_phrases": [],
        "permitted_rewrite": "Teams adopting async workflows report fewer status meetings",
        "residual_risk": "medium",
        "human_review_required": True,
        "legal_review_required": False,
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
    }
    assessment_prohibited = {
        "claim_id": "claim-income-bad",
        "original_statement": "100% guaranteed income within 30 days",
        "normalized_claim": "Guaranteed income outcome",
        "substantiation_status": "prohibited",
        "evidence_references": [],
        "contradictory_evidence": [],
        "mechanism_reference": "",
        "proof_requirements": [],
        "limitations": ["Financial outcome guarantee prohibited"],
        "required_qualifiers": [],
        "prohibited_phrases": ["100% guaranteed income"],
        "permitted_rewrite": "",
        "residual_risk": "critical",
        "human_review_required": True,
        "legal_review_required": True,
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
    }
    output_ok = {
        "substantiation_report_id": "cs-001",
        "skill_id": sid,
        "skill_version": "0.1.0",
        "source_positioning_reference": upstream_ref("ms.skill.positioning", "0.1.0", POS_HASH),
        "source_meaning_reference": upstream_ref("ms.skill.customer_meaning_extraction", "0.1.0", "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"),
        "source_market_validation_reference": upstream_ref("ms.skill.market_validation", "0.2.0", MV_HASH),
        "claim_assessments": [assessment_supported, assessment_prohibited],
        "supported_claims": ["claim-async-1"],
        "conditional_claims": ["claim-async-1"],
        "unsupported_claims": [],
        "prohibited_claims": ["claim-income-bad"],
        "proof_gaps": [],
        "legal_review_items": ["claim-income-bad"],
        "required_qualifiers": ["for teams that adopt async norms"],
        "risk_reversal_candidates": [
            {
                "risk_reversal_id": "rr-refund-1",
                "reversal_type": "refund",
                "description": "30-day refund if onboarding incomplete",
                "reduces_commercial_risk": True,
                "proves_outcome": False,
            }
        ],
        "evidence_gaps": [],
        **research_fixture_defaults(),
        "offer_builder_claim_inputs": [
            {"claim_id": "claim-async-1", "substantiation_status": "supported_with_conditions"}
        ],
        "human_review_required": True,
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
        "input_hash": "5" * 64,
        "output_hash": "6" * 64,
    }
    write_json(root / "tests/fixtures/output_valid_substantiation.json", output_ok)
    write_json(
        root / "tests/fixtures/output_safety_prohibited.json",
        {
            **output_ok,
            "substantiation_report_id": "cs-safety-bad",
            "claim_assessments": [
                {
                    **assessment_prohibited,
                    "claim_id": "claim-safety-bad",
                    "original_statement": "100% safety — technology cannot fail",
                    "substantiation_status": "prohibited",
                    "prohibited_phrases": ["100% safety", "technology cannot fail"],
                }
            ],
            "prohibited_claims": ["claim-safety-bad"],
        },
    )
    write(
        root / "tests/eval_manifest.yaml",
        eval_manifest(sid, [("valid", "tests/fixtures/output_valid_substantiation.json")]),
    )


def build_offer_builder() -> None:
    root = SKILLS / "ms.skill.offer_builder"
    sid = "ms.skill.offer_builder"
    write(
        root / "manifest.yaml",
        manifest_block(
            sid,
            "Offer Builder",
            "Transform substantiated claims and positioning into structured offer "
            "candidates without campaigns, publication or launch authorization.",
            [
                "offer_candidate_generation",
                "delivery_mechanism_structuring",
                "price_justification_mapping",
                "risk_reversal_planning",
                "offer_readiness_assessment",
            ],
            [
                ("ms.skill.icp_segmentation", "required_dependency", "CIM >=0.1.0,<1.0.0"),
                ("ms.skill.positioning", "required_dependency", ">=0.1.0,<1.0.0"),
                ("ms.skill.market_validation", "required_dependency", ">=0.2.0,<1.0.0"),
                ("ms.skill.customer_meaning_extraction", "required_dependency", ">=0.1.0,<1.0.0"),
                ("ms.skill.claim_substantiation", "required_dependency", ">=0.1.0,<1.0.0"),
            ],
        ),
    )
    write(
        root / "SKILL.md",
        skill_md(
            sid,
            "Offer Builder",
            "Produce structured offer candidates using only substantiated claims. "
            "MV stop blocks preferred offer; defer allows exploratory only.",
        ),
    )
    write_json(
        root / "schemas/delivery_mechanism.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/schemas/delivery_mechanism.schema.json",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "mechanism_id": {"type": "string"},
                "mechanism_name": {"type": "string"},
                "plain_language_explanation": {"type": "string"},
                "process_steps": {"type": "array", "items": {"type": "string"}},
                "expected_intermediate_outcomes": {"type": "array", "items": {"type": "string"}},
                "capability_references": {"type": "array", "items": {"type": "string"}},
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "customer_effort": {"type": "string"},
                "provider_effort": {"type": "string"},
                "limitations": {"type": "array", "items": {"type": "string"}},
                "failure_modes": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string"},
                "provenance": {"type": "object"},
            },
            "required": [
                "mechanism_id",
                "mechanism_name",
                "plain_language_explanation",
                "process_steps",
                "capability_references",
                "evidence_references",
                "limitations",
                "confidence",
                "provenance",
            ],
        },
    )
    write_json(
        root / "schemas/offer_candidate.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/schemas/offer_candidate.schema.json",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "offer_id": {"type": "string"},
                "offer_name": {"type": "string"},
                "selected_segment_ids": {"type": "array", "items": {"type": "string"}},
                "positioning_hypothesis_id": {"type": "string"},
                "primary_customer_problem": {"type": "string"},
                "desired_outcome": {"type": "string"},
                "offer_promise": {"type": "string"},
                "claim_references": {"type": "array", "items": {"type": "string"}},
                "delivery_mechanism": {"$ref": "delivery_mechanism.schema.json"},
                "delivery_steps": {"type": "array", "items": {"type": "string"}},
                "intermediate_outcomes": {"type": "array", "items": {"type": "string"}},
                "time_to_value": {"type": "object"},
                "product_components": {"type": "array", "items": {"type": "string"}},
                "service_components": {"type": "array", "items": {"type": "string"}},
                "proof_elements": {"type": "array", "items": {"type": "string"}},
                "proof_requirements": {"type": "array", "items": {"type": "string"}},
                "trust_elements": {"type": "array", "items": {"type": "string"}},
                "objection_responses": {"type": "array", "items": {"type": "object"}},
                "risk_reversal": {"type": "object"},
                "guarantee_proposal": {"type": "object"},
                "pricing_context": {"type": "object"},
                "price_justification": {"type": "array", "items": {"type": "object"}},
                "buying_conditions": {"type": "array", "items": {"type": "string"}},
                "customer_responsibilities": {"type": "array", "items": {"type": "string"}},
                "provider_responsibilities": {"type": "array", "items": {"type": "string"}},
                "eligibility_or_fit": {"type": "string"},
                "exclusions": {"type": "array", "items": {"type": "string"}},
                "limitations": {"type": "array", "items": {"type": "string"}},
                "bonuses": {"type": "array", "items": {"type": "string"}},
                "bundle_candidates": {"type": "array", "items": {"type": "object"}},
                "upsell_candidates": {"type": "array", "items": {"type": "object"}},
                "cross_sell_candidates": {"type": "array", "items": {"type": "object"}},
                "CTA_strategy": {"type": "string"},
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "inherited_conditions": {"type": "array", "items": {"type": "object"}},
                "inherited_blockers": {"type": "array", "items": {"type": "object"}},
                "assumptions": {"type": "array", "items": {"type": "object"}},
                "unknowns": {"type": "array", "items": {"type": "object"}},
                "risks": {"type": "array", "items": {"type": "object"}},
                "confidence": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": [
                        "preferred",
                        "viable_alternative",
                        "exploratory",
                        "blocked",
                        "insufficient_evidence",
                        "rejected",
                    ],
                },
                "provenance": {"type": "object"},
            },
            "required": [
                "offer_id",
                "offer_name",
                "selected_segment_ids",
                "positioning_hypothesis_id",
                "primary_customer_problem",
                "desired_outcome",
                "offer_promise",
                "claim_references",
                "delivery_mechanism",
                "limitations",
                "status",
                "provenance",
            ],
        },
    )
    write_json(
        root / "schemas/input.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/input/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "source_cim_reference": {"type": "object"},
                "source_positioning_reference": {"type": "object"},
                "source_market_validation_reference": {"type": "object"},
                "source_meaning_reference": {"type": "object"},
                "source_claim_substantiation_reference": {"type": "object"},
                "market_validation_verdict": {"type": "string"},
                "positioning_hypothesis_id": {"type": "string"},
                "substantiated_claim_ids": {"type": "array", "items": {"type": "string"}},
                "cim_claim_catalog": {"type": "object"},
                "inherited_conditions": {"type": "array", "items": {"type": "object"}},
                "inherited_blockers": {"type": "array", "items": {"type": "object"}},
            },
            "required": [
                "source_cim_reference",
                "source_positioning_reference",
                "source_market_validation_reference",
                "source_claim_substantiation_reference",
                "market_validation_verdict",
                "positioning_hypothesis_id",
                "substantiated_claim_ids",
            ],
        },
    )
    write_json(
        root / "schemas/output.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{sid}/output/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "offer_analysis_id": {"type": "string"},
                "skill_id": {"type": "string", "const": sid},
                "skill_version": {"type": "string"},
                "source_cim_reference": {"type": "object"},
                "source_positioning_reference": {"type": "object"},
                "source_market_validation_reference": {"type": "object"},
                "source_meaning_reference": {"type": "object"},
                "source_claim_substantiation_reference": {"type": "object"},
                "selected_segment_ids": {"type": "array", "items": {"type": "string"}},
                "offer_candidates": {
                    "type": "array",
                    "items": {"$ref": "schemas/offer_candidate.schema.json"},
                },
                "preferred_offer_id": {"type": "string"},
                "blocked_offer_ids": {"type": "array", "items": {"type": "string"}},
                "proof_plan": {"type": "array", "items": {"type": "object"}},
                "objection_handling_plan": {"type": "array", "items": {"type": "object"}},
                "risk_reversal_plan": {"type": "array", "items": {"type": "object"}},
                "pricing_justification": {"type": "array", "items": {"type": "object"}},
                "product_decomposition": {"type": "array", "items": {"type": "object"}},
                "service_advantages": {"type": "array", "items": {"type": "string"}},
                "bundle_strategy": {"type": "object"},
                "unsupported_claims_excluded": {"type": "array", "items": {"type": "string"}},
                "inherited_conditions": {"type": "array", "items": {"type": "object"}},
                "inherited_blockers": {"type": "array", "items": {"type": "object"}},
                **RESEARCH_FIELDS,
                "offer_readiness": {
                    "type": "string",
                    "enum": [
                        "ready_for_owner_review",
                        "partially_ready",
                        "exploratory_only",
                        "blocked",
                        "insufficient_evidence",
                        "conflicted",
                        "out_of_scope",
                    ],
                },
                "downstream_launch_inputs": {"type": "array", "items": {"type": "object"}},
                "downstream_copy_inputs": {"type": "array", "items": {"type": "object"}},
                "human_approval_required": {"type": "boolean"},
                "provenance": {"type": "object"},
                "input_hash": {"type": "string", "minLength": 64, "maxLength": 64},
                "output_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            },
            "required": [
                "offer_analysis_id",
                "skill_id",
                "skill_version",
                "source_cim_reference",
                "source_positioning_reference",
                "source_market_validation_reference",
                "source_claim_substantiation_reference",
                "selected_segment_ids",
                "offer_candidates",
                *RESEARCH_REQUIRED,
                "offer_readiness",
                "human_approval_required",
                "provenance",
                "input_hash",
                "output_hash",
            ],
        },
    )
    mechanism = {
        "mechanism_id": "mech-async-handoff",
        "mechanism_name": "Async workflow handoff",
        "plain_language_explanation": "Replace status meetings with structured async updates",
        "process_steps": ["Configure channels", "Run pilot sprint", "Measure meeting hours"],
        "expected_intermediate_outcomes": ["Pilot team reduces one recurring meeting"],
        "capability_references": ["cap-async-workflows"],
        "evidence_references": ["ev-cap-001"],
        "dependencies": ["Team lead sponsorship"],
        "customer_effort": "Medium — habit change required",
        "provider_effort": "Onboarding and templates",
        "limitations": ["Does not eliminate all meetings"],
        "failure_modes": ["Low adoption"],
        "assumptions": ["Leadership models async behavior"],
        "confidence": "medium",
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
    }
    offer = {
        "offer_id": "offer-async-001",
        "offer_name": "Async Team Pilot",
        "selected_segment_ids": [SEG],
        "positioning_hypothesis_id": "hyp-async-1",
        "primary_customer_problem": "Too many sync meetings",
        "desired_outcome": "More deep work time",
        "offer_promise": "Pilot async workflows to reduce status meetings",
        "claim_references": ["claim-async-1"],
        "delivery_mechanism": mechanism,
        "delivery_steps": mechanism["process_steps"],
        "intermediate_outcomes": mechanism["expected_intermediate_outcomes"],
        "time_to_value": {"horizon": "30 days", "is_assumption": True, "evidence_references": []},
        "product_components": ["Workflow templates"],
        "service_components": ["Onboarding workshop"],
        "proof_elements": ["Pilot case summary"],
        "proof_requirements": ["pilot_results"],
        "trust_elements": ["Transparent limitations"],
        "objection_responses": [],
        "risk_reversal": {
            "risk_reversal_id": "rr-refund-1",
            "reversal_type": "refund",
            "reduces_commercial_risk": True,
            "proves_outcome": False,
        },
        "guarantee_proposal": {
            "guarantee_id": "g-refund",
            "outcome_guarantee": False,
            "legal_review_required": True,
        },
        "pricing_context": {"model": "pilot_fee"},
        "price_justification": [
            {
                "justification_id": "pj-1",
                "justification_type": "faster_outcome",
                "statement": "Pilot surfaces meeting reduction within 30 days",
                "comparison_basis": "Status quo meeting load",
                "is_assumption": True,
            }
        ],
        "buying_conditions": ["Executive sponsor"],
        "customer_responsibilities": ["Adopt async norms"],
        "provider_responsibilities": ["Deliver onboarding"],
        "eligibility_or_fit": "Remote engineering teams 20-200 people",
        "exclusions": ["Guaranteed hour savings"],
        "limitations": ["Requires adoption"],
        "bonuses": [],
        "bundle_candidates": [],
        "upsell_candidates": [],
        "cross_sell_candidates": [],
        "CTA_strategy": "Book pilot scoping call",
        "evidence_references": ["ev-cap-001"],
        "inherited_conditions": [],
        "inherited_blockers": [],
        "assumptions": [],
        "unknowns": [],
        "risks": [],
        "confidence": "medium",
        "status": "preferred",
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
    }
    output_ok = {
        "offer_analysis_id": "ob-001",
        "skill_id": sid,
        "skill_version": "0.1.0",
        "source_cim_reference": cim_ref(sid),
        "source_positioning_reference": upstream_ref("ms.skill.positioning", "0.1.0", POS_HASH),
        "source_market_validation_reference": upstream_ref("ms.skill.market_validation", "0.2.0", MV_HASH),
        "source_meaning_reference": upstream_ref("ms.skill.customer_meaning_extraction", "0.1.0", "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"),
        "source_claim_substantiation_reference": upstream_ref("ms.skill.claim_substantiation", "0.1.0", "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"),
        "selected_segment_ids": [SEG],
        "offer_candidates": [offer],
        "preferred_offer_id": "offer-async-001",
        "blocked_offer_ids": [],
        "proof_plan": [],
        "objection_handling_plan": [],
        "risk_reversal_plan": [{"risk_reversal_id": "rr-refund-1"}],
        "pricing_justification": offer["price_justification"],
        "product_decomposition": [],
        "service_advantages": ["Dedicated onboarding"],
        "bundle_strategy": {},
        "unsupported_claims_excluded": ["claim-income-bad"],
        "inherited_conditions": [],
        "inherited_blockers": [],
        **research_fixture_defaults(),
        "offer_readiness": "ready_for_owner_review",
        "downstream_launch_inputs": [],
        "downstream_copy_inputs": [],
        "human_approval_required": True,
        "provenance": {"skill_id": sid, "skill_version": "0.1.0"},
        "input_hash": "7" * 64,
        "output_hash": "8" * 64,
    }
    output_mv_stop = dict(output_ok)
    output_mv_stop["offer_analysis_id"] = "ob-mv-stop"
    output_mv_stop["offer_candidates"] = [dict(offer, status="blocked", offer_id="offer-blocked-1")]
    output_mv_stop["preferred_offer_id"] = None
    output_mv_stop["blocked_offer_ids"] = ["offer-blocked-1"]
    output_mv_stop["offer_readiness"] = "blocked"
    output_mv_defer = dict(output_ok)
    output_mv_defer["offer_analysis_id"] = "ob-mv-defer"
    output_mv_defer["offer_candidates"] = [dict(offer, status="exploratory", offer_id="offer-explore-1")]
    output_mv_defer["preferred_offer_id"] = None
    output_mv_defer["offer_readiness"] = "exploratory_only"
    write_json(root / "tests/fixtures/output_proceed_preferred.json", output_ok)
    write_json(root / "tests/fixtures/output_mv_stop_blocked.json", output_mv_stop)
    write_json(root / "tests/fixtures/output_mv_defer_exploratory.json", output_mv_defer)
    write(
        root / "tests/eval_manifest.yaml",
        eval_manifest(
            sid,
            [
                ("proceed_preferred", "tests/fixtures/output_proceed_preferred.json"),
                ("mv_stop", "tests/fixtures/output_mv_stop_blocked.json"),
            ],
        ),
    )


def print_hashes() -> None:
    from app.skills.hashing import calculate_skill_package_hash

    for name in [
        "ms.skill.customer_interview_design",
        "ms.skill.customer_meaning_extraction",
        "ms.skill.claim_substantiation",
        "ms.skill.offer_builder",
    ]:
        h = calculate_skill_package_hash(SKILLS / name)
        print(f"{name}: {h}")


def main() -> None:
    build_customer_interview_design()
    build_customer_meaning_extraction()
    build_claim_substantiation()
    build_offer_builder()
    print_hashes()


if __name__ == "__main__":
    main()
