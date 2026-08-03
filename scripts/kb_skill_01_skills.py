#!/usr/bin/env python3
# ruff: noqa: E501
"""Generate KB-SKILL-01 native candidate packages."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "packages" / "skills"

RESEARCH_FIELDS = {
    "evidence_gaps": {"type": "array", "items": {"type": "string"}, "maxItems": 30},
    "coverage": {"type": "string", "enum": ["full", "partial", "minimal", "unknown"]},
    "evidence_quality": {
        "type": "string",
        "enum": ["comprehensive", "partial", "insufficient", "conflicted", "unknown"],
    },
    "research_status": {
        "type": "string",
        "enum": ["complete", "partially_complete", "insufficient_sources", "conflicted", "out_of_scope"],
    },
}
RESEARCH_REQ = ["evidence_gaps", "coverage", "evidence_quality", "research_status"]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def manifest(skill_id: str, name: str, desc: str, caps: list[str], deps: list[tuple[str, str]]) -> str:
    cap = "\n".join(f"  - {c}" for c in caps)
    dep = "\n".join(f'    - id: {d}\n      relationship: {r}\n      note: "KB-SKILL-01 adapted"' for d, r in deps)
    return f"""id: {skill_id}
name: {name}
version: 0.1.0
description: >
  {desc}
owner: Marketsynth Platform
source: platform_native
license: Proprietary
status: candidate
output_contract_type: research
capabilities:
{cap}
activation_conditions:
  runtime_compatibility:
    - operator_dry_run
    - assistant_explicit_run
  requires_governed_context: true
  executable: false
required_inputs:
  schema_ref: schemas/input.schema.json
output_schema:
  schema_ref: schemas/output.schema.json
required_evidence:
  classes:
    - user_statement
    - assumption
    - inference
  rules:
    - id: no_runtime_execution
      description: Non-executable candidate — no deployment or network.
dependencies:
  declared_future_dependencies:
{dep if dep else "    []"}
allowed_tools: []
approval_policy:
  analysis_preparation:
    external_side_effects: false
    approval_required: false
  deployment_or_publication:
    approval_required: true
tenant_scope: global
quality_threshold:
  eval_required_before_active: true
  minimum_eval_cases: 1
  current_state: skeleton_only
known_limitations:
  - Non-executable candidate — no runtime loader.
  - No workflow deployment or external network.
network_policy:
  default: deny
  allowed_hosts: []
script_policy:
  enabled: false
provenance:
  origin: platform_native
  methodology:
    - KB-SKILL-01 external archive adaptation
test_suite:
  manifest: tests/eval_manifest.yaml
