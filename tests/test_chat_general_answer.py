"""General answer LLM path — one call, one persisted response, idempotent replay."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.domain.user_request_assistant import chat_route_for_decision
from app.domain.user_request_routing import route_user_request
from app.llm.contracts import LLMGenerateOutput
from app.llm.errors import LLMTimeoutError
from app.schemas.contracts import LLMProvider
from app.services.user_request_general_answer_service import UserRequestGeneralAnswerService


GENERAL_QUESTION = "Что такое unit-экономика SaaS и как её считать для подписной модели?"


@pytest.fixture(autouse=True)
def _mock_llm_provider(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "mock")
    monkeypatch.setenv("DEFAULT_LLM_MODEL", "mock-model")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_general_question_routes_to_general_answer() -> None:
    decision = route_user_request(GENERAL_QUESTION)
    assert chat_route_for_decision(decision) == "general_answer"
    assert decision.confidence >= 0.7
    assert decision.rationale


@pytest.mark.asyncio
async def test_general_answer_llm_called_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def _fake_generate(_self, data):  # noqa: ANN001
        nonlocal calls
        calls += 1
        user_text = next(
            (m.content for m in reversed(data.messages) if m.role == "user"),
            "",
        )
        return LLMGenerateOutput(
            content=f"Test answer for: {user_text[:80]}",
            provider=LLMProvider.MOCK,
            model="mock-model",
        )

    monkeypatch.setattr(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        _fake_generate,
    )
    result = await UserRequestGeneralAnswerService().generate(GENERAL_QUESTION)
    assert calls == 1
    assert "Test answer" in result.content


def test_general_answer_persisted_once(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client_id = str(uuid4())
    key = f"chat-ga-{uuid4()}"
    res = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": GENERAL_QUESTION,
            "client_message_id": client_id,
            "idempotency_key": key,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["chat_route"] == "general_answer"
    assert body["status"] == "routed"
    assert "Ответ Marketsynth (mock)" in body["assistant_message"]
    assert body["execution_provider"] == "mock"
    assert body["skill_inputs"].get("_llm_call_count") == 1
    assert body["routing_decision_id"] is not None


def test_provider_timeout_commercial_failure(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _timeout(_self, _data):  # noqa: ANN001
        raise LLMTimeoutError(
            "timeout",
            provider=LLMProvider.MOCK,
            model="mock-model",
        )

    monkeypatch.setattr(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        _timeout,
    )
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "mock")
    from app.core.config import get_settings

    get_settings.cache_clear()

    res = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": GENERAL_QUESTION,
            "client_message_id": str(uuid4()),
            "idempotency_key": f"chat-fail-{uuid4()}",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "failed"
    assert body["chat_route"] == "general_answer"
    assert "Не удалось получить ответ" in body["assistant_message"]
    assert "жизнеспособность идеи" not in body["assistant_message"]


def test_empty_content_controlled_failure(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _empty(_self, data):  # noqa: ANN001
        return LLMGenerateOutput(
            content="   ",
            provider=LLMProvider.MOCK,
            model="mock-model",
        )

    monkeypatch.setattr(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        _empty,
    )
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "mock")
    from app.core.config import get_settings

    get_settings.cache_clear()

    res = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": GENERAL_QUESTION,
            "client_message_id": str(uuid4()),
            "idempotency_key": f"chat-empty-{uuid4()}",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "failed"
    assert "пустой ответ" in body["assistant_message"].lower()


def test_duplicate_post_does_not_call_llm_twice(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    original = UserRequestGeneralAnswerService.generate

    async def _counting_generate(self, *args, **kwargs):  # noqa: ANN001, ANN002
        nonlocal calls
        calls += 1
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(UserRequestGeneralAnswerService, "generate", _counting_generate)

    key = f"chat-dup-{uuid4()}"
    client_id = str(uuid4())
    payload = {
        "text": GENERAL_QUESTION,
        "client_message_id": client_id,
        "idempotency_key": key,
    }
    first = client.post("/user-requests", headers=auth_headers, json=payload)
    second = client.post("/user-requests", headers=auth_headers, json=payload)
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert calls == 1
