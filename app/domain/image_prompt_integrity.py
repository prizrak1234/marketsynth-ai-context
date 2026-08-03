"""Image prompt integrity helpers (Phase H2.8A) тАФ binding, fingerprints, gross mismatch."""

from __future__ import annotations

import hashlib
import re
from typing import Any

_META_ONLY = re.compile(
    r"(?is)^\s*(?:"
    r"╤Б╨┤╨╡╨╗╨░╨╣\s+╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕[╨╡╤П]\s+╨┐╨╛\s+╨┐╤А╨╛╨╝[╨┐╤В]╤Г|"
    r"╨┐╨╛\s+╨┐╤А╨╛╨╝[╨┐╤В]╤Г|"
    r"use\s+(?:the\s+)?(?:attached\s+)?(?:prompt|reference)|"
    r"╨┐╨╛\s+╤А╨╡╤Д╨╡╤А╨╡╨╜╤Б╤Г|"
    r"╨╖╨░\s+╤А╨╡╤Д╨╡╤А╨╡╨╜╤Б\s+╨╕╤Б╨┐╨╛╨╗╤М╨╖╤Г╨╣|"
    r"╨╕╤Б╨┐╨╛╨╗╤М╨╖╤Г╨╣\s+╨┐╤А╨╕╨╗╨╛╨╢╨╡╨╜╨╜\w+\s+╤Д╨░╨╣╨╗|"
    r"generate\s+(?:from|using)\s+(?:the\s+)?(?:prompt|reference)"
    r").*$"
)

_PERSON = re.compile(
    r"(?i)\b(?:╨╢╨╡╨╜╤Й╨╕╨╜|╨┤╨╡╨▓╤Г╤И╨║|╨┐╨╛╤А╤В╤А╨╡╤В|person|woman|man|girl|boy|face|╨╗╨╕╤Ж╨╛|"
    r"╨┤╨╡╨╝╨╛╨╜|demon|╨│╨╡╤А╨╛╨╕|character|╨┐╨╛╤А╤В╤А╨╡╤В)\b"
)
_BOTANICAL = re.compile(
    r"(?i)\b(?:╤А╨╛╨╖[╨░╤Л╤Г]|rose|flower|╤Ж╨▓╨╡╤В╨╛╨║|╤Ж╨▓╨╡╤В╨║|╨▒╨╛╤В╨░╨╜╨╕╨║|╨▒╤Г╨║╨╡╤В|╤Д╨╗╨╛╤А╨╕╤Б╤В|"
    r"╤В╤О╨╗╤М╨┐╨░╨╜|lily|orchid)\b"
)
_PRODUCT = re.compile(r"(?i)\b(?:╨┐╤А╨╛╨┤╤Г╨║╤В|╤Г╨┐╨░╨║╨╛╨▓╨║|bottle|packaging|logo|╨╗╨╛╨│╨╛╤В╨╕╨┐)\b")


