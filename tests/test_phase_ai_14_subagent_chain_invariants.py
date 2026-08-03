"""Phase AI.14.1 — multi-subagent chain freeze invariants (guard)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from app.agents.marketer.chain_execution import execute_subagent_chain
from app.agents.marketer.chains import (
    COMPACT_SUBAGENT_OUTPUT_MAX_BYTES,
    CONTENT_LAUNCH,
    CONTENT_PLAN,
    MAX_SUBAGENT_CHAIN_LENGTH,
    RESEARCH,
    REWRITE,
    validate_chain,
)
from app.agents.marketer.compact_output import compact_subagent_output
from app.agents.marketer.router import detect_execution_chain
from app.schemas.agent_chat import AgentChatSendResponse

MARKETER_CHAIN_MODULES = (
    Path(__file__).resolve().parents[1] / "app" / "agents" / "marketer" / "execution.py",
    Path(__file__).resolve().parents[1] / "app" / "agents" / "marketer" / "chain_execution.py",
    Path(__file__).resolve().parents[1] / "app" / "agents" / "marketer" / "router.py",
    Path(__file__).resolve().parents[1] / "app" / "agents" / "marketer" / "chains.py",
)

FORBIDDEN_MARKERS = ("langgraph", "handoff", "parallel_execution", "swarm")


def test_invariant_max_chain_length_is_three() -> None:
    assert MAX_SUBAGENT_CHAIN_LENGTH == 3
    assert len(CONTENT_LAUNCH) == 3


def test_invariant_frozen_chain_definitions() -> None:
    assert CONTENT_LAUNCH == (RESEARCH[0], CONTENT_PLAN[0], REWRITE[0])
    assert CONTENT_PLAN == (CONTENT_PLAN[0], REWRITE[0])


def test_invariant_validate_chain_rejects_empty() -> None:
    with pytest.raises(ValueError):
        validate_chain(())


def test_invariant_validate_chain_rejects_four_steps() -> None:
    with pytest.raises(ValueError):
        validate_chain((*CONTENT_LAUNCH, RESEARCH[0]))


def test_invariant_launch_and_content_plan_router_chains() -> None:
    assert detect_execution_chain(message="Запусти новый продукт") == CONTENT_LAUNCH
    assert detect_execution_chain(message="Сделай контент-план") == CONTENT_PLAN


def test_invariant_proanaliziruy_rynok_no_chain() -> None:
    assert detect_execution_chain(message="Проанализируй рынок") is None


def test_invariant_compact_output_respects_4kb() -> None:
    import json

    compact = compact_subagent_output({"content": "x" * 100_000})
    assert len(json.dumps(compact).encode("utf-8")) <= COMPACT_SUBAGENT_OUTPUT_MAX_BYTES


def test_invariant_chat_response_has_subagent_chain_field() -> None:
    assert "subagent_chain" in AgentChatSendResponse.model_fields
    assert "subagent_execution" in AgentChatSendResponse.model_fields


def test_invariant_chain_modules_no_langgraph_handoff() -> None:
    combined = "".join(path.read_text(encoding="utf-8") for path in MARKETER_CHAIN_MODULES).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker not in combined


def test_invariant_chain_execution_no_langgraph_in_source() -> None:
    source = inspect.getsource(execute_subagent_chain).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker not in source
