"""Phase V2.1 characterization — additive Architecture contracts only.

These tests lock contract vocabulary without exercising runtime APIs.
"""

from __future__ import annotations

from app.schemas.contracts import (
    ARCHITECTURE_V2_1_ACTIVE_PHASE,
    ARCHITECTURE_V2_1_COMPATIBILITY_MAPPINGS,
    AiQualityGate,
    ApprovalState,
    ArchitectureV2Phase,
    EvidenceState,
    ExecutionLifecycleState,
    MarketsynthCompatibilityMapping,
    ProviderKind,
    ReasoningArtifactKind,
    ToolLayerKind,
    VerdictKind,
    VerificationStatus,
)


def test_v2_1_active_phase_is_contracts_only() -> None:
    assert ARCHITECTURE_V2_1_ACTIVE_PHASE is ArchitectureV2Phase.V2_1_CONTRACTS


def test_verification_status_includes_limited_and_failed() -> None:
    assert VerificationStatus.VERIFIED.value == "verified"
    assert VerificationStatus.VERIFICATION_LIMITED.value == "verification_limited"
    assert VerificationStatus.FAILED.value == "failed"


def test_verdict_includes_insufficient_data_abstention() -> None:
    assert VerdictKind.INSUFFICIENT_DATA.value == "insufficient_data"
    assert set(VerdictKind) >= {
        VerdictKind.GO,
        VerdictKind.CONDITIONAL_GO,
        VerdictKind.NO_GO,
        VerdictKind.INSUFFICIENT_DATA,
    }


def test_reasoning_artifacts_exclude_chain_of_thought_label() -> None:
    values = {m.value for m in ReasoningArtifactKind}
    assert "chain_of_thought" not in values
    assert "hypothesis" in values
    assert "evidence" in values


def test_tool_layer_kind_split() -> None:
    assert ToolLayerKind.INTERNAL_CAPABILITY.value == "internal_capability"
    assert ToolLayerKind.BUSINESS_TOOL.value == "business_tool"


def test_ai_quality_gates_q0_through_q6() -> None:
    assert len(AiQualityGate) == 7
    assert AiQualityGate.Q0_INPUT.value == "q0_input"
    assert AiQualityGate.Q6_BUSINESS_VERDICT.value == "q6_business_verdict"


def test_semantic_state_enums_cover_brand_token_domains() -> None:
    assert EvidenceState.MISSING.value == "missing"
    assert ApprovalState.PENDING.value == "pending"
    assert ExecutionLifecycleState.VERIFYING.value == "verifying"
    assert ProviderKind.MOCK.value == "mock"


def test_compatibility_mappings_are_documented_and_typed() -> None:
    assert len(ARCHITECTURE_V2_1_COMPATIBILITY_MAPPINGS) >= 8
    for row in ARCHITECTURE_V2_1_COMPATIBILITY_MAPPINGS:
        assert isinstance(row, MarketsynthCompatibilityMapping)
        assert row.compatibility in {
            "compatible",
            "partially_compatible",
            "absent",
            "conflicting",
        }
    concepts = {row.marketsynth_concept for row in ARCHITECTURE_V2_1_COMPATIBILITY_MAPPINGS}
    assert "VerifiedExecution" in concepts
    assert "EvidenceRecord" in concepts


def test_compatibility_mapping_round_trip() -> None:
    sample = ARCHITECTURE_V2_1_COMPATIBILITY_MAPPINGS[0]
    restored = MarketsynthCompatibilityMapping.model_validate(sample.model_dump())
    assert restored.marketsynth_concept == sample.marketsynth_concept
    assert restored.legacy_artifact == sample.legacy_artifact