def normalize_prompt_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def prompt_hash(text: str) -> str:
    digest = hashlib.sha256(normalize_prompt_text(text).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def is_meta_only_image_prompt(text: str) -> bool:
    """True when the text is an instruction to use a prompt/reference, not a scene."""
    cleaned = normalize_prompt_text(text)
    if len(cleaned) < 12:
        return True
    if len(cleaned) > 220:
        return False
    if _META_ONLY.match(cleaned):
        return True
    # Short instruction that mentions reference/prompt but lacks scene nouns.
    lower = cleaned.lower()
    mentions_ref = any(
        t in lower
        for t in ("╤А╨╡╤Д╨╡╤А╨╡╨╜╤Б", "reference", "╨┐╤А╨╛╨╝╤В", "╨┐╤А╨╛╨╝╨┐╤В", "prompt", "╨┐╤А╨╕╨╗╨╛╨╢╨╡╨╜")
    )
    has_scene = bool(_PERSON.search(cleaned) or _BOTANICAL.search(cleaned) or _PRODUCT.search(cleaned))
    return bool(mentions_ref and not has_scene and len(cleaned) < 160)


def expected_subject_category(prompt: str) -> str:
    if _BOTANICAL.search(prompt or "") and not _PERSON.search(prompt or ""):
        return "botanical"
    if _PERSON.search(prompt or ""):
        return "person_portrait"
    if _PRODUCT.search(prompt or ""):
        return "product"
    if is_meta_only_image_prompt(prompt or ""):
        return "meta_instruction"
    return "scene_other"


def presence_flags(prompt: str) -> dict[str, bool]:
    lower = (prompt or "").lower()
    return {
        "demon": bool(re.search(r"╨┤╨╡╨╝╨╛╨╜|demon", lower)),
        "woman": bool(re.search(r"╨╢╨╡╨╜╤Й╨╕╨╜|woman|╨┤╨╡╨▓╤Г╤И╨║", lower)),
        "black_hair": bool(re.search(r"╤З╤С╤А╨╜\w*\s+╨▓╨╛╨╗╨╛╤Б|╤З╨╡╤А╨╜\w*\s+╨▓╨╛╨╗╨╛╤Б|black\s+hair", lower)),
        "dark_fantasy": bool(re.search(r"╤В[╨╡╤С]╨╝╨╜\w*\s+╤Д╤Н╨╜╤В╨╡╨╖|dark\s+fantasy|╤Д╤Н╨╜╤В╨╡╨╖", lower)),
        "wings": bool(re.search(r"╨║╤А╤Л╨╗|wing", lower)),
        "red_black_lighting": bool(re.search(r"╨║╤А╨░╤Б╨╜╨╛|red|╨╛╤А╨░╨╜╨╢|╨╛╨│╨╜", lower)),
        "portrait": bool(re.search(r"╨┐╨╛╤А╤В╤А╨╡╤В|portrait", lower)),
        "attached_reference": bool(re.search(r"╤А╨╡╤Д╨╡╤А╨╡╨╜╤Б|reference|╨┐╤А╨╕╨╗╨╛╨╢╨╡╨╜", lower)),
    }


def gross_semantic_mismatch(
    *,
    expected_category: str,
    observed_category: str | None,
) -> bool:
    """Gross mismatch filter only тАФ not identity proof."""
    if not observed_category:
        return False
    expected = (expected_category or "").strip().lower()
    observed = observed_category.strip().lower()
    if expected == observed:
        return False
    personish = {"person_portrait", "person", "portrait", "character"}
    botanical = {"botanical", "flowers", "flower", "rose", "roses"}
    if expected in personish and observed in botanical:
        return True
    if expected in botanical and observed in personish:
        return True
    return False


def compute_generation_fingerprint(
    *,
    prompt: str,
    user_request_id: str,
    reference_set_id: str | None,
    selected_reference_ids: list[str],
    selected_checksums: list[str] | None = None,
    size: str,
    style: str,
    preservation: str,
    provider: str,
    model: str,
    generation_mode: str,
) -> str:
    parts = [
        normalize_prompt_text(prompt),
        str(user_request_id),
        str(reference_set_id or ""),
        ",".join(sorted(str(x) for x in selected_reference_ids)),
        ",".join(sorted(str(x) for x in (selected_checksums or []))),
        size,
        style,
        preservation,
        provider,
        model,
        generation_mode,
    ]
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def safe_prompt_debug(prompt: str) -> dict[str, Any]:
    cleaned = normalize_prompt_text(prompt)
    return {
        "prompt_hash": prompt_hash(cleaned),
        "prompt_preview": cleaned[:200],
        "prompt_length": len(cleaned),
        "expected_subject": expected_subject_category(cleaned),
        "presence_flags": presence_flags(cleaned),
        "is_meta_only": is_meta_only_image_prompt(cleaned),
    }
