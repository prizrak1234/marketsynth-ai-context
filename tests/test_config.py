"""Configuration tests."""

from __future__ import annotations

import pytest
from app.core.config import Settings, get_settings


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_VERSION", "0.1.0-test")
    settings = Settings()
    assert settings.app_env == "development"
    assert settings.app_version == "0.1.0-test"
    assert settings.is_development is True
    get_settings.cache_clear()


def test_safe_dict_redacts_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "super-secret")
    monkeypatch.setenv("TELEGRAM_PUBLICATION_BOT_TOKEN", "tg-token")
    settings = Settings()
    safe = settings.safe_dict()
    assert safe["telegram_webhook_secret"] == "***"
    assert safe["telegram_publication_bot_token"] == "***"
    get_settings.cache_clear()
