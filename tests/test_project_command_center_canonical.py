"""PROJECT-COMMAND-CENTER-CANONICAL-01 — summary + General recommend-only."""

from __future__ import annotations

from app.domain.project_command_center_routing import route_project_general
from fastapi.testclient import TestClient


def _project(client: TestClient, headers: dict[str, str], name: str = "PCC Canon") -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def test_route_text_intent_deep_links_content_director() -> None:
    d = route_project_general("Напиши Telegram-пост про оффер", project_id="proj-1")
    assert d.capability_id == "project.content_director"
    assert d.skill_id == "marketsynth.copywriter"
    assert d.next_href and "view=content_director" in d.next_href
    assert "mode=text" in d.next_href
    assert d.requires_approval is True


def test_route_image_marks_paid_and_approval() -> None:
    d = route_project_general("Создай изображение к посту", project_id="proj-1")
    assert d.next_href and "mode=image" in d.next_href
    assert d.requires_paid is True
    assert d.requires_approval is True


def test_route_video_coming_soon_no_href() -> None:
    d = route_project_general("Сделай видео для запуска", project_id="proj-1")
    assert d.status_notes == "coming_soon"
    assert d.next_href is None


def test_route_avito_unconfigured_no_execute() -> None:
    d = route_project_general(
        "Покажи расходы на Avito",
        project_id="proj-1",
        avito_configured=False,
    )
    assert d.skill_id == "marketsynth.avito"
    assert d.status_notes == "unconfigured"
    assert d.next_href == "/workspace/settings/skills"
    assert d.requires_external is True


def test_route_research_paused() -> None:
    d = route_project_general("Проверь идею заново", project_id="proj-1")
    assert d.capability_id == "project.research"
    assert d.status_notes == "paused"
    assert "пока нет" in d.assistant_message


def test_route_research_paused_with_saved_result() -> None:
    d = route_project_general(
        "Проверь идею заново",
        project_id="proj-1",
        has_research_result=True,
    )
    assert d.status_notes == "paused"
    assert "Сохранённый прогон" in d.assistant_message
    assert d.next_href and "#pcc-recent" in d.next_href


def test_command_center_summary_and_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    execute_calls: list[object] = []

    async def _forbid_execute(self, *args, **kwargs):  # noqa: ANN001
        execute_calls.append((args, kwargs))
        raise AssertionError("ProductSkillRuntimeService.execute must not run on GET summary")

    monkeypatch.setattr(
        "app.product_skills.runtime_service.ProductSkillRuntimeService.execute",
        _forbid_execute,
    )

    project_id = _project(client, auth_headers)
    ok = client.get(f"/projects/{project_id}/command-center", headers=auth_headers)
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["project_id"] == project_id
    assert body["project_name"] == "PCC Canon"
    assert execute_calls == []
    ids = [c["capability_id"] for c in body["capabilities"]]
    assert "project.content_director.text" in ids
    assert "project.content_director.image" in ids
    assert "launch.visuals" in ids
    research = next(c for c in body["capabilities"] if c["capability_id"] == "project.research")
    assert research["status"] == "paused"
    assert "пока нет" in (research.get("placeholder_note") or "")
    video = next(c for c in body["capabilities"] if c["capability_id"] == "launch.visuals")
    assert video["status"] == "coming_soon"
    assert video["cta_enabled"] is False
    text = next(
        c for c in body["capabilities"] if c["capability_id"] == "project.content_director.text"
    )
    assert text["status"] == "available"
    assert text["primary_cta_href"] and "mode=text" in text["primary_cta_href"]
    # Status labels are customer-facing, not raw enums alone on cards
    assert text["status_label"] == "Доступно"
    # No hardcoded «В работе» on fresh project capability cards
    assert all(c["status"] != "in_progress" for c in body["capabilities"])

    denied = client.get(
        f"/projects/{project_id}/command-center",
        headers=other_auth_headers,
    )
    assert denied.status_code in (403, 404)


