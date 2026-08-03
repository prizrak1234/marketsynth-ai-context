"""Pin-aware text generation adapter for Content Director (PRODUCT-CD-RUNTIME-01).

Never Architecture-canonical. Does not call ContentFactoryGenerationService.
Does not merge H2.7 content drafts. Reads only the pinned ContentInputSnapshot.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.llm.config import resolve_llm_config
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.llm.registry import get_llm_adapter
from app.schemas.contracts import LLMProvider


@dataclass(frozen=True)
class GeneratedTextCandidate:
    title: str
    body: str
    provider: str
    model: str
    metadata: dict[str, Any]


class ContentDirectorTextAdapter:
    """Generate 1..N telegram_post candidates from a pinned snapshot only."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def generate_candidates(
        self,
        *,
        snapshot_payload: dict[str, Any],
        content_request_id: str,
        content_request_version: int,
        snapshot_id: str,
        requested_variants: int,
    ) -> list[GeneratedTextCandidate]:
        if requested_variants < 1 or requested_variants > 3:
            raise InvalidStateError("requested_variants must be between 1 and 3")

        # Pin check — refuse unbound generation
        if not snapshot_payload.get("content_request_id"):
            raise InvalidStateError("Snapshot missing content_request_id pin")
        if str(snapshot_payload.get("content_request_id")) != str(content_request_id):
            raise InvalidStateError("Snapshot content_request_id mismatch")
        if int(snapshot_payload.get("content_request_version", -1)) != int(
            content_request_version
        ):
            raise InvalidStateError("Snapshot content_request_version mismatch")

        # Fixture path is opt-in only — never implied by DEFAULT_LLM_PROVIDER=mock.
        if self._settings.content_director_deterministic:
            return self._deterministic_candidates(
                snapshot_payload=snapshot_payload,
                count=requested_variants,
            )

        return await self._llm_candidates(
            snapshot_payload=snapshot_payload,
            count=requested_variants,
            content_request_id=content_request_id,
            snapshot_id=snapshot_id,
        )

    def _deterministic_candidates(
        self,
        *,
        snapshot_payload: dict[str, Any],
        count: int,
    ) -> list[GeneratedTextCandidate]:
        title_base = str(snapshot_payload.get("title") or "Telegram post")
        key = str(snapshot_payload.get("key_message") or "Key message")
        cta = str(snapshot_payload.get("cta") or "").strip()
        audience = str(snapshot_payload.get("audience_description") or "audience")
        out: list[GeneratedTextCandidate] = []
        for idx in range(count):
            n = idx + 1
            body_parts = [
                f"Вариант {n}: {key}",
                f"Для аудитории: {audience}.",
            ]
            if cta:
                body_parts.append(cta)
            body_parts.append(
                f"[content_director_deterministic · request v{snapshot_payload.get('content_request_version')}]"
            )
            out.append(
                GeneratedTextCandidate(
                    title=f"{title_base} — вариант {n}",
                    body="\n\n".join(body_parts),
                    provider="deterministic",
                    model="fixture",
                    metadata={
                        "generation_mode": "deterministic",
                        "candidate_index": n,
                        "content_request_id": snapshot_payload.get("content_request_id"),
                        "content_request_version": snapshot_payload.get(
                            "content_request_version"
                        ),
                        "skill_id": "marketsynth.copywriter",
                        "skill_version": "1.0.0",
                        "copywriter_package_verified": self._copywriter_package_present(),
                    },
                )
            )
        return out

    async def _llm_candidates(
        self,
        *,
        snapshot_payload: dict[str, Any],
        count: int,
        content_request_id: str,
        snapshot_id: str,
    ) -> list[GeneratedTextCandidate]:
        try:
            provider, model, temperature, max_tokens = resolve_llm_config(
                {},
                self._settings,
            )
        except Exception as exc:  # noqa: BLE001 — normalize for customer surface
            raise InvalidStateError(
                f"provider_config_error: {type(exc).__name__}"
            ) from exc

        prompt = self._build_prompt(snapshot_payload, count)
        system = self._copywriter_system_prompt()
        adapter = get_llm_adapter(provider)
        try:
            result = await adapter.generate(
                LLMGenerateInput(
                    provider=provider,
                    model=model,
                    messages=[
                        LLMMessage(
                            role="system",
                            content=system,
                        ),
                        LLMMessage(role="user", content=prompt),
                    ],
                    temperature=temperature if temperature is not None else 0.7,
                    max_tokens=max_tokens if max_tokens is not None else 1200,
                    metadata={
                        "content_director": True,
                        "content_request_id": content_request_id,
                        "snapshot_id": snapshot_id,
                        "skill_id": "marketsynth.copywriter",
                        "skill_version": "1.0.0",
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001
            raise InvalidStateError(
                f"provider_failure: {type(exc).__name__}"
            ) from exc

        text = (result.content or "").strip()
        parsed = self._parse_candidates_json(text, count)
        provider_name = (
            provider.value if isinstance(provider, LLMProvider) else str(provider)
        )
        out: list[GeneratedTextCandidate] = []
        for idx, item in enumerate(parsed):
            out.append(
                GeneratedTextCandidate(
                    title=item["title"][:512],
                    body=item["body"][:20000],
                    provider=provider_name,
                    model=str(model),
                    metadata={
                        "generation_mode": "llm",
                        "candidate_index": idx + 1,
                        "content_request_id": content_request_id,
                        "snapshot_id": snapshot_id,
                        "skill_id": "marketsynth.copywriter",
                        "skill_version": "1.0.0",
                    },
                )
            )
        return out

    def _copywriter_package_present(self) -> bool:
        from app.product_skills.catalog import package_root_for

        root = package_root_for("marketsynth.copywriter", "1.0.0")
        return (root / "SKILL.md").is_file() and (
            root / "resources" / "system_prompt.md"
        ).is_file()

    def _copywriter_system_prompt(self) -> str:
        from app.product_skills.catalog import package_root_for

        root = package_root_for("marketsynth.copywriter", "1.0.0")
        system = ""
        skill_md = ""
        sp = root / "resources" / "system_prompt.md"
        sm = root / "SKILL.md"
        if sp.is_file():
            system = sp.read_text(encoding="utf-8")[:12000]
        if sm.is_file():
            skill_md = sm.read_text(encoding="utf-8")[:4000]
        base = (
            "You write Telegram marketing posts using Marketsynth Copywriter skill "
            "(marketsynth.copywriter@1.0.0). "
            "Return JSON only: {\"candidates\":[{\"title\":\"\",\"body\":\"\"},...]}. "
            "Do not invent unverified facts. Mark assumptions explicitly. "
            "Do not change Strategy/Offer/ICP. No secrets. Customer language."
        )
        if system:
            return f"{base}\n\n# Copywriter system prompt\n{system}\n\n# Skill notes\n{skill_md[:2000]}"
        return base

    def _build_prompt(self, snapshot_payload: dict[str, Any], count: int) -> str:
        return (
            f"Create exactly {count} Telegram post variants.\n"
            f"Title context: {snapshot_payload.get('title')}\n"
            f"Objective: {snapshot_payload.get('objective')}\n"
            f"Audience: {snapshot_payload.get('audience_description')}\n"
            f"Key message: {snapshot_payload.get('key_message')}\n"
            f"Offer/VP: {snapshot_payload.get('offer_value_proposition')}\n"
            f"Tone: {snapshot_payload.get('tone')}\n"
            f"Language: {snapshot_payload.get('language')}\n"
            f"Length: {snapshot_payload.get('length')}\n"
            f"CTA: {snapshot_payload.get('cta')}\n"
            f"Must include: {snapshot_payload.get('must_include')}\n"
            f"Must avoid: {snapshot_payload.get('must_avoid')}\n"
            "Channel: telegram. Type: telegram_post.\n"
            "Return JSON only."
        )

    def _parse_candidates_json(
        self,
        text: str,
        count: int,
    ) -> list[dict[str, str]]:
        match = re.search(r"\{[\s\S]*\}", text)
        raw = match.group(0) if match else text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidStateError("provider_failure: invalid_json_response") from exc
        items = data.get("candidates") if isinstance(data, dict) else None
        if not isinstance(items, list) or not items:
            raise InvalidStateError("provider_failure: empty_candidates")
        out: list[dict[str, str]] = []
        for item in items[:count]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "Telegram post").strip()
            body = str(item.get("body") or "").strip()
            if not body:
                continue
            out.append({"title": title, "body": body})
        if len(out) < 1:
            raise InvalidStateError("provider_failure: no_valid_candidates")
        while len(out) < count:
            base = out[-1]
            out.append(
                {
                    "title": f"{base['title']} ({len(out) + 1})",
                    "body": base["body"],
                }
            )
        return out[:count]
