"""Metrica mock tool service (Phase AI.219)."""

from __future__ import annotations

from typing import Any

from app.domain.marketing_metrica_parser import parse_metrica_input
from app.schemas.contracts import MetricaToolInput


class MarketingMetricaService:
    """Mock Metrica provider — no real Yandex API calls."""

    async def execute(self, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        parsed = parse_metrica_input(MetricaToolInput.model_validate(payload))
        counter_id = parsed.counter_id or "mock-counter"
        date1 = parsed.date1 or "7daysAgo"
        date2 = parsed.date2 or "today"

        data_rows = self._mock_report(parsed.metrics, parsed.dimensions)
        output = {
            "provider": "mock",
            "counter_id": counter_id,
            "metrics": parsed.metrics,
            "dimensions": parsed.dimensions,
            "date1": date1,
            "date2": date2,
            "filtersCustom": parsed.filtersCustom,
            "data": data_rows,
            "totals": self._mock_totals(parsed.metrics),
        }
        metadata = {
            "provider": "mock",
            "external_call": False,
            "row_count": len(data_rows),
        }
        return output, metadata

    @staticmethod
    def _mock_totals(metrics: list[str]) -> dict[str, float]:
        totals: dict[str, float] = {}
        for index, metric in enumerate(metrics):
            totals[metric] = float(1000 + index * 250)
        return totals

    @staticmethod
    def _mock_report(metrics: list[str], dimensions: list[str]) -> list[dict[str, Any]]:
        if not dimensions:
            return [{"metrics": MarketingMetricaService._mock_totals(metrics)}]

        scenarios = [
            ("organic", "desktop"),
            ("direct", "mobile"),
            ("social", "tablet"),
        ]
        rows: list[dict[str, Any]] = []
        for index, (source, device) in enumerate(scenarios):
            row: dict[str, Any] = {
                "dimensions": {
                    dimensions[0]: source if "traffic" in dimensions[0] else device,
                },
                "metrics": {},
            }
            if len(dimensions) > 1:
                row["dimensions"][dimensions[1]] = device
            for metric_index, metric in enumerate(metrics):
                row["metrics"][metric] = float(300 + index * 120 + metric_index * 40)
            rows.append(row)
        return rows
