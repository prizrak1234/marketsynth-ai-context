"""General-answer LLM execution for commercial chat (one call, one persisted response)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.llm.contracts import LLMGenerateInput
from app.llm.errors import LLMError
from app.llm.registry import get_llm_adapter
from app.prompts.user_request_general_answer import build_general_answer_messages
from app.schemas.contracts import LLMProvider

log = logging.getLogger(__name__)

MSG_PROVIDER_FAILED = (
    "Не удалось получить ответ от модели. Повторите запрос — проект не создавался."
)
MSG_EMPTY = "Модель вернула пустой ответ. Повторите запрос."


@dataclass(frozen=True, slots=True)
class GeneralAnswerResult:
    content: str
    provider: str
    model: str


class GeneralAnswerFailure(Exception):
    def __init__(self, category: str, message: str) -> None:
        self.category = category
        self.message = message
        super().__init__(message)


class UserRequestGeneralAnswerService:
    async def generate(
        self,
        user_text: str,
        *,
        locale: str = "ru",
        settings: Settings | None = None,
    ) -> GeneralAnswerResult:
        cfg = settings or get_settings()
        if not cfg.chat_general_answer_enabled:
            raise GeneralAnswerFailure("disabled", MSG_PROVIDER_FAILED)

        provider = _resolve_provider(cfg.default_llm_provider)
        model = cfg.default_llm_model
        messages = build_general_answer_messages(user_text=user_text, locale=locale)

        delay = float(cfg.chat_general_answer_e2e_delay_seconds or 0)
        if delay > 0 and cfg.app_env in {"development", "test"}:
            await asyncio.sleep(delay)

        metadata = {
            "user_request_general_answer": True,
            "locale": locale,
        }

        adapter = get_llm_adapter(provider)
        try:
            output = await adapter.generate(
                LLMGenerateInput(
                    provider=provider,
                    model=model,
                    messages=messages,
                    temperature=0.4,
                    max_tokens=900,
                    timeout_seconds=cfg.llm_timeout_seconds,
                    max_retries=cfg.llm_max_retries,
                    metadata=metadata,
                ),
            )
        except LLMError as exc:
            log.warning(
                "general_answer_llm_failed",
                extra={
                    "provider": exc.provider,
                    "model": exc.model,
                    "error_type": exc.original_error_type,
                },
            )
            raise GeneralAnswerFailure("provider_error", MSG_PROVIDER_FAILED) from exc
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "general_answer_llm_unexpected",
                extra={"error": type(exc).__name__},
            )
            raise GeneralAnswerFailure("provider_error", MSG_PROVIDER_FAILED) from exc

        content = (output.content or "").strip()
        if not content:
            raise GeneralAnswerFailure("empty_content", MSG_EMPTY)

        return GeneralAnswerResult(
            content=content[:4000],
            provider=provider.value,
            model=output.model or model,
        )


def _resolve_provider(provider_name: str) -> LLMProvider:
    try:
        return LLMProvider(provider_name.lower())
    except ValueError as exc:
        raise GeneralAnswerFailure("provider_error", MSG_PROVIDER_FAILED) from exc
