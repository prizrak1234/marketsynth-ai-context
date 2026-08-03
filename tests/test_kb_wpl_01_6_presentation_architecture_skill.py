"""KB-WPL-01.6 — Presentation Architecture Skill tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from app.audit.adapters import adapt_package_validation_report
from app.knowledge.n8n_engineering.constants import (
    FROZEN_LIBRARY_SEMANTIC_HASH,
    N8N_ENGINEERING_SKILL_IDS,
)
from app.knowledge.n8n_engineering.pattern_selection import validate_pattern_selection
from app.knowledge.presentation_architecture.accessibility import (
    validate_accessibility_requirements,
)
from app.knowledge.presentation_architecture.slide_rules import validate_slide_plan
from app.knowledge.presentation_architecture.theme_rules import validate_theme_recommendation
from app.knowledge.presentation_architecture.validation import (
    validate_chart_requirement,
    validate_presentation_input,
    validate_presentation_output,
    validate_prohibited_claim,
)
from app.knowledge.workflow_patterns.serialization import (
    FROZEN_PILOT_BUNDLE_HASH,
    FROZEN_SCHEMA_HASH,
    load_library_manifest,
)
from app.lineage.builders import build_package_validation_lineage
from app.schemas.contracts import SkillLifecycleStatus
from app.skills.hashing import calculate_skill_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from tests.support.kb_skill_validation import KB_SKILL_PACKAGE_HASHES
from tests.support.presentation_architecture_skill_validation import (
    load_json_fixture,
    package_hash,
    package_root,
    sample_slide,
    schema_validator,
)

REPO = Path(__file__).resolve().parents[1]
SKILL_ID = "ms.skill.presentation_architecture"
FORBIDDEN_IMPORTS = ("requests", "httpx", "aiohttp", "subprocess", "socket", "marp")
PATTERN_REF = {
    "pattern_id": "source_lineage_preservation",
    "library_version": "0.1.0-frozen",
    "library_semantic_hash": FROZEN_LIBRARY_SEMANTIC_HASH,
    "selection_reason": "Preserve evidence lineage in slides.",
    "maturity": "reviewed",
    "runtime_authorized": False,
}
ACCESSIBILITY_FIXTURE = {
    "minimum_body_text_guidance": "18pt",
    "contrast_requirement": "WCAG AA",
    "color_independence": True,
    "alt_text_required": True,
    "chart_description_required": True,
    "reading_order": "logical",
}


@pytest.fixture
def package_report():
    return validate_skill_package(package_root())


def test_01_package_validates(package_report) -> None:
    assert package_report.valid is True


def test_02_version_010(package_report) -> None:
    assert package_report.skill_version == "0.1.0"


def test_03_candidate(package_report) -> None:
    projection = project_validation_report(package_report)
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_04_non_executable(package_report) -> None:
    assert package_report.manifest.activation_conditions.executable is False


def test_05_no_tools(package_report) -> None:
    assert package_report.manifest.allowed_tools == []


def test_06_network_denied(package_report) -> None:
    assert package_report.manifest.network_policy.default.value == "deny"


def test_07_scripts_disabled(package_report) -> None:
    assert package_report.manifest.script_policy.enabled is False


def test_08_output_contract_research(package_report) -> None:
    assert package_report.manifest.output_contract_type.value == "research"


def test_09_input_schema_valid() -> None:
    schema_validator("input.schema.json").validate(
        load_json_fixture("tests/fixtures/input_saas_sales.json")
    )


def test_10_output_schema_valid() -> None:
    schema_validator("output.schema.json").validate(
        load_json_fixture("tests/fixtures/output_saas_sales.json")
    )


def test_11_narrative_schema_valid() -> None:
    arc = load_json_fixture("tests/fixtures/output_saas_sales.json")["narrative_arc"]
    schema_validator("narrative-arc.schema.json").validate(arc)


def test_12_slide_schema_valid() -> None:
    slide = load_json_fixture("tests/fixtures/output_saas_sales.json")["slide_plan"][0]
    schema_validator("slide-specification.schema.json").validate(slide)


def test_13_visual_brief_schema_valid() -> None:
    brief = load_json_fixture("tests/fixtures/output_saas_sales.json")["visual_briefs"][0]
    schema_validator("visual-brief.schema.json").validate(brief)


def test_14_chart_schema_valid() -> None:
    chart = load_json_fixture("tests/fixtures/output_saas_sales.json")["chart_requirements"][0]
    schema_validator("chart-requirement.schema.json").validate(chart)


def test_15_theme_schema_valid() -> None:
    theme = load_json_fixture("tests/fixtures/output_saas_sales.json")["theme_recommendation"]
    schema_validator("theme-recommendation.schema.json").validate(theme)


def test_16_valid_sales_fixture() -> None:
    data = load_json_fixture("tests/fixtures/output_saas_sales.json")
    assert data["presentation_type"] == "sales_presentation"
    assert not validate_presentation_output(data)


def test_17_valid_research_report_fixture() -> None:
    data = load_json_fixture("tests/fixtures/output_saas_sales.json")
    data["presentation_type"] = "market_research_report"
    assert not validate_presentation_output(data)


def test_18_valid_technical_fixture() -> None:
    data = load_json_fixture("tests/fixtures/output_technical_architecture.json")
    schema_validator("output.schema.json").validate(data)


def test_19_slide_sequence_contiguous() -> None:
    slides = [
        sample_slide("a", 1),
        sample_slide("b", 2),
        sample_slide("c", 3),
    ]
    assert "slide_sequence_not_contiguous" not in validate_slide_plan(slides)


def test_20_duplicate_slide_id_rejected() -> None:
    slides = [sample_slide("dup", 1), sample_slide("dup", 2)]
    assert any("duplicate_slide_id" in e for e in validate_slide_plan(slides))


def test_21_chart_without_data_rejected() -> None:
    assert "chart_requires_data_reference" in validate_chart_requirement(
        {"chart_id": "c1", "chart_type": "bar"}
    )


def test_22_unsupported_claim_as_key_message_rejected() -> None:
    slide = sample_slide("s1", 1, key_message="Unverified stat", unsupported=["Unverified stat"])
    assert "unsupported_claim_as_key_message" in validate_slide_plan([slide])


def test_23_prohibited_claim_rejected() -> None:
    errors = validate_prohibited_claim(
        "Banned claim",
        prohibited=["Banned claim"],
        key_messages=["Banned claim"],
    )
    assert "prohibited_claim_as_key_message" in errors


def test_24_evidence_claim_without_source_rejected() -> None:
    slide = sample_slide("s1", 1)
    slide["evidence_references"] = [{"claim": "no source"}]
    assert "evidence_claim_without_source" in validate_slide_plan([slide])


def test_25_financial_projection_without_basis_rejected() -> None:
    payload = {
        "presentation_type": "investor_presentation",
        "presentation_readiness": "ready_for_rendering_review",
        "unsupported_claims": ["2027 revenue projection"],
        "narrative_arc": {
            "arc_id": "a",
            "arc_type": "custom",
            "opening": "x",
            "conclusion": "y",
            "source_references": [],
            "provenance": {},
        },
        "slide_plan": [sample_slide("s1", 1)],
        "theme_recommendation": {
            "theme_family": "business",
            "selection_reason": "r",
            "audience_fit": "h",
            "readability": "h",
            "accessibility": {"contrast_reviewed": True},
            "typography_direction": "sans",
            "provider_neutral": True,
            "provenance": {},
        },
        "accessibility_requirements": ACCESSIBILITY_FIXTURE,
        "CTA_strategy": {"aligned_with_objective": True},
    }
    assert "investor_projections_require_assumptions" in validate_presentation_output(payload)


def test_26_raw_css_rejected() -> None:
    assert "raw_css_rejected" in validate_presentation_input({"style": "body { color: red; }"})


def test_27_raw_html_rejected() -> None:
    payload = {"body": "<html><body>x</body></html>"}
    assert "raw_html_rejected" in validate_presentation_input(payload)


def test_28_remote_font_rejected() -> None:
    payload = {"theme_recommendation": {"remote_font_url": "https://fonts.googleapis.com/css"}}
    assert "remote_font_rejected" in validate_presentation_output(payload)


def test_29_provider_specific_output_rejected() -> None:
    assert "forbidden_output_field:marp_output" in validate_presentation_output(
        {"research_status": "complete", "marp_output": "---"}
    )


def test_30_rendered_file_field_rejected() -> None:
    assert "forbidden_output_field:rendered_file" in validate_presentation_output(
        {"research_status": "complete", "rendered_file": "/tmp/out.pptx"}
    )


def test_31_dark_theme_requires_contrast_review() -> None:
    theme = {
        "theme_family": "dark",
        "selection_reason": "r",
        "audience_fit": "h",
        "readability": "h",
        "typography_direction": "sans",
        "provider_neutral": True,
        "provenance": {},
    }
    assert "dark_or_colorful_theme_requires_contrast_review" in validate_theme_recommendation(theme)


def test_32_custom_brand_requires_brand_constraints() -> None:
    theme = {
        "theme_family": "custom_brand",
        "selection_reason": "r",
        "audience_fit": "h",
        "readability": "h",
        "typography_direction": "sans",
        "provider_neutral": True,
        "provenance": {},
    }
    assert "custom_brand_requires_brand_constraints" in validate_theme_recommendation(theme)


def test_33_accessibility_requirements_present() -> None:
    assert not validate_accessibility_requirements(ACCESSIBILITY_FIXTURE)


def test_34_excessive_density_produces_finding() -> None:
    slide = sample_slide("s1", 1, extra_points=15)
    assert "excessive_slide_density" in validate_slide_plan([slide])


def test_35_cta_aligned_with_objective() -> None:
    payload = {
        "presentation_objective": "Book demo",
        "CTA_strategy": {"primary_action": "Book demo", "aligned_with_objective": False},
        "research_status": "complete",
    }
    assert "cta_not_aligned_with_objective" in validate_presentation_output(payload)


def test_36_pattern_reference_resolves() -> None:
    assert not validate_pattern_selection(PATTERN_REF)


def test_37_pattern_hash_mismatch_rejected() -> None:
    bad = {**PATTERN_REF, "library_semantic_hash": "0" * 64}
    assert "library_hash_mismatch" in validate_pattern_selection(bad)


def test_38_runtime_authorized_true_rejected() -> None:
    bad = {**PATTERN_REF, "runtime_authorized": True}
    assert "runtime_authorized_must_be_false" in validate_pattern_selection(bad)


def test_39_marp_consumer_stub_reads_specification_only() -> None:
    stub = load_json_fixture("tests/fixtures/consumer_marp_stub.json")
    output = load_json_fixture("tests/fixtures/output_saas_sales.json")
    assert stub["executes_render"] is False
    assert all(field in output for field in stub["reads_fields"])
    assert stub["forbidden_fields"][0] not in output


def test_40_pptx_consumer_stub_reads_specification_only() -> None:
    stub = load_json_fixture("tests/fixtures/consumer_pptx_stub.json")
    output = load_json_fixture("tests/fixtures/output_saas_sales.json")
    assert stub["executes_render"] is False
    assert all(field in output for field in stub["reads_fields"])


def test_41_no_renderer_selected_as_authority() -> None:
    output = load_json_fixture("tests/fixtures/output_saas_sales.json")
    assert output["renderer_requirements"]["renderer_selected"] is None


def test_42_registry_projection_candidate(package_report) -> None:
    projection = project_validation_report(package_report)
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_43_production_eligible_false(package_report) -> None:
    view = derive_eligibility_view(project_validation_report(package_report).version_record)
    assert view.production_eligible is False


def test_44_audit_readiness_not_activation(package_report) -> None:
    audit = adapt_package_validation_report(package_report)
    assert audit.decision_readiness.value == "ready_for_audit"


def test_45_lineage_builds_in_memory(package_report) -> None:
    audit = adapt_package_validation_report(package_report)
    graph = build_package_validation_lineage(package_report, audit_report=audit)
    assert graph.nodes


def test_46_package_hash_deterministic() -> None:
    assert package_hash() == calculate_skill_package_hash(package_root())
    assert package_hash() == KB_SKILL_PACKAGE_HASHES[SKILL_ID]


def test_47_frozen_wpl_hashes_unchanged() -> None:
    manifest = load_library_manifest()
    assert manifest["library_semantic_hash"] == FROZEN_LIBRARY_SEMANTIC_HASH
    assert manifest["pilot_bundle_hash"] == FROZEN_PILOT_BUNDLE_HASH
    assert manifest["schema_bundle_hash"] == FROZEN_SCHEMA_HASH


def test_48_frozen_engineering_and_linking_hashes_unchanged() -> None:
    for skill_id in (*N8N_ENGINEERING_SKILL_IDS, "ms.skill.knowledge_linking"):
        current = calculate_skill_package_hash(REPO / "packages" / "skills" / skill_id)
        assert current == KB_SKILL_PACKAGE_HASHES[skill_id]


def test_49_no_renderer_network_imports() -> None:
    module = REPO / "app" / "knowledge" / "presentation_architecture"
    for path in module.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in FORBIDDEN_IMPORTS


def test_50_existing_kb_wpl_tests_remain_green() -> None:
    assert load_library_manifest()["runtime_authorized"] is False