def test_general_persists_and_recommend_only(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    execute_calls: list[object] = []

    async def _forbid_execute(self, *args, **kwargs):  # noqa: ANN001
        execute_calls.append((args, kwargs))
        raise AssertionError("execute must not run on General send")

    monkeypatch.setattr(
        "app.product_skills.runtime_service.ProductSkillRuntimeService.execute",
        _forbid_execute,
    )

    project_id = _project(client, auth_headers, name="PCC General")
    empty = client.get(
        f"/projects/{project_id}/command-center/general",
        headers=auth_headers,
    )
    assert empty.status_code == 200
    assert empty.json()["messages"] == []

    denied_get = client.get(
        f"/projects/{project_id}/command-center/general",
        headers=other_auth_headers,
    )
    assert denied_get.status_code in (403, 404)

    sent = client.post(
        f"/projects/{project_id}/command-center/general/messages",
        headers=auth_headers,
        json={"message": "Напиши пост для Telegram"},
    )
    assert sent.status_code == 200, sent.text
    payload = sent.json()
    assert payload["assistant"]["skill_id"] == "marketsynth.copywriter"
    assert payload["assistant"]["next_href"]
    assert "mode=text" in payload["assistant"]["next_href"]
    assert len(payload["conversation"]["messages"]) >= 2
    assert execute_calls == []

    denied_post = client.post(
        f"/projects/{project_id}/command-center/general/messages",
        headers=other_auth_headers,
        json={"message": "intruder"},
    )
    assert denied_post.status_code in (403, 404)

    restored = client.get(
        f"/projects/{project_id}/command-center/general",
        headers=auth_headers,
    )
    assert restored.status_code == 200
    assert len(restored.json()["messages"]) >= 2
    roles = [m["role"] for m in restored.json()["messages"]]
    assert "user" in roles and "assistant" in roles


def test_general_avito_cannot_execute(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    execute_calls: list[object] = []

    async def _forbid_execute(self, *args, **kwargs):  # noqa: ANN001
        execute_calls.append((args, kwargs))
        raise AssertionError("Avito General must not execute skills")

    monkeypatch.setattr(
        "app.product_skills.runtime_service.ProductSkillRuntimeService.execute",
        _forbid_execute,
    )
    monkeypatch.setattr(
        "app.services.project_command_center_service.avito_configured",
        lambda: False,
    )

    project_id = _project(client, auth_headers, name="PCC Avito")
    sent = client.post(
        f"/projects/{project_id}/command-center/general/messages",
        headers=auth_headers,
        json={"message": "Покажи расходы на Avito"},
    )
    assert sent.status_code == 200
    assistant = sent.json()["assistant"]
    assert assistant["skill_id"] == "marketsynth.avito"
    assert assistant["status_notes"] == "unconfigured"
    assert assistant["requires_external"] is True
    assert execute_calls == []


def test_general_avito_configured_still_recommend_only(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    execute_calls: list[object] = []

    async def _forbid_execute(self, *args, **kwargs):  # noqa: ANN001
        execute_calls.append((args, kwargs))
        raise AssertionError("configured Avito must still be recommend-only from General")

    monkeypatch.setattr(
        "app.product_skills.runtime_service.ProductSkillRuntimeService.execute",
        _forbid_execute,
    )
    monkeypatch.setattr(
        "app.services.project_command_center_service.avito_configured",
        lambda: True,
    )

    project_id = _project(client, auth_headers, name="PCC Avito OK")
    sent = client.post(
        f"/projects/{project_id}/command-center/general/messages",
        headers=auth_headers,
        json={"message": "Покажи расходы на Avito"},
    )
    assert sent.status_code == 200
    assistant = sent.json()["assistant"]
    assert assistant["skill_id"] == "marketsynth.avito"
    assert assistant["next_href"] == "/workspace/settings/skills"
    assert execute_calls == []