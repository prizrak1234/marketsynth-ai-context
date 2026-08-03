"""Manual LiteLLM smoke test — real OpenAI call outside pytest and the API.

Usage:
    uv run python scripts/smoke_litellm_openai.py

Requires OPENAI_API_KEY in .env and optional extra: uv sync --extra llm
"""

from __future__ import annotations

import asyncio
import sys

from app.core.config import get_settings
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.llm.errors import LLMError
from app.llm.litellm_adapter import LiteLLMAdapter
from app.llm.provider_config import get_provider_runtime_config
from app.schemas.contracts import LLMProvider

OPENAI_FALLBACK_MODEL = "gpt-4o-mini"


def _resolve_smoke_model(default_model: str) -> str:
    if not default_model or default_model == "mock-model":
        return OPENAI_FALLBACK_MODEL
    return default_model


def _safe_error_message(exc: BaseException) -> str:
    message = str(exc).strip()
    if not message:
        return "(no message)"
    lowered = message.lower()
    if "sk-" in lowered or "api_key" in lowered or "authorization" in lowered:
        return "(error message redacted — may contain secrets)"
    return message


def _print_usage(usage: dict[str, object]) -> None:
    if not usage:
        return
    parts = []
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        if key in usage:
            parts.append(f"{key}={usage[key]}")
    if parts:
        print(f"usage: {', '.join(parts)}")


async def run_smoke_litellm_openai() -> int:
    settings = get_settings()
    runtime = get_provider_runtime_config(LLMProvider.OPENAI, settings)

    if not runtime.api_key:
        print(
            "ERROR: OPENAI_API_KEY is not set.\n"
            "Add OPENAI_API_KEY=sk-... to your .env file and retry.",
            file=sys.stderr,
        )
        return 1

    model = _resolve_smoke_model(settings.default_llm_model)
    adapter = LiteLLMAdapter()
    request = LLMGenerateInput(
        provider=LLMProvider.OPENAI,
        model=model,
        messages=[
            LLMMessage(role="system", content="You are a concise assistant."),
            LLMMessage(role="user", content="Reply with exactly: LiteLLM smoke ok"),
        ],
        temperature=0.1,
        max_tokens=100,
        metadata={"source": "smoke_litellm_openai"},
    )

    try:
        output = await adapter.generate(request)
    except LLMError as exc:
        print(f"ERROR: {type(exc).__name__}: {_safe_error_message(exc)}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {_safe_error_message(exc)}", file=sys.stderr)
        return 1

    resolved_model = output.model or model
    print(f"provider: {output.provider.value}")
    print(f"model: {resolved_model}")
    print(f"content: {output.content}")
    _print_usage(output.usage)
    return 0


def main() -> None:
    exit_code = asyncio.run(run_smoke_litellm_openai())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
