"""Prompt/message builder layer tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.prompts.contracts import PromptBuildInput
from app.prompts.message_builder import build_llm_messages
from app.prompts.safety import PromptBuildError, sanitize_prompt_context
from app.prompts.templates import DEFAULT_SYSTEM_PROMPTS
from app.schemas.contracts import AgentType
from fastapi.testclient import TestClient


def test_build_messages_happy_path() -> None:
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.RESEARCHER,
            agent_config={},
            input_payload={"prompt": "Analyze the audience"},
        ),
    )
    assert len(built.messages) >= 2
    assert built.messages[0].role == "system"
    assert built.messages[-1].role == "user"
    assert "Analyze the audience" in built.messages[-1].content
    assert built.metadata["message_count"] == len(built.messages)
    assert built.metadata["agent_type"] == "researcher"


def test_system_prompt_selected_by_agent_type() -> None:
    strategist = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.STRATEGIST,
            input_payload={"prompt": "Plan Q2"},
        ),
    )
    researcher = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.RESEARCHER,
            input_payload={"prompt": "Plan Q2"},
        ),
    )
    assert strategist.messages[0].content == DEFAULT_SYSTEM_PROMPTS[AgentType.STRATEGIST]
    assert researcher.messages[0].content == DEFAULT_SYSTEM_PROMPTS[AgentType.RESEARCHER]
    assert strategist.metadata["prompt_template_id"] == "default:strategist"


def test_user_input_becomes_user_message() -> None:
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.COPYWRITER,
            input_payload={"prompt": "Write a headline"},
        ),
    )
    user_messages = [message for message in built.messages if message.role == "user"]
    assert len(user_messages) == 1
    assert user_messages[0].content == "Write a headline"


def test_memory_context_adds_optional_system_message() -> None:
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.ANALYST,
            input_payload={"prompt": "Summarize"},
            memory_context={"campaign": "spring launch", "kpi": "ctr"},
        ),
    )
    assert built.metadata["has_memory_context"] is True
    assert built.metadata["message_count"] == 3
    assert any("Memory context" in message.content for message in built.messages)


def test_secrets_in_agent_config_are_blocked() -> None:
    with pytest.raises(PromptBuildError, match="api_key"):
        build_llm_messages(
            PromptBuildInput(
                agent_id=uuid4(),
                agent_type=AgentType.RESEARCHER,
                agent_config={"prompt": {"system": "ok", "api_key": "sk-bad"}},
                input_payload={"prompt": "hello"},
            ),
        )


def test_secret_values_are_redacted_in_sanitized_context() -> None:
    sanitized = sanitize_prompt_context({"note": "token=sk-secret-value"})
    assert sanitized["note"] == "[REDACTED]"


def test_metadata_contains_expected_fields() -> None:
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.ORCHESTRATOR,
            input_payload={"prompt": "route task", "channel": "email"},
        ),
    )
    assert built.metadata["prompt_template_id"] == "default:orchestrator"
    assert "prompt" in built.metadata["input_keys"]
    assert "channel" in built.metadata["input_keys"]
    assert "messages" not in str(built.metadata)


def test_custom_system_override_is_supported() -> None:
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.RESEARCHER,
            input_payload={"prompt": "hello"},
            system_overrides="You are a custom system prompt.",
        ),
    )
    assert built.messages[0].content == "You are a custom system prompt."
    assert built.metadata["prompt_template_id"] == "override:system"


def test_unknown_config_shape_falls_back_without_crashing() -> None:
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.RESEARCHER,
            agent_config={"llm": {"provider": "mock"}, "unexpected": {"nested": True}},
            input_payload={"prompt": "still works"},
        ),
    )
    assert built.messages[-1].content == "still works"


def test_prebuilt_messages_are_preserved() -> None:
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.RESEARCHER,
            input_payload={
                "messages": [{"role": "user", "content": "custom chain"}],
            },
        ),
    )
    assert any(message.content == "custom chain" for message in built.messages)


def test_prompt_builder_error_returns_409_from_executor(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Prompt Fail Project"}, headers=auth_headers)
    agent = client.post(
        "/agents",
        json={"project_id": project.json()["id"], "type": "researcher"},
        headers=auth_headers,
    )
    agent_id = agent.json()["id"]
    client.patch(
        f"/agents/{agent_id}",
        json={"config": {"prompt": {"api_key": "sk-no"}}},
        headers=auth_headers,
    )
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "fail"}},
        headers=auth_headers,
    ).json()["id"]

    response = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 409
    assert client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()["status"] == "queued"


def test_executor_stores_prompt_metadata_not_full_prompt_dump(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Prompt Meta Project"}, headers=auth_headers)
    agent = client.post(
        "/agents",
        json={"project_id": project.json()["id"], "type": "strategist"},
        headers=auth_headers,
    )
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent.json()["id"], "input_payload": {"prompt": "Plan campaign"}},
        headers=auth_headers,
    ).json()["id"]
    execute = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)
    assert execute.status_code == 200

    llm_request = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()[0]
    assert llm_request["request_metadata"]["prompt_template_id"] == "default:strategist"
    assert llm_request["prompt_metadata"]["agent_type"] == "strategist"
    assert "messages" not in llm_request["input_payload"]
    assert llm_request["input_payload"]["input"] == {"prompt": "Plan campaign"}

    detail = client.get(f"/llm-requests/{llm_request['id']}", headers=auth_headers).json()
    assert "prompt_template_id" not in detail["response"]["output_payload"]
    assert detail["response"]["raw_response"] == {}