"""


def minimal_io(skill_id: str, out_fields: dict, out_required: list[str]) -> None:
    root = SKILLS / skill_id
    write_json(
        root / "schemas/input.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{skill_id}/input/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "artifact_references": {"type": "array", "items": {"type": "string"}},
                "tenant_scope": {"type": "string"},
                "project_scope": {"type": "string"},
            },
            "required": ["artifact_references"],
        },
    )
    props = {
        "analysis_id": {"type": "string"},
        "skill_id": {"type": "string", "const": skill_id},
        "skill_version": {"type": "string"},
        **out_fields,
        **RESEARCH_FIELDS,
        "human_review_required": {"type": "boolean"},
        "provenance": {"type": "object"},
        "input_hash": {"type": "string", "minLength": 64, "maxLength": 64},
        "output_hash": {"type": "string", "minLength": 64, "maxLength": 64},
    }
    req = ["analysis_id", "skill_id", "skill_version", *out_required, *RESEARCH_REQ, "human_review_required", "provenance", "input_hash", "output_hash"]
    write_json(
        root / "schemas/output.schema.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{skill_id}/output/0.1.0",
            "type": "object",
            "additionalProperties": False,
            "properties": props,
            "required": req,
        },
    )


def fixture(skill_id: str, extra: dict) -> dict:
    base = {
        "skill_id": skill_id,
        "skill_version": "0.1.0",
        "evidence_gaps": [],
        "coverage": "partial",
        "evidence_quality": "partial",
        "research_status": "partially_complete",
        "human_review_required": True,
        "provenance": {"skill_id": skill_id, "skill_version": "0.1.0"},
        "input_hash": "a" * 64,
        "output_hash": "b" * 64,
    }
    base.update(extra)
    return base


def build_package(
    skill_id: str,
    name: str,
    desc: str,
    caps: list[str],
    deps: list[tuple[str, str]],
    out_fields: dict,
    out_required: list[str],
    fixture_extra: dict,
    fixture_name: str,
) -> None:
    root = SKILLS / skill_id
    write_text(root / "manifest.yaml", manifest(skill_id, name, desc, caps, deps))
    write_text(
        root / "SKILL.md",
        f"# {name}\n\n**Skill ID:** `{skill_id}` v0.1.0 candidate non-executable.\n\n{desc}\n",
    )
    minimal_io(skill_id, out_fields, out_required)
    write_json(root / f"tests/fixtures/{fixture_name}", fixture(skill_id, fixture_extra))
    write_text(
        root / "tests/eval_manifest.yaml",
        f"version: 1\nskill_id: {skill_id}\neval_cases:\n  - id: valid\n    fixture: tests/fixtures/{fixture_name}\n    expectation: schema_valid\n",
    )


def main() -> None:
    build_package(
        "ms.skill.n8n_workflow_architecture",
        "n8n Workflow Architecture",
        "Design n8n workflow architecture specs without deployment.",
        ["workflow_requirements_normalization", "node_boundary_design", "approval_boundary_design"],
        [],
        {
            "workflow_architecture_spec": {"type": "object"},
            "node_plan": {"type": "array", "items": {"type": "object"}},
            "credential_requirements": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
        },
        ["workflow_architecture_spec", "node_plan"],
        {"analysis_id": "n8n-arch-001", "workflow_architecture_spec": {}, "node_plan": [], "credential_requirements": [], "risks": []},
        "output_valid.json",
    )
    build_package(
        "ms.skill.n8n_workflow_debugging",
        "n8n Workflow Debugging",
        "Diagnostic reports for n8n failures without live mutation.",
        ["failure_localization", "sandbox_plan", "expression_type_diagnosis"],
        [("ms.skill.n8n_workflow_architecture", "optional_dependency")],
        {
            "diagnostic_report": {"type": "object"},
            "suspected_failure_node": {"type": "string"},
            "remediation_candidates": {"type": "array", "items": {"type": "string"}},
        },
        ["diagnostic_report"],
        {"analysis_id": "n8n-dbg-001", "diagnostic_report": {}, "suspected_failure_node": "node-1", "remediation_candidates": []},
        "output_valid.json",
    )
    build_package(
        "ms.skill.n8n_deployment_review",
        "n8n Deployment Review",
        "Review deployment readiness without PUT/POST to n8n.",
        ["deployment_readiness_review", "activation_safety_review", "rollback_plan_review"],
        [("ms.skill.n8n_workflow_architecture", "required_dependency")],
        {
            "deployment_review": {"type": "object"},
            "blockers": {"type": "array", "items": {"type": "string"}},
            "activation_gate": {"type": "string"},
        },
        ["deployment_review", "blockers"],
        {"analysis_id": "n8n-dep-001", "deployment_review": {}, "blockers": [], "activation_gate": "blocked"},
        "output_valid.json",
    )
    build_package(
        "ms.skill.knowledge_linking",
        "Knowledge Linking",
        "Propose deterministic links between knowledge artifacts — no filesystem edits.",
        ["orphan_detection", "link_proposal", "broken_link_detection"],
        [],
        {
            "proposed_links": {"type": "array", "items": {"type": "object"}},
            "broken_links": {"type": "array", "items": {"type": "object"}},
            "orphan_artifacts": {"type": "array", "items": {"type": "string"}},
        },
        ["proposed_links", "orphan_artifacts"],
        {"analysis_id": "kl-001", "proposed_links": [], "broken_links": [], "orphan_artifacts": []},
        "output_valid.json",
    )
    build_package(
        "ms.skill.presentation_architecture",
        "Presentation Architecture",
        "Structured presentation specs — no Marp execution.",
        ["slide_plan_generation", "theme_recommendation", "narrative_arc_design"],
        [],
        {
            "presentation_id": {"type": "string"},
            "objective": {"type": "string"},
            "slide_plan": {"type": "array", "items": {"type": "object"}},
            "theme_recommendation": {"type": "string"},
        },
        ["presentation_id", "slide_plan", "theme_recommendation"],
        {
            "analysis_id": "pres-001",
            "presentation_id": "pres-001",
            "objective": "Owner review deck",
            "slide_plan": [{"slide_id": "s1", "title": "Context"}],
            "theme_recommendation": "business",
        },
        "output_valid.json",
    )
    from app.skills.hashing import calculate_skill_package_hash

    for sid in [
        "ms.skill.n8n_workflow_architecture",
        "ms.skill.n8n_workflow_debugging",
        "ms.skill.n8n_deployment_review",
        "ms.skill.knowledge_linking",
        "ms.skill.presentation_architecture",
    ]:
        print(sid, calculate_skill_package_hash(SKILLS / sid))


if __name__ == "__main__":
    main()
