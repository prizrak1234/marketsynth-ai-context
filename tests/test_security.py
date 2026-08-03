"""PII sanitizer and Telegram secret verification tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.core.config import Settings
from app.core.logging import sanitize_log_payload
from app.middleware.telegram import check_telegram_webhook_secret
from app.security.pii import mask_email, mask_phone, sanitize_payload, sanitize_text
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_mask_email() -> None:
    assert mask_email("Contact user@example.com today") == "Contact [EMAIL] today"


def test_mask_phone() -> None:
    assert mask_phone("Call +79991234567 now") == "Call [PHONE] now"


def test_mask_phone_preserves_uuid_values() -> None:
    brief_id = "4d2ff820-9789-4347-b482-20e413ad1edc"
    assert mask_phone(brief_id) == brief_id
    assert sanitize_payload({"source_campaign_brief_id": brief_id}) == {
        "source_campaign_brief_id": brief_id
    }


def test_sanitize_text_masks_email_and_phone() -> None:
    text = "Email user@example.com or call +79991234567"
    result = sanitize_text(text)
    assert "[EMAIL]" in result
    assert "[PHONE]" in result
    assert "user@example.com" not in result
    assert "+79991234567" not in result


def test_sanitize_payload_nested_dict_and_list() -> None:
    data = {
        "message": {"text": "Call +79991234567"},
        "contacts": ["a@b.co", {"phone": "+1 (555) 123-4567"}],
    }
    result = sanitize_payload(data)
    assert result["message"]["text"] == "Call [PHONE]"
    assert result["contacts"][0] == "[EMAIL]"
    assert result["contacts"][1]["phone"] == "[PHONE]"


def test_sanitize_payload_none() -> None:
    assert sanitize_payload(None) is None


def test_sanitize_log_payload_uses_sanitizer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_SANITIZER_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    payload = {"email": "secret@example.com"}
    result = sanitize_log_payload(payload)
    assert result == {"email": "[EMAIL]"}
    get_settings.cache_clear()


def test_check_telegram_secret_valid() -> None:
    settings = Settings(telegram_webhook_secret="abc", app_env="development")
    request = MagicMock()
    request.headers = {"X-Telegram-Bot-Api-Secret-Token": "abc"}
    check_telegram_webhook_secret(request, settings)


def test_check_telegram_secret_invalid() -> None:
    settings = Settings(telegram_webhook_secret="abc", app_env="development")
    request = MagicMock()
    request.headers = {"X-Telegram-Bot-Api-Secret-Token": "wrong"}
    with pytest.raises(HTTPException) as exc:
        check_telegram_webhook_secret(request, settings)
    assert exc.value.status_code == 403


def test_telegram_webhook_accepts_valid_secret(client: TestClient) -> None:
    response = client.post(
        "/webhooks/telegram",
        json={"update_id": 1, "message": {"text": "hello user@secret.com"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_telegram_webhook_rejects_bad_secret(client: TestClient) -> None:
    response = client.post(
        "/webhooks/telegram",
        json={"update_id": 2},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert response.status_code == 403
