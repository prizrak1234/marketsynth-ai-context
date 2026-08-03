"""Wordstat mock tool service (Phase AI.218)."""

from __future__ import annotations

from typing import Any

from app.core.security import sanitize_text
from app.marketing.data_tools.yandex_regions import resolve_region
from app.schemas.contracts import WordstatToolInput


class MarketingWordstatService:
    """Mock Wordstat provider — no external XMLRiver calls."""

    async def execute(self, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        parsed = WordstatToolInput.model_validate(payload)
        query = sanitize_text(parsed.query).strip()
        if not query:
            raise ValueError("query is required")

        region = resolve_region(parsed.region)
        report_type = parsed.report_type or "one"
        device = parsed.device or "all"

        rows = self._mock_rows(query, report_type)
        output = {
            "provider": "mock",
            "query": query,
            "region_code": region["code"],
            "region_name": region["name"],
            "device": device,
            "report_type": report_type,
            "rows": rows,
        }
        metadata = {
            "provider": "mock",
            "external_call": False,
            "row_count": len(rows),
        }
        return output, metadata

    @staticmethod
    def _mock_rows(query: str, report_type: str) -> list[dict[str, Any]]:
        base = {
            "phrase": query,
            "shows": 1200,
            "clicks": 84,
            "ctr": 0.07,
        }
        if report_type == "one":
            return [base]
        related = [
            {**base, "phrase": f"{query} цена", "shows": 640, "clicks": 41, "ctr": 0.064},
            {**base, "phrase": f"{query} отзывы", "shows": 510, "clicks": 29, "ctr": 0.057},
        ]
        if report_type == "short":
            return [base, *related[:1]]
        return [base, *related]
