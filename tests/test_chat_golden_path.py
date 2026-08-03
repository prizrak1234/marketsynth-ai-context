"""Chat golden path — idempotency, contextual responses, no duplicate messages."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.user_request_assistant import build_assistant_message
from app.domain.user_request_routing import route_user_request
from app.schemas.contracts import UserRequestRouteCategory


ACCEPTANCE_TEXT = (
    "Делаю SaaS проект. ИИ-маркетинговое агентство, "
    "которое заменяет реальное агентство. "
    "Функционал — от идеи до полноценной рекламной кампании, "
    "а также создание контента для разных каналов."
)


def test_saas_acceptance_case_not_biv_canned_stub() -> None:
    decision = route_user_request(ACCEPTANCE_TEXT)
    assert decision.category == UserRequestRouteCategory.SAAS
    message = build_assistant_message(ACCEPTANCE_TEXT, decision)
    assert "Здесь лучше сначала проверить жизнеспособность идеи" not in message
    assert "SaaS" in message or "saas" in message.lower()
    assert "Создать проект" in message


def test_contextual_message_addresses_user_content() -> None:
    decision = route_user_request(ACCEPTANCE_TEXT)
    message = build_assistant_message(ACCEPTANCE_TEXT, decision)
    assert "агентств" in message.lower() or "маркетинг" in message.lower()
    assert "монетизац" in message.lower() or "аудитор" in message.lower()


def test_duplicate_idempotency_key_returns_same_row(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    key = f"chat-{uuid4()}"
    client_id = str(uuid4())
    payload = {
        "text": "Привет, это тестовый запрос для чата с достаточной длиной.",
        "client_message_id": client_id,
        "idempotency_key": key,
    }
    first = client.post("/user-requests", headers=auth_headers, json=payload)
    assert first.status_code == 201, first.text
    second = client.post("/user-requests", headers=auth_headers, json=payload)
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["sequence_number"] == second.json()["sequence_number"]


def test_two_posts_different_keys_create_two_messages(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    a = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": "Первый уникальный запрос в чат с достаточной длиной текста.",
            "client_message_id": str(uuid4()),
            "idempotency_key": f"chat-{uuid4()}",
        },
    )
    b = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": "Второй уникальный запрос в чат с достаточной длиной текста.",
            "client_message_id": str(uuid4()),
            "idempotency_key": f"chat-{uuid4()}",
        },
    )
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["id"] != b.json()["id"]
    assert a.json()["sequence_number"] != b.json()["sequence_number"]


def test_api_returns_chat_route_and_client_message_id(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client_id = str(uuid4())
    res = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": ACCEPTANCE_TEXT,
            "client_message_id": client_id,
            "idempotency_key": f"chat-{uuid4()}",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["client_message_id"] == client_id
    assert body["chat_route"] == "project_action"
    assert "жизнеспособность идеи" not in body["assistant_message"]
